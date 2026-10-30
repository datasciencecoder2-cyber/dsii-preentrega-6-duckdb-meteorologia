"""Pre-entrega 6. DuckDB analiza un CSV de clima SIN base de datos persistente."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import time

from src.consultas import CALIDAD, CONSULTAS
from src.fuentes import obtener_completo, registrar_vistas

RAIZ = Path(__file__).resolve().parent
MUESTRA = RAIZ / "datos" / "muestra_weather.csv"
COMPLETO = RAIZ / "datos" / "weather_completo.csv"


def analizar(archivo: Path, salida: Path | None = None) -> dict:
    """Abre conexión DuckDB en memoria y ejecuta 4 consultas directas sobre CSV."""
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("Falta DuckDB. Ejecutá: python -m pip install -r requirements.txt") from exc
    if salida is not None:
        salida.mkdir(parents=True, exist_ok=True)
    inicio_total = time.perf_counter()
    # :memory: evita archivos .db o .duckdb en el repositorio.
    con = duckdb.connect(database=":memory:")
    try:
        registrar_vistas(con, archivo)
        calidad = con.execute(CALIDAD)
        nombres = [x[0] for x in calidad.description]
        reporte_calidad = dict(zip(nombres, calidad.fetchone()))
        print(f"Archivo: {archivo.name}")
        print("Origen: CSV directo (vistas temporales, sin base persistente)")
        print("Calidad:", reporte_calidad)
        resultados = {"calidad": reporte_calidad}
        tiempos = {}
        for nombre, sql in CONSULTAS.items():
            inicio = time.perf_counter()
            consulta = con.execute(sql)
            columnas = [c[0] for c in consulta.description]
            filas = consulta.fetchall()
            tiempos[nombre] = round((time.perf_counter() - inicio) * 1000, 2)
            resultados[nombre] = [dict(zip(columnas, fila)) for fila in filas]
            print(f"\n{nombre}: {len(filas)} filas | {tiempos[nombre]} ms")
            for fila in filas[:5]:
                print(" ", dict(zip(columnas, fila)))
            if salida is not None:
                destino = salida / f"{nombre}.csv"
                with destino.open("w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=columnas)
                    w.writeheader()
                    w.writerows(resultados[nombre])
        resultados["tiempos_ms"] = tiempos
        resultados["tiempo_total_ms"] = round((time.perf_counter()-inicio_total)*1000, 2)
        print(f"\nTiempo total (incluye lectura/consultas): {resultados['tiempo_total_ms']} ms")
        print("ANÁLISIS FINALIZADO: OK")
        return resultados
    finally:
        con.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Análisis meteorológico con DuckDB directamente desde CSV")
    grupo = p.add_mutually_exclusive_group()
    grupo.add_argument("--completo", action="store_true", help="descarga/utiliza las 2922 filas del dataset NOAA/Vega")
    grupo.add_argument("--archivo", type=Path, help="CSV meteorológico propio con columnas estándar")
    p.add_argument("--actualizar", action="store_true", help="fuerza nueva descarga; requiere --completo")
    p.add_argument("--sin-exportar", action="store_true", help="no escribe CSVs de resultados")
    args = p.parse_args()
    if args.actualizar and not args.completo:
        p.error("--actualizar requiere --completo")
    ruta = args.archivo if args.archivo else obtener_completo(COMPLETO, args.actualizar) if args.completo else MUESTRA
    if not args.completo and args.archivo is None:
        print("MODO MUESTRA: 30 lecturas reales seleccionadas, no toda la serie 2012-2015.")
        print("Para el análisis histórico completo: python main.py --completo\n")
    salida = None if args.sin_exportar else RAIZ / "resultados"
    analizar(ruta, salida)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"ERROR CONTROLADO: {exc}") from exc
