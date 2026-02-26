"""
GreenFlow AI – Automatic Alert Engine
=======================================
Monitors environmental thresholds and anomaly events; fires SystemAlert
records when breach conditions are met.

Two trigger pathways:
  A) Threshold alerts  – rule-based (CO₂ > 800, AQI > 200, Risk > 70, etc.)
  B) Anomaly alerts    – from AnomalyDetector.ingest() output

Features:
  • Per-alert-type cooldown (avoids duplicate storms)
  • Severity escalation (LOW → MEDIUM → HIGH → CRITICAL)
  • Async DB write via SQLAlchemy
  • In-memory ring buffer of recent alerts for /metrics
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# Threshold Rules
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ThresholdRule:
    field:        str      # data field name
    low_warn:     float    # LOW severity threshold
    medium_warn:  float    # MEDIUM severity threshold
    high_warn:    float    # HIGH severity threshold
    critical:     float    # CRITICAL severity threshold
    alert_type:   str      # e.g. "CO2_HIGH"
    unit:         str = "" # ppm, AQI, etc.


DEFAULT_RULES: List[ThresholdRule] = [
    ThresholdRule("co2_ppm",      600,  700,  800, 950, "CO2_HIGH",   "ppm"),
    ThresholdRule("aqi",          100,  150,  200, 300, "AQI_HIGH",   "AQI"),
    ThresholdRule("risk_score",    50,   60,   70,  85, "RISK_HIGH",  "%"),
    ThresholdRule("temperature_c", 35,   38,   40,  45, "HEAT_HIGH",  "°C"),
    ThresholdRule("carbon_score",  0.7,  0.8,  0.9, 0.95,"CARBON_HIGH",""),
]


# ─────────────────────────────────────────────────────────────────────────────
# Alert Record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AlertRecord:
    alert_type: str
    severity:   str
    message:    str
    city:       Optional[str] = None
    timestamp:  float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "alert_type": self.alert_type,
            "severity":   self.severity,
            "message":    self.message,
            "city":       self.city,
            "timestamp":  self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Alert Engine
# ─────────────────────────────────────────────────────────────────────────────

class AlertEngine:
    """
    Evaluates incoming readings + anomaly events against rules and fires
    alerts. Async-safe (call `async_fire` from async context for DB writes,
    or `fire` for in-memory only).
    """

    COOLDOWN_SECS = 300   # 5 min between identical alert types per city

    def __init__(self, rules: Optional[List[ThresholdRule]] = None):
        self._rules:     List[ThresholdRule] = rules or DEFAULT_RULES
        self._cooldowns: Dict[str, float]    = {}   # key = f"{city}:{alert_type}"
        self._history:   deque[AlertRecord]  = deque(maxlen=200)
        self._total_fired: int = 0

    # ── Public sync interface ─────────────────────────────────────────────────

    def evaluate(
        self,
        readings: Dict[str, float],
        city:     Optional[str] = None,
        anomalies: Optional[list] = None,
    ) -> List[AlertRecord]:
        """
        Evaluate readings + anomaly events. Returns list of new alerts fired.
        Call from async context via `await evaluate_async(...)`.
        """
        fired: List[AlertRecord] = []

        # A) Threshold rules
        for rule in self._rules:
            value = readings.get(rule.field)
            if value is None:
                continue
            sev = self._classify_threshold(rule, value)
            if sev is None:
                continue
            msg = (
                f"{rule.field} reached {value:.1f}{rule.unit} "
                f"in {city or 'unknown city'} — {sev} alert."
            )
            alert = self._maybe_fire(rule.alert_type, sev, msg, city)
            if alert:
                fired.append(alert)

        # B) Anomaly events
        if anomalies:
            for evt in anomalies:
                atype = f"ANOMALY_{str(evt.field).upper()}"
                msg   = str(evt.message)
                alert = self._maybe_fire(atype, str(evt.severity), msg, city)
                if alert:
                    fired.append(alert)

        return fired

    async def evaluate_async(
        self,
        readings:  Dict[str, float],
        city:      Optional[str] = None,
        anomalies: Optional[list] = None,
        db_session=None,
    ) -> List[AlertRecord]:
        """
        Async version: evaluates rules and optionally persists to DB.
        `db_session` should be a SQLAlchemy AsyncSession if provided.
        """
        alerts = self.evaluate(readings, city, anomalies)

        if alerts and db_session is not None:
            await self._persist(alerts, db_session)

        return alerts

    def get_recent(self, limit: int = 50) -> List[dict]:
        """Return most recent alerts as plain dicts (for /metrics)."""
        return [a.to_dict() for a in list(self._history)[:limit]]

    @property
    def total_fired(self) -> int:
        return self._total_fired

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _maybe_fire(
        self, alert_type: str, severity: str, message: str, city: Optional[str]
    ) -> Optional[AlertRecord]:
        """Fire alert if not in cooldown; record in history."""
        key = f"{city or '_'}:{alert_type}"
        now = time.time()
        if now - self._cooldowns.get(key, 0.0) < self.COOLDOWN_SECS:
            return None

        self._cooldowns[key] = now
        record = AlertRecord(
            alert_type = alert_type,
            severity   = severity,
            message    = message,
            city       = city,
        )
        self._history.appendleft(record)
        self._total_fired += 1

        log_fn = {
            "CRITICAL": logger.critical,
            "HIGH":     logger.error,
            "MEDIUM":   logger.warning,
        }.get(severity, logger.info)
        log_fn("🔔 Alert | type={} sev={} city={} msg={}", alert_type, severity, city, message)

        return record

    @staticmethod
    def _classify_threshold(rule: ThresholdRule, value: float) -> Optional[str]:
        if value >= rule.critical:
            return "CRITICAL"
        if value >= rule.high_warn:
            return "HIGH"
        if value >= rule.medium_warn:
            return "MEDIUM"
        if value >= rule.low_warn:
            return "LOW"
        return None

    @staticmethod
    async def _persist(alerts: List[AlertRecord], session) -> None:
        """Write alert records to SystemAlert table."""
        try:
            from database.session import SystemAlert  # lazy import
            for a in alerts:
                session.add(SystemAlert(
                    timestamp  = a.timestamp,
                    city       = a.city,
                    alert_type = a.alert_type,
                    message    = a.message,
                    severity   = a.severity,
                    resolved   = False,
                ))
            await session.commit()
            logger.debug("Persisted {} alert(s) to DB", len(alerts))
        except Exception as exc:
            logger.error("Failed to persist alerts: {}", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────
alert_engine = AlertEngine()
