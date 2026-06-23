"""Métricas de retorno, riesgo y agregación de portafolio."""
import numpy as np
import pandas as pd
from scipy.stats import norm


def latest_portfolio(saldos: pd.DataFrame, fondos: pd.DataFrame, politica: dict) -> pd.DataFrame:
    """Calcula saldo, peso actual, objetivo y desviación para la fecha más reciente."""
    fecha = saldos["fecha"].max()
    actual = saldos[saldos["fecha"] == fecha].copy()
    actual["saldo_total"] = actual["saldo"].sum()
    actual["peso_actual"] = actual["saldo"] / actual["saldo_total"]
    actual["peso_objetivo"] = actual["fondo"].map(politica["pesos_objetivo"])
    actual["desviacion"] = actual["peso_actual"] - actual["peso_objetivo"]
    actual = actual.merge(fondos, on="fondo", how="left")
    actual["retorno_esperado_anual"] = (1 + actual["retorno_esperado_mensual"]) ** 12 - 1
    actual["volatilidad_anual"] = actual["volatilidad_mensual"] * np.sqrt(12)
    return actual


def covariance_matrix(fondos: pd.DataFrame, politica: dict) -> pd.DataFrame:
    """Construye matriz de covarianzas mensual desde volatilidades y correlaciones configuradas."""
    nombres = fondos["fondo"].tolist()
    vols = fondos.set_index("fondo")["volatilidad_mensual"].reindex(nombres).to_numpy()
    corr = pd.DataFrame(politica["correlaciones"]).reindex(index=nombres, columns=nombres).T.fillna(0.0)
    np.fill_diagonal(corr.values, 1.0)
    cov = np.outer(vols, vols) * corr.to_numpy()
    return pd.DataFrame(cov, index=nombres, columns=nombres)


def portfolio_metrics(weights, returns, cov, rf_monthly: float) -> dict:
    """Calcula métricas mensuales y anualizadas de un vector de pesos."""
    weights = np.asarray(weights, dtype=float)
    port_return = float(weights @ returns)
    port_vol = float(np.sqrt(weights @ cov @ weights))
    sharpe = np.nan if port_vol == 0 else (port_return - rf_monthly) / port_vol
    return {
        "retorno_mensual": port_return,
        "retorno_anual": (1 + port_return) ** 12 - 1,
        "volatilidad_mensual": port_vol,
        "volatilidad_anual": port_vol * np.sqrt(12),
        "sharpe": sharpe,
    }


def parametric_var_95(value: float, expected_return: float, volatility: float, confidence: float = 0.95) -> float:
    """VaR paramétrico mensual positivo: pérdida potencial en moneda al nivel indicado."""
    z = norm.ppf(1 - confidence)
    return max(0.0, -value * (expected_return + z * volatility))
