"""Evaluación simple de escenarios configurables."""
import pandas as pd


def scenario_table(total_value: float, expected_return: float, scenarios: dict) -> pd.DataFrame:
    """Proyecta impacto mensual monetario por escenario."""
    rows = []
    for name, multiplier in scenarios.items():
        scenario_return = expected_return * float(multiplier)
        rows.append({"escenario": name, "retorno_mensual": scenario_return, "valor_estimado": total_value * (1 + scenario_return), "impacto": total_value * scenario_return})
    return pd.DataFrame(rows)
