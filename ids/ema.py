"""
ema.py - adaptive (EMA) and fixed decision thresholds for the IDS.

Implements report sections 3.4.6 / 3.5.6, with two changes that are
flagged below as deviations from the report text:
  (A) the baseline is NOT updated on windows that raised an alert
      (unless update_on_alert=True) - stops an attack raising its own threshold
  (B) the threshold is clamped to [floor, ceiling]
  (C) optional min_std: the report's std update shrinks towards zero when
      traffic is smooth, making mean + k*std hug the mean. min_std=0 keeps
      the report's behaviour; a small value (e.g. 0.02) prevents the collapse.

Time is passed in (`now`, in seconds) instead of read from the clock,
so the logic can be unit-tested without waiting 10 real minutes.
"""
import math
from dataclasses import dataclass


@dataclass
class Decision:
    status: str          # "learning" | "normal" | "alert"
    score: float
    threshold: float     # the threshold this score was compared against (None while learning)
    mean: float
    std: float
    clamped: bool        # True if the active threshold is sitting on the floor or ceiling


class AdaptiveThreshold:
    def __init__(self, mode="adaptive", beta=0.1, k=3.0,
                 learning_seconds=600, recalc_seconds=300,
                 floor=0.5, ceiling=0.95, fixed_value=0.5,
                 update_on_alert=False, min_std=0.0):
        if mode not in ("adaptive", "fixed"):
            raise ValueError("mode must be 'adaptive' or 'fixed'")
        if not 0 < beta <= 1:
            raise ValueError("beta must be in (0, 1]")
        self.mode = mode
        self.beta, self.k = beta, k
        self.learning_seconds, self.recalc_seconds = learning_seconds, recalc_seconds
        self.floor, self.ceiling = floor, ceiling
        self.fixed_value = fixed_value
        self.update_on_alert = update_on_alert
        self.min_std = min_std

        self.mean = 0.0
        self.std = 0.0
        self.threshold = None
        self.clamped = False
        self.learning = True
        self._start = None
        self._last_recalc = None
        self._learn_scores = []

    # -- helpers --------------------------------------------------------------
    def _compute_threshold(self):
        if self.mode == "fixed":
            self.threshold, self.clamped = self.fixed_value, False
            return
        raw = self.mean + self.k * max(self.std, self.min_std)  # report eq. 2.5.4, + (C)
        t = min(max(raw, self.floor), self.ceiling)  # deviation (B)
        self.threshold, self.clamped = t, (t != raw)

    def _ema_update(self, score):
        # Report 3.4.6 equations, exactly as written
        b = self.beta
        new_mean = b * score + (1 - b) * self.mean
        new_std = math.sqrt(b * (score - new_mean) ** 2 + (1 - b) * self.std ** 2)
        self.mean, self.std = new_mean, new_std

    def _finish_learning(self, now):
        n = len(self._learn_scores)
        if n:
            self.mean = sum(self._learn_scores) / n
            self.std = math.sqrt(sum((s - self.mean) ** 2 for s in self._learn_scores) / n)
        self._learn_scores = []
        self.learning = False
        self._compute_threshold()
        self._last_recalc = now

    # -- public ---------------------------------------------------------------
    def process(self, score, now):
        """Feed one window's threat score. Returns a Decision."""
        if self._start is None:
            self._start = now

        if self.learning:
            if now - self._start < self.learning_seconds:
                self._learn_scores.append(score)
                return Decision("learning", score, None, self.mean, self.std, False)
            self._finish_learning(now)

        active = self.threshold                    # compare against the ACTIVE threshold
        is_alert = score > active
        if (not is_alert) or self.update_on_alert:  # deviation (A)
            self._ema_update(score)

        if now - self._last_recalc >= self.recalc_seconds:
            self._compute_threshold()              # takes effect from the NEXT window
            self._last_recalc = now

        return Decision("alert" if is_alert else "normal", score, active,
                        self.mean, self.std, self.clamped)

    def state(self):
        """For the dashboard's system status page."""
        return {"mode": self.mode, "learning": self.learning, "mean": self.mean,
                "std": self.std, "threshold": self.threshold, "clamped": self.clamped}
