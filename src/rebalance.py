"""Recomendaciones de rebalanceo; no ejecuta operaciones reales."""
import pandas as pd


def rebalance_table(portfolio: pd.DataFrame, min_amount: float) -> pd.DataFrame:
    """Calcula compras/ventas sugeridas para volver a pesos objetivo."""
    out = portfolio[["fondo", "saldo", "saldo_total", "peso_actual", "peso_objetivo", "desviacion"]].copy()
    out["saldo_objetivo"] = out["saldo_total"] * out["peso_objetivo"]
    out["monto_sugerido"] = out["saldo_objetivo"] - out["saldo"]
    out["accion_sugerida"] = out["monto_sugerido"].apply(lambda x: "Comprar/Aportar" if x > min_amount else ("Vender/Retirar" if x < -min_amount else "Mantener"))
    return out


def risk_alerts(portfolio: pd.DataFrame, var_ratio: float, politica: dict) -> pd.DataFrame:
    """Genera alertas por desviación de política y VaR elevado."""
    alerts = []
    threshold = politica.get("umbral_desviacion_rebalanceo", 0.05)
    for _, row in portfolio.iterrows():
        if abs(row["desviacion"]) > threshold:
            alerts.append({"tipo": "Desviación", "mensaje": f"{row['fondo']} se desvía {row['desviacion']:.2%} del objetivo."})
    if var_ratio > politica.get("umbral_var_95", 0.04):
        alerts.append({"tipo": "VaR", "mensaje": f"VaR 95% mensual estimado de {var_ratio:.2%} supera el umbral."})
    if not alerts:
        alerts.append({"tipo": "OK", "mensaje": "No se detectan alertas según la política configurada."})
    return pd.DataFrame(alerts)
