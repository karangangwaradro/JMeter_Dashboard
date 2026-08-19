#!/usr/bin/env python3
"""
apdex_calculator.py — Apdex (Application Performance Index) Calculator for JmeterAI.

Formula:
  Apdex = ( Satisfied_Count + (Tolerating_Count / 2) ) / Total_Samples

Definitions given target threshold T:
  - Satisfied:  response_time <= T AND sample is successful
  - Tolerating: T < response_time <= 4*T AND sample is successful
  - Frustrated: response_time > 4*T OR sample is failed (error)
"""

import json
from typing import List, Dict, Union, Tuple, Optional


def calculate_apdex(
    samples: List[Union[int, float]],
    success_flags: Optional[List[bool]] = None,
    target_t: float = 500.0
) -> Dict[str, Union[float, int, str]]:
    """
    Calculate Apdex score for a list of sample response times.

    :param samples: List of response times in milliseconds (or seconds if consistent with target_t).
    :param success_flags: Optional list of booleans indicating success status for each sample.
                           If None, assumes all samples in `samples` were successful.
    :param target_t: Target response time threshold T in ms (default: 500 ms).
    :return: Dictionary containing Apdex score, count breakdowns, rating label, and target_t.
    """
    if not samples:
        return {
            "apdex": 1.00,
            "target_t": target_t,
            "tolerated_t": target_t * 4,
            "satisfied": 0,
            "tolerating": 0,
            "frustrated": 0,
            "total": 0,
            "rating": "Excellent"
        }

    total = len(samples)
    if success_flags is None or len(success_flags) != total:
        success_flags = [True] * total

    tolerated_t = target_t * 4.0
    satisfied = 0
    tolerating = 0
    frustrated = 0

    for rt, is_success in zip(samples, success_flags):
        if not is_success or rt > tolerated_t:
            frustrated += 1
        elif rt <= target_t:
            satisfied += 1
        else: # target_t < rt <= 4 * target_t
            tolerating += 1

    apdex_score = (satisfied + (tolerating / 2.0)) / float(total)
    apdex_score = round(apdex_score, 3)

    rating = get_apdex_rating(apdex_score)

    return {
        "apdex": apdex_score,
        "target_t": target_t,
        "tolerated_t": tolerated_t,
        "satisfied": satisfied,
        "tolerating": tolerating,
        "frustrated": frustrated,
        "total": total,
        "rating": rating
    }


def get_apdex_rating(score: float) -> str:
    """
    Get standard Apdex rating description based on score.
      0.94 - 1.00 : Excellent
      0.85 - 0.93 : Good
      0.70 - 0.84 : Fair
      0.50 - 0.69 : Poor
      0.00 - 0.49 : Unacceptable
    """
    if score >= 0.94:
        return "Excellent"
    elif score >= 0.85:
        return "Good"
    elif score >= 0.70:
        return "Fair"
    elif score >= 0.50:
        return "Poor"
    else:
        return "Unacceptable"


def calculate_apdex_from_summary(
    avg_rt: float,
    p90_rt: float,
    error_rate: float,
    target_t: float = 500.0
) -> float:
    """
    Estimate Apdex score when individual raw sample arrays are unavailable,
    using summary metrics (p90, avg, error_rate).
    """
    tolerated_t = target_t * 4.0
    
    # Base penalty from error rate
    frustrated_ratio = min(1.0, error_rate / 100.0)

    # Estimate response time distribution relative to T and 4T
    if p90_rt <= target_t:
        satisfied_ratio = 1.0 - frustrated_ratio
        tolerating_ratio = 0.0
    elif p90_rt <= tolerated_t:
        satisfied_ratio = max(0.0, 0.9 - frustrated_ratio)
        tolerating_ratio = min(0.9, 1.0 - satisfied_ratio - frustrated_ratio)
    else:
        satisfied_ratio = max(0.0, 0.5 - frustrated_ratio)
        tolerating_ratio = max(0.0, 0.3 - frustrated_ratio)

    frustrated_ratio = max(0.0, 1.0 - satisfied_ratio - tolerating_ratio)

    score = satisfied_ratio + (tolerating_ratio / 2.0)
    return round(max(0.0, min(1.0, score)), 3)


if __name__ == "__main__":
    # Quick self-test
    sample_rts = [120, 250, 480, 510, 800, 1200, 2200, 3500]
    sample_success = [True, True, True, True, True, True, True, False]
    res = calculate_apdex(sample_rts, sample_success, target_t=500.0)
    print("Apdex Calculation Example:")
    print(json.dumps(res, indent=2))
