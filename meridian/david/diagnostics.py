"""Posterior diagnostics utilities for Meridian.

This module provides simple helper functions to compute common
statistical diagnostics from the posterior draws of a fitted
``Meridian`` model.
"""

from __future__ import annotations

from typing import Dict, Optional, Union

import arviz as az
import numpy as np
import pandas as pd
from scipy.stats import jarque_bera as _jarque_bera


# --------------------------------------------------------------------
# 1. Posterior mean, standard deviation and credible interval
# --------------------------------------------------------------------

def posterior_summary(
    idata: az.InferenceData,
    var_name: str,
    coord: Optional[Dict[str, Union[str, int]]] = None,
    cred_mass: float = 0.95,
) -> Dict[str, float]:
  """Summary statistics for a single scalar posterior.

  Parameters
  ----------
  idata:
    ArviZ ``InferenceData`` returned by ``Meridian.sample_posterior``.
  var_name:
    Name of the variable to summarize, e.g. ``"beta_m"``.
  coord:
    Optional mapping selecting a single coefficient, for example
    ``{"media": "media_channel_1"}``.
  cred_mass:
    Width of the central credible interval. ``0.95`` by default.

  Returns
  -------
  dict
    Keys ``mean``, ``sd``, ``t_stat`` and the bounds of the requested
    credible interval.
  """
  da = idata.posterior[var_name]
  if coord:
    da = da.sel(**coord)
  samples = da.values.reshape(-1)

  mean = float(samples.mean())
  sd = float(samples.std(ddof=1))
  t = mean / sd

  alpha = 1.0 - cred_mass
  lo, hi = np.quantile(samples, [alpha / 2, 1.0 - alpha / 2])
  ci_key_lo = f"{cred_mass * 100:.1f}%_ci_lower"
  ci_key_hi = f"{cred_mass * 100:.1f}%_ci_upper"

  return {
      "mean": mean,
      "sd": sd,
      "t_stat": t,
      ci_key_lo: float(lo),
      ci_key_hi: float(hi),
  }


# --------------------------------------------------------------------
# 2. Variance inflation factors
# --------------------------------------------------------------------

def compute_vif(X: Union[np.ndarray, pd.DataFrame]) -> pd.Series:
  """Computes OLS-style variance inflation factors for each column of ``X``."""
  if isinstance(X, np.ndarray):
    X_mat = X
    columns = [f"x{i}" for i in range(X.shape[1])]
  else:
    X_mat = X.values
    columns = list(X.columns)

  vifs = []
  for j in range(X_mat.shape[1]):
    y = X_mat[:, j]
    X_other = np.delete(X_mat, j, axis=1)
    coef, *_ = np.linalg.lstsq(X_other, y, rcond=None)
    y_hat = X_other @ coef
    ssr = np.sum((y - y_hat) ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - ssr / sst
    vifs.append(1.0 / (1.0 - r2 + 1e-12))

  return pd.Series(vifs, index=columns, name="VIF")


# --------------------------------------------------------------------
# 3. Durbin-Watson statistic
# --------------------------------------------------------------------

def durbin_watson(residuals: np.ndarray) -> float:
  """First-order autocorrelation diagnostic."""
  residuals = np.asarray(residuals).ravel()
  diff = np.diff(residuals)
  return float(np.sum(diff ** 2) / np.sum(residuals ** 2))


# --------------------------------------------------------------------
# 4. Jarque-Bera normality test
# --------------------------------------------------------------------

def jarque_bera(residuals: np.ndarray):
  """Returns the Jarque-Bera statistic and p-value."""
  return _jarque_bera(np.asarray(residuals).ravel())


# --------------------------------------------------------------------
# 5. Mass-above-threshold test
# --------------------------------------------------------------------

def mass_above_threshold(
    idata: az.InferenceData,
    var_name: str,
    coord: dict | None = None,
    cred_mass: float = 0.95,
    *,
    threshold: float | None = None,
    log_space: bool = False,
) -> dict[str, float | bool]:
  """Probability that a coefficient exceeds a threshold."""
  da = idata.posterior[var_name]
  if coord:
    da = da.sel(**coord)
  samples = da.values.reshape(-1)

  if log_space:
    samples = np.log(samples)

  if threshold is None:
    threshold = 0.0

  prob_above = np.mean(samples > threshold)

  return {
      "prob_above": float(prob_above),
      "meets_cred": bool(prob_above >= cred_mass),
      "cred_mass_req": float(cred_mass),
      "threshold": float(threshold),
  }
