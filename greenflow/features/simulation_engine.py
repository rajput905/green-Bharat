"""
GreenFlow AI – Smart-City What-If Simulation Engine
=====================================================
Provides deterministic, physics-inspired mathematical modelling for
three city-level interventions and their downstream effects on:
  • Atmospheric CO₂ concentration (ppm)
  • Environmental risk score (0-100)
  • Alert level  (SAFE / MODERATE / HIGH / CRITICAL)

Model calibration notes
------------------------
Real-world source shares (IPCC AR6 / urban studies):
  ─ Road traffic   : ~27% of urban CO₂ annually
  ─ Industry       : ~33% of urban CO₂ annually
  ─ HVAC/buildings : ~24% of urban CO₂ annually
  ─ Other (natural, agriculture, misc): ~16%

Ventilation does NOT reduce emissions directly; it dilutes local
concentrations by increasing air-exchange rate. We model it as a
concentration-dispersion multiplier, capped at 30% reduction of
local concentration.

All parameters are clipped to [0, 100] % before calculation to
avoid nonsensical extrapolations.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# Emission Source Contribution Fractions (urban average)
# ─────────────────────────────────────────────────────────────────────────────
TRAFFIC_CO2_SHARE    = 0.27   # Traffic ▶ CO₂
INDUSTRY_CO2_SHARE   = 0.33   # Industry ▶ CO₂
BUILDING_CO2_SHARE   = 0.24   # HVAC / buildings
OTHER_CO2_SHARE      = 0.16   # Residual (not controllable by these 3 levers)

# Ventilation dilution cap (max 30% local concentration reduction)
MAX_VENTILATION_DILUTION = 0.30

# ─────────────────────────────────────────────────────────────────────────────
# Risk Model Constants  (mirrors risk_engine.py for consistency)
# ─────────────────────────────────────────────────────────────────────────────
WEIGHT_CO2   = 0.55
WEIGHT_AQI   = 0.25
WEIGHT_OTHER = 0.20

BASE_CO2 = 400.0
MAX_CO2  = 1000.0

BASE_AQI = 50.0
MAX_AQI  = 300.0

# ─────────────────────────────────────────────────────────────────────────────
# Non-linear elasticity  (diminishing returns on intervention)
# ─────────────────────────────────────────────────────────────────────────────
def _diminishing(pct: float, steepness: float = 1.8) -> float:
    """
    Maps intervention percentage [0,1] → effective reduction fraction [0,1]
    using a logarithmic diminishing-returns curve.
    Full 100% intervention never yields 100% reduction in practice.
    """
    if pct <= 0:
        return 0.0
    # log-based model: effective = (1 - exp(-steepness * pct))
    return 1.0 - math.exp(-steepness * pct)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SimulationInput:
    """User-supplied 'what-if' levers — all values are percentages [0, 100]."""
    traffic_reduction_pct:   float = 0.0   # Reduce traffic by X %
    ventilation_increase_pct: float = 0.0  # Boost ventilation by X %
    industry_reduction_pct:  float = 0.0   # Reduce industrial emissions by X %

    # Optional baseline overrides (if not supplied, engine fetches from DB/cache)
    baseline_co2:   Optional[float] = None   # ppm
    baseline_aqi:   Optional[float] = None   # AQI index
    baseline_risk:  Optional[float] = None   # 0-100
    baseline_temp:  Optional[float] = None   # °C


@dataclass
class SimulationResult:
    """Full simulation output with intermediate diagnostics."""
    # Primary outputs (API contract)
    new_predicted_co2: float = 0.0
    new_risk_score:    float = 0.0
    alert_level:       str   = "SAFE"
    impact_summary:    str   = ""

    # Intermediate diagnostics
    co2_reduction_ppm:       float = 0.0   # absolute ppm saved
    co2_reduction_pct:       float = 0.0   # % reduction vs baseline
    risk_reduction:          float = 0.0   # points saved on risk score
    traffic_co2_saved:       float = 0.0
    industry_co2_saved:      float = 0.0
    ventilation_co2_diluted: float = 0.0

    # Metadata
    baseline_co2:  float = 0.0
    baseline_risk: float = 0.0
    timestamp:     float = field(default_factory=time.time) # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Core Engine
# ─────────────────────────────────────────────────────────────────────────────
class SimulationEngine:
    """
    Stateless deterministic engine.  Call `simulate()` with a `SimulationInput`
    and optionally the current live readings.
    """

    # ── Default baseline when no live data is available ──────────────────────
    DEFAULT_CO2  = 420.0    # ppm – global 2024 average
    DEFAULT_AQI  = 85.0     # moderate urban AQI
    DEFAULT_RISK = 45.0     # moderate risk
    DEFAULT_TEMP = 28.0     # °C

    # ── AQI co-reduction coefficients ────────────────────────────────────────
    # Traffic reduction also cuts particulates roughly in proportion
    TRAFFIC_AQI_COEFF  = 0.35  # 100% traffic cut ▶ ~35% AQI reduction
    INDUSTRY_AQI_COEFF = 0.40  # 100% industry cut ▶ ~40% AQI reduction
    VENTIL_AQI_COEFF   = 0.20  # 100% ventilation ▶ ~20% AQI dilution

    def simulate(
        self,
        inp: SimulationInput,
        live_co2:  Optional[float] = None,
        live_aqi:  Optional[float] = None,
        live_risk: Optional[float] = None,
        live_temp: Optional[float] = None,
    ) -> SimulationResult:
        """
        Run a single-step what-if simulation.

        Priority for baselines:
            1. inp.baseline_* (explicit override)
            2. live_* (from database / SSE)
            3. class-level defaults
        """
        # ── 1. Resolve baselines ─────────────────────────────────────────────
        base_co2  = inp.baseline_co2  or live_co2  or self.DEFAULT_CO2
        base_aqi  = inp.baseline_aqi  or live_aqi  or self.DEFAULT_AQI
        base_risk = inp.baseline_risk or live_risk or self.DEFAULT_RISK
        base_temp = inp.baseline_temp or live_temp or self.DEFAULT_TEMP

        # ── 2. Clip inputs to valid range ────────────────────────────────────
        t = max(0.0, min(100.0, inp.traffic_reduction_pct))   / 100.0
        v = max(0.0, min(100.0, inp.ventilation_increase_pct))/ 100.0
        i = max(0.0, min(100.0, inp.industry_reduction_pct))  / 100.0

        # ── 3. Compute effective fractions with diminishing returns ──────────
        eff_t = _diminishing(t, steepness=1.6)   # traffic  elasticity
        eff_v = _diminishing(v, steepness=1.2)   # ventilation elasticity
        eff_i = _diminishing(i, steepness=1.8)   # industry elasticity

        # ── 4. CO₂ reduction model ───────────────────────────────────────────
        #
        # Each source emits share_x × base_co2 ppm-equivalent.
        # Intervention cuts that source by eff_x (capped by source share).
        #
        traffic_co2_saved  = base_co2 * TRAFFIC_CO2_SHARE  * eff_t
        industry_co2_saved = base_co2 * INDUSTRY_CO2_SHARE * eff_i

        # Ventilation: disperses existing concentration; doesn't change emissions
        # but lowers *measured* local ppm.
        ventil_diluted = base_co2 * min(eff_v, MAX_VENTILATION_DILUTION)

        total_co2_reduction = traffic_co2_saved + industry_co2_saved + ventil_diluted
        new_co2 = max(300.0, base_co2 - total_co2_reduction)

        # ── 5. AQI co-reduction ──────────────────────────────────────────────
        aqi_reduction = (
            base_aqi * self.TRAFFIC_AQI_COEFF  * eff_t +
            base_aqi * self.INDUSTRY_AQI_COEFF * eff_i +
            base_aqi * self.VENTIL_AQI_COEFF   * eff_v
        )
        new_aqi = max(10.0, base_aqi - aqi_reduction)

        # ── 6. New risk score ────────────────────────────────────────────────
        n_co2 = max(0.0, min(1.0, (new_co2 - BASE_CO2) / (MAX_CO2 - BASE_CO2)))
        n_aqi = max(0.0, min(1.0, (new_aqi - BASE_AQI) / (MAX_AQI - BASE_AQI)))

        # Temperature is unchanged by these interventions
        n_temp = max(0.0, min(1.0, (base_temp - 25.0) / 20.0))

        raw_risk = (
            n_co2  * WEIGHT_CO2  +
            n_aqi  * WEIGHT_AQI  +
            n_temp * WEIGHT_OTHER
        ) * 100.0
        new_risk = float(f"{max(0.0, min(100.0, raw_risk)):.2f}")

        # ── 7. Alert level classification ────────────────────────────────────
        alert = self._classify_alert(new_risk)

        # ── 8. Build natural-language impact summary ─────────────────────────
        co2_delta_pct = (total_co2_reduction / base_co2) * 100
        risk_delta    = base_risk - new_risk
        summary       = self._build_summary(
            inp, base_co2, new_co2, base_risk, new_risk,
            alert, co2_delta_pct, risk_delta,
            traffic_co2_saved, industry_co2_saved, ventil_diluted
        )

        logger.info(
            "🔧 Simulation | CO₂: {:.1f}→{:.1f} ppm | Risk: {:.1f}→{:.1f} | Alert: {}",
            base_co2, new_co2, base_risk, new_risk, alert
        )

        return SimulationResult( # type: ignore
            new_predicted_co2       = round(new_co2, 2), # type: ignore
            new_risk_score          = new_risk,
            alert_level             = alert, # type: ignore
            impact_summary          = summary,
            co2_reduction_ppm       = round(total_co2_reduction, 2), # type: ignore
            co2_reduction_pct       = round(co2_delta_pct, 1), # type: ignore
            risk_reduction          = round(risk_delta, 2), # type: ignore
            traffic_co2_saved       = round(traffic_co2_saved, 2), # type: ignore
            industry_co2_saved      = round(industry_co2_saved, 2), # type: ignore
            ventilation_co2_diluted = round(ventil_diluted, 2), # type: ignore
            baseline_co2            = round(base_co2, 2), # type: ignore
            baseline_risk           = round(base_risk, 2), # type: ignore
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _classify_alert(risk: float) -> str:
        if risk < 30:
            return "SAFE"
        elif risk < 55:
            return "MODERATE"
        elif risk < 75:
            return "HIGH"
        else:
            return "CRITICAL"

    @staticmethod
    def _build_summary(
        inp: SimulationInput,
        base_co2: float, new_co2: float,
        base_risk: float, new_risk: float,
        alert: str,
        co2_delta_pct: float, risk_delta: float,
        traffic_saved: float, industry_saved: float, ventil_saved: float,
    ) -> str:
        parts: list[str] = []

        # Overall headline
        if co2_delta_pct >= 15:
            parts.append(f"🌟 Significant improvement: {co2_delta_pct:.1f}% CO₂ reduction achieved.")
        elif co2_delta_pct >= 5:
            parts.append(f"✅ Meaningful reduction: {co2_delta_pct:.1f}% CO₂ cut projected.")
        elif co2_delta_pct > 0:
            parts.append(f"📊 Marginal improvement: {co2_delta_pct:.1f}% CO₂ reduction possible.")
        else:
            parts.append("⚠️ No meaningful interventions applied.")

        # Source breakdown
        source_lines = []
        if inp.traffic_reduction_pct > 0:
            source_lines.append(f"traffic reduction (−{traffic_saved:.1f} ppm)")
        if inp.industry_reduction_pct > 0:
            source_lines.append(f"industrial cutback (−{industry_saved:.1f} ppm)")
        if inp.ventilation_increase_pct > 0:
            source_lines.append(f"ventilation boost (−{ventil_saved:.1f} ppm dilution)")

        if source_lines:
            parts.append("Breakdown: " + ", ".join(source_lines) + ".")

        # CO₂ delta
        parts.append(
            f"CO₂ moves from {base_co2:.1f} → {new_co2:.1f} ppm "
            f"(saving {base_co2 - new_co2:.1f} ppm)."
        )

        # Risk delta
        direction = "improved" if risk_delta > 0 else "unchanged"
        parts.append(
            f"Risk score {direction} from {base_risk:.1f} → {new_risk:.1f} "
            f"({abs(risk_delta):.1f} pts {'gained' if risk_delta > 0 else 'net'})."
        )

        # Alert narrative
        alert_msg = {
            "SAFE":     "City achieves SAFE status — outdoor activities are unrestricted.",
            "MODERATE": "City status: MODERATE — sensitive groups should still take precautions.",
            "HIGH":     "City status remains HIGH — sustained action needed over multiple days.",
            "CRITICAL": "City status still CRITICAL — intervention scale is insufficient; escalate immediately.",
        }
        parts.append(alert_msg[alert])

        return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────
simulation_engine = SimulationEngine()
