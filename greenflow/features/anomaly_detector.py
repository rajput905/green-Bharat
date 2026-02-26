"""
GreenFlow AI – Anomaly Detection Module
=========================================
Detects statistical anomalies in streaming environmental data using a
dual-method approach:
  1. Z-score  (fast, works well when window ≥ 30)
  2. IQR fence (robust to non-normal distributions)

A datapoint is flagged as an anomaly when EITHER method triggers.
Maintains a per-sensor sliding window so each city / sensor is judged
against its own history — not a global baseline.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
WINDOW_SIZE      = 60     # readings per sensor before Z-score is reliable
MIN_WINDOW       = 10     # minimum readings needed to start detection
Z_THRESHOLD      = 2.8    # standard deviations → anomaly
IQR_MULTIPLIER   = 2.5    # fence = Q3 + k×IQR  (Tukey fences, default k=1.5)
COOLDOWN_SECS    = 120    # suppress repeat anomaly alerts for same sensor+field

# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AnomalyEvent:
    sensor_id:  str
    field:      str               # "co2_ppm" | "aqi" | "risk_score" | "temperature_c"
    value:      float
    z_score:    Optional[float]
    iqr_flag:   bool
    mean:       float
    std:        float
    severity:   str               # LOW | MEDIUM | HIGH | CRITICAL
    timestamp:  float = field(default_factory=time.time) # type: ignore
    message:    str = ""

    def to_dict(self) -> dict:
        return {
            "sensor_id":  self.sensor_id,
            "field":      self.field,
            "value":      self.value,
            "z_score":    round(self.z_score, 3) if self.z_score else None, # type: ignore
            "iqr_flag":   self.iqr_flag,
            "mean":       round(self.mean, 3), # type: ignore
            "std":        round(self.std, 3), # type: ignore
            "severity":   self.severity,
            "timestamp":  self.timestamp,
            "message":    self.message,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Statistical Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mean_std(values: list[float]) -> Tuple[float, float]:
    n = len(values)
    if n < 2:
        return values[0] if n else 0.0, 0.0
    mu = sum(values) / n
    variance = sum((x - mu) ** 2 for x in values) / (n - 1)
    return mu, math.sqrt(variance)


def _percentiles(values: list[float]) -> Tuple[float, float]:
    """Return (Q1, Q3) for IQR calculation."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    # Lower half median
    q1 = _median(s[:mid]) # type: ignore
    # Upper half median (exclude middle for odd n)
    q3 = _median(s[mid + (1 if n % 2 else 0):]) # type: ignore
    return q1, q3


def _median(values: list[float]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    mid = n // 2
    return values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2


# ─────────────────────────────────────────────────────────────────────────────
# Anomaly Detector
# ─────────────────────────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    Per-sensor, per-field sliding-window anomaly detector.
    Thread-safe for asyncio (single-threaded event loop) with no locks needed.
    """

    def __init__(
        self,
        window_size:    int   = WINDOW_SIZE,
        min_window:     int   = MIN_WINDOW,
        z_threshold:    float = Z_THRESHOLD,
        iqr_multiplier: float = IQR_MULTIPLIER,
        cooldown_secs:  int   = COOLDOWN_SECS,
    ):
        self._window_size    = window_size
        self._min_window     = min_window
        self._z_threshold    = z_threshold
        self._iqr_multiplier = iqr_multiplier
        self._cooldown       = cooldown_secs

        # windows[sensor_id][field] = deque of floats
        self._windows: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )
        # last alert time: (sensor_id, field) → timestamp
        self._last_alert: Dict[Tuple[str, str], float] = {}
        # recent anomaly history (capped at 500)
        self._history: deque[AnomalyEvent] = deque(maxlen=500)

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest(
        self,
        sensor_id: str,
        readings:  Dict[str, float],
    ) -> List[AnomalyEvent]:
        """
        Ingest a dict of field→value readings for a sensor.
        Returns a (possibly empty) list of anomaly events.

        Usage::
            anomalies = detector.ingest("sensor_delhi",
                {"co2_ppm": 890, "aqi": 210, "temperature_c": 38})
        """
        found: List[AnomalyEvent] = []
        for field_name, value in readings.items():
            if value is None or not math.isfinite(value):
                continue
            evt = self._check(sensor_id, field_name, float(value))
            if evt:
                found.append(evt)
                self._history.appendleft(evt)
                logger.warning(
                    "🚨 Anomaly | sensor={} field={} value={:.2f} z={} severity={}",
                    sensor_id, field_name, value, evt.z_score, evt.severity,
                )
        return found

    def get_recent(self, limit: int = 50) -> List[dict]:
        """Return the most recent anomaly events as plain dicts."""
        return [e.to_dict() for e in list(self._history)[:limit]] # type: ignore

    def get_window_stats(self) -> dict:
        """Return per-sensor, per-field window size info (for /metrics)."""
        out: dict = {}
        for sid, fields in self._windows.items():
            out[sid] = {f: len(w) for f, w in fields.items()}
        return out

    # ── Internal logic ────────────────────────────────────────────────────────

    def _check(self, sensor_id: str, field: str, value: float) -> Optional[AnomalyEvent]:
        window = self._windows[sensor_id][field]
        snapshot = list(window)     # stable copy before appending
        window.append(value)        # update window

        if len(snapshot) < self._min_window:
            return None             # not enough data yet

        # ─ Z-score ─────────────────────────────────────────────────────────
        mu, std = _mean_std(snapshot)
        z_score: Optional[float] = None
        z_flag = False
        if std > 1e-10:
            z_score = abs((value - mu) / std)
            z_flag  = z_score > self._z_threshold

        # ─ IQR fence ───────────────────────────────────────────────────────
        iqr_flag = False
        if len(snapshot) >= 20:
            q1, q3 = _percentiles(snapshot)
            iqr    = q3 - q1
            upper  = q3 + self._iqr_multiplier * iqr
            lower  = q1 - self._iqr_multiplier * iqr
            iqr_flag = (value > upper) or (value < lower)

        is_anomaly = z_flag or iqr_flag
        if not is_anomaly:
            return None

        # ─ Cooldown dedup ──────────────────────────────────────────────────
        key = (sensor_id, field)
        now = time.time()
        if now - self._last_alert.get(key, 0.0) < self._cooldown:
            return None
        self._last_alert[key] = now

        severity = self._classify_severity(z_score)
        message  = self._build_message(sensor_id, field, value, mu, std, z_score, iqr_flag)

        return AnomalyEvent(
            sensor_id = sensor_id,
            field     = field,
            value     = value,
            z_score   = round(z_score, 3) if z_score else None, # type: ignore
            iqr_flag  = iqr_flag,
            mean      = mu,
            std       = std,
            severity  = severity,
            message   = message,
        )

    @staticmethod
    def _classify_severity(z: Optional[float]) -> str:
        if z is None:
            return "LOW"
        if z > 5.0:
            return "CRITICAL"
        if z > 4.0:
            return "HIGH"
        if z > 3.0:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _build_message(sensor_id, field, value, mu, std, z, iqr) -> str:
        methods = []
        if z and z > Z_THRESHOLD:
            methods.append(f"Z-score={z:.2f}σ")
        if iqr:
            methods.append("IQR-fence")
        return (
            f"Anomaly in '{field}' on {sensor_id}: "
            f"observed {value:.2f} vs μ={mu:.2f} σ={std:.2f}. "
            f"Detection: {', '.join(methods)}."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────
anomaly_detector = AnomalyDetector()
