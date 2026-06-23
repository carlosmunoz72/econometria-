"""Automatización diagnóstica de portafolio Trii: no compra ni vende activos reales."""
from __future__ import annotations

import csv
import math
import zipfile
import zlib
import struct
from pathlib import Path
from xml.sax.saxutils import escape

FONDOS = ["Accival Vista", "Accicuenta Mayor Riesgo", "Acciones Dinámico"]


def read_csv(path: Path):
    """Lee CSV ignorando comentarios iniciales con datos de ejemplo editables."""
    rows = []
    with path.open(encoding="utf-8") as fh:
        filtered = (line for line in fh if not line.lstrip().startswith("#"))
        for row in csv.DictReader(filtered):
            rows.append(row)
    return rows


def read_policy(path: Path):
    """Parser YAML mínimo para la política incluida en este proyecto."""
    policy = {"pesos_objetivo": {}, "correlaciones": {}, "escenarios": {}}
    section = None
    current_fund = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            section = text[:-1]
            current_fund = None
            continue
        if section == "pesos_objetivo" and indent == 2:
            key, value = text.split(":", 1)
            policy[section][key] = float(value)
        elif section == "correlaciones":
            if indent == 2 and text.endswith(":"):
                current_fund = text[:-1]
                policy[section][current_fund] = {}
            elif indent == 4 and current_fund:
                key, value = text.split(":", 1)
                policy[section][current_fund][key] = float(value)
        elif section == "escenarios" and indent == 2:
            key, value = text.split(":", 1)
            policy[section][key] = float(value)
        elif indent == 0 and ":" in text:
            key, value = text.split(":", 1)
            policy[key] = float(value)
    return policy


def latest_portfolio(saldos, fondos, policy):
    """Calcula saldos, pesos, desviaciones y métricas por fondo."""
    latest_date = max(row["fecha"] for row in saldos)
    latest_rows = [row for row in saldos if row["fecha"] == latest_date]
    fund_data = {row["fondo"]: row for row in fondos}
    total = sum(float(row["saldo"]) for row in latest_rows)
    output = []
    for row in latest_rows:
        fondo = row["fondo"]
        data = fund_data[fondo]
        saldo = float(row["saldo"])
        retorno_m = float(data["retorno_esperado_mensual"])
        vol_m = float(data["volatilidad_mensual"])
        peso = saldo / total
        objetivo = policy["pesos_objetivo"][fondo]
        output.append({
            "fecha": latest_date,
            "fondo": fondo,
            "saldo": saldo,
            "saldo_total": total,
            "peso_actual": peso,
            "peso_objetivo": objetivo,
            "desviacion": peso - objetivo,
            "retorno_esperado_mensual": retorno_m,
            "retorno_esperado_anual": (1 + retorno_m) ** 12 - 1,
            "volatilidad_mensual": vol_m,
            "volatilidad_anual": vol_m * math.sqrt(12),
            "beta": float(data["beta"]),
        })
    return output


def covariance_matrix(fondos, policy):
    """Construye la matriz de covarianzas mensual desde volatilidades y correlaciones."""
    vols = {row["fondo"]: float(row["volatilidad_mensual"]) for row in fondos}
    matrix = []
    for i in FONDOS:
        row = {"fondo": i}
        for j in FONDOS:
            corr = 1.0 if i == j else policy["correlaciones"].get(i, {}).get(j, 0.0)
            row[j] = vols[i] * vols[j] * corr
        matrix.append(row)
    return matrix


def portfolio_metrics(weights, returns, cov, rf):
    """Calcula retorno, volatilidad y Sharpe del portafolio."""
    ret = sum(w * r for w, r in zip(weights, returns))
    variance = 0.0
    for i, wi in enumerate(weights):
        for j, wj in enumerate(weights):
            variance += wi * wj * cov[i][j]
    vol = math.sqrt(max(variance, 0.0))
    return {
        "retorno_mensual": ret,
        "retorno_anual": (1 + ret) ** 12 - 1,
        "volatilidad_mensual": vol,
        "volatilidad_anual": vol * math.sqrt(12),
        "sharpe": (ret - rf) / vol if vol else 0.0,
    }


def norm_ppf_5_percent():
    """Valor z fijo para VaR paramétrico al 95%."""
    return -1.6448536269514722


def capm_table(portfolio, rf, rm):
    """Agrega CAPM, alfa de Jensen y Treynor por fondo."""
    output = []
    for row in portfolio:
        required = rf + row["beta"] * (rm - rf)
        item = dict(row)
        item["capm_retorno_requerido"] = required
        item["alfa_jensen"] = row["retorno_esperado_mensual"] - required
        item["treynor"] = (row["retorno_esperado_mensual"] - rf) / row["beta"] if row["beta"] else 0.0
        output.append(item)
    return output


def optimize(returns, cov, rf):
    """Optimización long-only por grilla: frontera, mínima varianza y máximo Sharpe."""
    candidates = []
    for a in range(0, 101):
        for b in range(0, 101 - a):
            c = 100 - a - b
            w = [a / 100, b / 100, c / 100]
            m = portfolio_metrics(w, returns, cov, rf)
            candidates.append({"pesos": w, **m})
    min_var = min(candidates, key=lambda x: x["volatilidad_mensual"])
    max_sharpe = max(candidates, key=lambda x: x["sharpe"])
    frontier = []
    buckets = {}
    for c in candidates:
        bucket = round(c["retorno_mensual"], 4)
        if bucket not in buckets or c["volatilidad_mensual"] < buckets[bucket]["volatilidad_mensual"]:
            buckets[bucket] = c
    for c in sorted(buckets.values(), key=lambda x: x["volatilidad_mensual"]):
        row = {"retorno": c["retorno_mensual"], "volatilidad": c["volatilidad_mensual"], "sharpe": c["sharpe"]}
        for idx, weight in enumerate(c["pesos"]):
            row[f"peso_{FONDOS[idx]}"] = weight
        frontier.append(row)
    return frontier, min_var, max_sharpe


def rebalance_table(portfolio, min_amount):
    """Calcula recomendación diagnóstica de rebalanceo; no opera en Trii."""
    rows = []
    for row in portfolio:
        target = row["saldo_total"] * row["peso_objetivo"]
        amount = target - row["saldo"]
        action = "Comprar/Aportar" if amount > min_amount else "Vender/Retirar" if amount < -min_amount else "Mantener"
        rows.append({
            "fondo": row["fondo"],
            "saldo": row["saldo"],
            "peso_actual": row["peso_actual"],
            "peso_objetivo": row["peso_objetivo"],
            "desviacion": row["desviacion"],
            "saldo_objetivo": target,
            "monto_sugerido": amount,
            "accion_sugerida": action,
        })
    return rows


def scenario_table(total, expected_return, scenarios):
    """Genera escenarios base, optimista, pesimista y estrés."""
    return [{"escenario": name, "retorno_mensual": expected_return * mult, "valor_estimado": total * (1 + expected_return * mult), "impacto": total * expected_return * mult} for name, mult in scenarios.items()]


def risk_alerts(portfolio, var_ratio, policy):
    """Genera alertas por desvíos de política y VaR."""
    alerts = []
    threshold = policy.get("umbral_desviacion_rebalanceo", 0.05)
    for row in portfolio:
        if abs(row["desviacion"]) > threshold:
            alerts.append({"tipo": "Desviación", "mensaje": f"{row['fondo']} se desvía {row['desviacion']:.2%} del objetivo."})
    if var_ratio > policy.get("umbral_var_95", 0.04):
        alerts.append({"tipo": "VaR", "mensaje": f"VaR 95% mensual estimado de {var_ratio:.2%} supera el umbral."})
    return alerts or [{"tipo": "OK", "mensaje": "No se detectan alertas según la política configurada."}]


def write_png(path: Path, frontier):
    """Crea un PNG simple de la frontera eficiente usando solo biblioteca estándar."""
    width, height = 640, 420
    pixels = bytearray([255, 255, 255] * width * height)
    if frontier:
        vols = [r["volatilidad"] for r in frontier]
        rets = [r["retorno"] for r in frontier]
        min_v, max_v = min(vols), max(vols)
        min_r, max_r = min(rets), max(rets)
        for row in frontier:
            x = 40 + int((row["volatilidad"] - min_v) / (max_v - min_v or 1) * (width - 80))
            y = height - 40 - int((row["retorno"] - min_r) / (max_r - min_r or 1) * (height - 80))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < width and 0 <= yy < height:
                        pos = (yy * width + xx) * 3
                        pixels[pos:pos + 3] = bytes([20, 90, 200])
    raw = b"".join(b"\x00" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def col_letter(index):
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def sheet_xml(rows):
    """Convierte lista de dicts en XML de hoja XLSX con strings inline."""
    headers = list(rows[0].keys()) if rows else ["sin_datos"]
    table = [headers] + [[row.get(h, "") for h in headers] for row in rows]
    xml_rows = []
    for r_idx, values in enumerate(table, 1):
        cells = []
        for c_idx, value in enumerate(values, 1):
            ref = f"{col_letter(c_idx)}{r_idx}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(xml_rows) + "</sheetData></worksheet>"


def write_xlsx(path: Path, sheets):
    """Escribe XLSX válido sin dependencias externas."""
    names = list(sheets.keys())
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(names)+1)) + '</Types>')
        zf.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        workbook_sheets = "".join(f'<sheet name="{escape(name[:31])}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(names, 1))
        zf.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + workbook_sheets + '</sheets></workbook>')
        rels = "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(names)+1))
        zf.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + rels + '</Relationships>')
        for i, name in enumerate(names, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(sheets[name]))


def main():
    base = Path(".")
    saldos = read_csv(base / "data/saldos_mensuales.csv")
    fondos = read_csv(base / "data/datos_fondos.csv")
    rf_rm = read_csv(base / "data/rf_rm.csv")
    policy = read_policy(base / "config/politica_portafolio.yaml")
    latest_rates = sorted(rf_rm, key=lambda r: r["fecha"])[-1]
    rf, rm = float(latest_rates["rf_mensual"]), float(latest_rates["rm_mensual"])

    portfolio = latest_portfolio(saldos, fondos, policy)
    capm = capm_table(portfolio, rf, rm)
    cov_rows = covariance_matrix(fondos, policy)
    cov = [[row[f] for f in FONDOS] for row in cov_rows]
    weights = [next(r for r in portfolio if r["fondo"] == f)["peso_actual"] for f in FONDOS]
    returns = [next(r for r in portfolio if r["fondo"] == f)["retorno_esperado_mensual"] for f in FONDOS]
    metrics = portfolio_metrics(weights, returns, cov, rf)
    total = portfolio[0]["saldo_total"]
    var_95 = max(0.0, -total * (metrics["retorno_mensual"] + norm_ppf_5_percent() * metrics["volatilidad_mensual"]))
    frontier, min_var, max_sharpe = optimize(returns, cov, rf)
    rebalance = rebalance_table(portfolio, policy.get("monto_minimo_rebalanceo", 0))
    scenarios = scenario_table(total, metrics["retorno_mensual"], policy.get("escenarios", {}))
    alerts = risk_alerts(portfolio, var_95 / total, policy)
    optimization = []
    for idx, fondo in enumerate(FONDOS):
        optimization.append({"fondo": fondo, "peso_minima_varianza": min_var["pesos"][idx], "peso_maximo_sharpe": max_sharpe["pesos"][idx]})
    summary = [{
        "saldo_total": total,
        "retorno_esperado_mensual": metrics["retorno_mensual"],
        "retorno_esperado_anual": metrics["retorno_anual"],
        "volatilidad_mensual": metrics["volatilidad_mensual"],
        "volatilidad_anual": metrics["volatilidad_anual"],
        "sharpe": metrics["sharpe"],
        "var_95_mensual": var_95,
        "rf_mensual_tes_colombia": rf,
        "rm_mensual_icolcap": rm,
    }]

    output = base / "output"
    output.mkdir(exist_ok=True)
    write_png(output / "frontera_eficiente.png", frontier)
    write_xlsx(output / "reporte_mensual.xlsx", {
        "Resumen": summary,
        "Portafolio": capm,
        "Covarianzas": cov_rows,
        "Frontera eficiente": frontier,
        "Optimizacion": optimization,
        "Rebalanceo": rebalance,
        "Escenarios": scenarios,
        "Alertas": alerts,
    })
    print("Programa ejecutado sin errores.")
    print("Reporte generado: output/reporte_mensual.xlsx")
    print("Gráfico generado: output/frontera_eficiente.png")
    print("Rebalanceo sugerido:")
    for row in rebalance:
        print(f"- {row['fondo']}: {row['accion_sugerida']} {row['monto_sugerido']:.2f}")


if __name__ == "__main__":
    main()
