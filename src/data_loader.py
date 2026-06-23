"""Carga y validación básica de entradas del sistema."""
from pathlib import Path
import pandas as pd
import yaml

FONDOS_REQUERIDOS = ["Accival Vista", "Accicuenta Mayor Riesgo", "Acciones Dinámico"]


def load_inputs(base_path: str = "."):
    """Lee CSV y YAML requeridos; falla temprano si falta algún fondo."""
    base = Path(base_path)
    saldos = pd.read_csv(base / "data/saldos_mensuales.csv", comment="#", parse_dates=["fecha"])
    fondos = pd.read_csv(base / "data/datos_fondos.csv", comment="#")
    rf_rm = pd.read_csv(base / "data/rf_rm.csv", comment="#", parse_dates=["fecha"])
    with open(base / "config/politica_portafolio.yaml", "r", encoding="utf-8") as file:
        politica = yaml.safe_load(file)

    for nombre, data in {"saldos": saldos, "datos_fondos": fondos}.items():
        faltantes = set(FONDOS_REQUERIDOS) - set(data["fondo"].unique())
        if faltantes:
            raise ValueError(f"Faltan fondos en {nombre}: {sorted(faltantes)}")
    return saldos, fondos, rf_rm, politica
