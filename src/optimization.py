"""Optimización de frontera eficiente sin posiciones cortas."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _metrics(w, returns, cov, rf):
    ret = float(w @ returns)
    vol = float(np.sqrt(w @ cov @ w))
    sharpe = -np.inf if vol == 0 else (ret - rf) / vol
    return ret, vol, sharpe


def optimize_portfolios(returns, cov, rf_monthly, points: int = 40):
    """Calcula frontera eficiente, mínima varianza y máximo Sharpe con pesos long-only."""
    n = len(returns)
    bounds = [(0, 1)] * n
    cons_sum = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    x0 = np.repeat(1 / n, n)
    min_var = minimize(lambda w: w @ cov @ w, x0, bounds=bounds, constraints=[cons_sum])
    max_sharpe = minimize(lambda w: -_metrics(w, returns, cov, rf_monthly)[2], x0, bounds=bounds, constraints=[cons_sum])

    targets = np.linspace(float(np.min(returns)), float(np.max(returns)), points)
    rows = []
    for target in targets:
        constraints = [cons_sum, {"type": "eq", "fun": lambda w, t=target: w @ returns - t}]
        res = minimize(lambda w: w @ cov @ w, x0, bounds=bounds, constraints=constraints)
        if res.success:
            ret, vol, sharpe = _metrics(res.x, returns, cov, rf_monthly)
            rows.append({"retorno": ret, "volatilidad": vol, "sharpe": sharpe, **{f"peso_{i}": v for i, v in enumerate(res.x)}})
    return pd.DataFrame(rows), min_var.x, max_sharpe.x
