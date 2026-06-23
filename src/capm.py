"""Cálculos CAPM, alfa de Jensen y Treynor."""
import numpy as np
import pandas as pd


def capm_table(portfolio: pd.DataFrame, rf_monthly: float, rm_monthly: float) -> pd.DataFrame:
    """Agrega retorno requerido CAPM, alfa Jensen y Treynor por fondo."""
    out = portfolio.copy()
    out["capm_retorno_requerido"] = rf_monthly + out["beta"] * (rm_monthly - rf_monthly)
    out["alfa_jensen"] = out["retorno_esperado_mensual"] - out["capm_retorno_requerido"]
    out["treynor"] = np.where(out["beta"] == 0, np.nan, (out["retorno_esperado_mensual"] - rf_monthly) / out["beta"])
    return out
