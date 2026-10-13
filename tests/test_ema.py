"""Unit tests for ids/ema.py.  Run from the project root:  python -m pytest -v"""
import math
import random

import pytest

from ids.ema import AdaptiveThreshold

WIN = 5  # seconds per flow window


def feed(det, scores, start=0):
    """Feed scores one window apart; return (decisions, next_time)."""
    out, t = [], start
    for s in scores:
        out.append(det.process(s, t))
        t += WIN
    return out, t


def learned(**kw):
    """A detector that has finished its 600 s learning window on scores ~0.02
    and processed one live window. Returns (detector, next_time)."""
    det = AdaptiveThreshold(**kw)
    rnd = random.Random(0)
    _, t = feed(det, [0.02 + rnd.uniform(-0.01, 0.01) for _ in range(600 // WIN)])
    det.process(0.02, t)          # first live window: learning ends here
    return det, t + WIN


def test_no_alerts_during_learning():
    det = AdaptiveThreshold()
    decs, _ = feed(det, [0.99] * (600 // WIN))
    assert all(d.status == "learning" for d in decs)


def test_threshold_set_when_learning_ends():
    det, t = learned(floor=0.0, ceiling=1.0)
    d = det.process(0.02, t)
    assert not det.learning
    assert d.threshold == pytest.approx(det.mean + 3.0 * det.std, abs=0.02)


def test_quiet_traffic_clamps_to_floor():
    det, t = learned()                   # benign scores ~0.02 -> raw threshold ~0.04
    d = det.process(0.02, t)
    assert d.threshold == 0.5 and d.clamped


def test_spike_alerts_and_does_not_move_baseline():
    det, t = learned()
    mean_before, std_before = det.mean, det.std
    d = det.process(0.99, t)
    assert d.status == "alert"
    assert det.mean == mean_before and det.std == std_before


def test_threshold_only_changes_at_recalc_boundary():
    det, t = learned(floor=0.0, ceiling=1.0)
    first = det.process(0.02, t).threshold
    # 58 more windows: still inside the 300 s interval that started at learning end
    decs, t = feed(det, [0.3] * 58, start=t + WIN)
    assert all(d.threshold == first for d in decs)
    # the window that crosses 300 s triggers a recalculation for the NEXT one
    det.process(0.3, t)
    assert det.process(0.3, t + WIN).threshold != first


DRIFT = [0.02 + i * 0.00005 for i in range(720)]   # benign scores rising slowly for 1 hour


def test_std_collapse_without_min_std():
    """Report's equations as written: smooth traffic shrinks std, threshold hugs
    the mean, and a slow legitimate rise ends up raising false alerts."""
    det, t = learned(floor=0.0, ceiling=1.0, min_std=0.0)
    decs, _ = feed(det, DRIFT, start=t)
    assert any(d.status == "alert" for d in decs)


def test_rising_benign_traffic_raises_threshold_with_min_std():
    det, t = learned(floor=0.0, ceiling=1.0, min_std=0.02)
    decs, _ = feed(det, DRIFT, start=t)
    assert decs[-1].threshold > decs[0].threshold
    assert not any(d.status == "alert" for d in decs)


def test_sustained_attack_cannot_raise_threshold():
    det, t = learned()
    decs, _ = feed(det, [0.99] * 60, start=t)          # 5-minute flood
    assert all(d.status == "alert" for d in decs)
    assert decs[-1].threshold == 0.5


def test_ablation_updating_on_alerts_poisons_baseline():
    """What the report's original design does: baseline also learns from attacks."""
    det, t = learned(update_on_alert=True, floor=0.0, ceiling=1.0)
    decs, _ = feed(det, [0.99] * 120, start=t)         # 10-minute flood
    assert decs[-1].threshold > decs[0].threshold
    assert decs[-1].status == "normal"                  # the attack stopped being detected


def test_fixed_mode_never_moves():
    det, t = learned(mode="fixed", fixed_value=0.5)
    decs, _ = feed(det, [0.02, 0.4, 0.99, 0.3] * 100, start=t)
    assert {d.threshold for d in decs} == {0.5}


def test_ema_equations_match_report():
    det, t = learned(floor=0.0, ceiling=1.0)
    m, s, b = det.mean, det.std, det.beta
    det.process(0.03, t)                      # below threshold, so baseline updates
    m_new = b * 0.03 + (1 - b) * m
    s_new = math.sqrt(b * (0.03 - m_new) ** 2 + (1 - b) * s ** 2)
    assert det.mean == pytest.approx(m_new) and det.std == pytest.approx(s_new)


def test_zero_variance_does_not_give_zero_threshold():
    det = AdaptiveThreshold()
    _, t = feed(det, [0.0] * (600 // WIN))
    assert det.process(0.0, t).threshold == 0.5
