"""Generación de reporte Excel y gráfico de frontera eficiente."""
from pathlib import Path
import matplotlib.pyplot as plt


def save_frontier_plot(frontier, min_var_point, max_sharpe_point, output_path: Path):
    """Guarda gráfico de frontera eficiente."""
    plt.figure(figsize=(8, 5))
    plt.plot(frontier["volatilidad"], frontier["retorno"], label="Frontera eficiente")
    plt.scatter([min_var_point["volatilidad_mensual"]], [min_var_point["retorno_mensual"]], label="Mínima varianza")
    plt.scatter([max_sharpe_point["volatilidad_mensual"]], [max_sharpe_point["retorno_mensual"]], label="Máximo Sharpe")
    plt.xlabel("Volatilidad mensual")
    plt.ylabel("Retorno mensual")
    plt.title("Frontera eficiente long-only")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def write_excel(path: Path, sheets: dict):
    """Escribe un libro Excel con una hoja por tabla."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with __import__("pandas").ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
