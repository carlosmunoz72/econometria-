# Sistema inicial de automatización de portafolio Trii

Programa en Python para seguimiento mensual, análisis de riesgo, optimización y rebalanceo **sugerido** de un portafolio con los fondos Accival Vista, Accicuenta Mayor Riesgo y Acciones Dinámico.

> Importante: este sistema no automatiza compras ni ventas reales en Trii. Solo genera diagnóstico, alertas y recomendaciones de rebalanceo.

## Estructura

- `main.py`: orquestador del proceso.
- `config/politica_portafolio.yaml`: pesos objetivo, correlaciones, escenarios y umbrales editables.
- `data/*.csv`: archivos de entrada. Incluyen datos de ejemplo claramente marcados como editables.
- `src/`: módulos de carga, métricas, CAPM, optimización, escenarios, rebalanceo y reporte.
- `output/`: carpeta donde se generan `reporte_mensual.xlsx` y `frontera_eficiente.png`.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

La versión actual es autocontenida y no requiere paquetes externos para ejecutarse; `requirements.txt` se mantiene para conservar el flujo estándar de instalación.

## Preparar datos

Reemplaza los datos de ejemplo por información real:

1. `data/saldos_mensuales.csv`: columnas `fecha,fondo,saldo`.
2. `data/datos_fondos.csv`: columnas `fondo,retorno_esperado_mensual,volatilidad_mensual,beta`.
3. `data/rf_rm.csv`: columnas `fecha,rf_mensual,rm_mensual`, donde Rf representa TES Colombia y Rm representa ICOLCAP.
4. `config/politica_portafolio.yaml`: pesos objetivo, matriz de correlaciones y umbrales.

## Ejecución

```bash
python main.py
```

El sistema genera:

- `output/reporte_mensual.xlsx`
- `output/frontera_eficiente.png`

## Contenido del reporte

El Excel incluye hojas con resumen del portafolio, métricas por fondo, matriz de covarianzas, frontera eficiente sin posiciones cortas, portafolios de mínima varianza y máximo Sharpe, escenarios, alertas y tabla de rebalanceo sugerido.
