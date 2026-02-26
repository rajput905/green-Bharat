"""
GreenFlow AI – Real-Time Prediction Engine
===========================================
Implements stateful streaming ML using Pathway for CO2 forecasting.
"""

import pathway as pw
import numpy as np
from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 1. Schemas
# ─────────────────────────────────────────────────────────────────────────────

class CO2Schema(pw.Schema):
    co2: float
    timestamp: float
    city: str

# ─────────────────────────────────────────────────────────────────────────────
# 2. UDFs (User Defined Functions)
# ─────────────────────────────────────────────────────────────────────────────

@pw.udf
def linear_regression_predict(timestamps: list[float], values: list[float], horizon_sec: float) -> float:
    """
    Performs simple linear regression over the window and predicts the value 
    at (latest_timestamp + horizon_sec).
    """
    if len(timestamps) < 2:
        return values[-1] if values else 0.0
    
    x = np.array(timestamps)
    y = np.array(values)
    
    # Simple linear fit: y = mx + c
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    
    latest_x = timestamps[-1]
    prediction = m * (latest_x + horizon_sec) + c
    return float(prediction)

@pw.udf
def compute_trend(timestamps: list[float], values: list[float]) -> str:
    """Classifies movement as increasing, decreasing, or stable."""
    if len(timestamps) < 5:
        return "stable"
    
    y = np.array(values)
    # Simple check: compare avg of first half vs second half of window
    mid = len(y) // 2
    first_half = np.mean(y[:mid])
    second_half = np.mean(y[mid:])
    
    diff_pct = (second_half - first_half) / (first_half + 1e-6)
    
    if diff_pct > 0.02: return "increasing"
    if diff_pct < -0.02: return "decreasing"
    return "stable"

@pw.udf
def compute_confidence(values: list[float]) -> float:
    """
    Estimates prediction confidence (0-1) based on data stability.
    More variance = lower confidence.
    """
    if len(values) < 3:
        return 0.5
    
    std = np.std(values)
    mean = np.mean(values)
    
    # Coefficient of variation (CV) as an inverse proxy for confidence
    cv = std / (mean + 1e-6)
    confidence = max(0.1, min(1.0, 1.0 - cv))
    return float(confidence)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Stream Transformation
# ─────────────────────────────────────────────────────────────────────────────

def build_co2_prediction_stream(co2_stream: pw.Table):
    """
    Applies stateful windowing to a CO2 stream.
    Window: 15 minutes (900 seconds) sliding.
    """
    # 1. Windowing
    windowed = co2_stream.window(
        pw.windows.sliding(duration=900, hop=30),
        instance=co2_stream.city
    ).reduce(
        timestamp=pw.reducers.max(co2_stream.timestamp),
        current_co2=pw.reducers.last(co2_stream.co2),
        # Collect lists for UDFs
        ts_list=pw.reducers.tuple(co2_stream.timestamp),
        val_list=pw.reducers.tuple(co2_stream.co2),
    )

    # 2. Predictive Features
    predictions = windowed.select(
        timestamp=pw.this.timestamp,
        current_co2=pw.this.current_co2,
        predicted_co2_30min=linear_regression_predict(
            pw.this.ts_list, pw.this.val_list, 1800.0
        ),
        trend=compute_trend(pw.this.ts_list, pw.this.val_list),
        confidence=compute_confidence(pw.this.val_list)
    )

    return predictions
