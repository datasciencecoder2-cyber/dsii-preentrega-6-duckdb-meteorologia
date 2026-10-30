"""Lectura directa de CSV y descarga opcional del conjunto completo NOAA/Vega."""
from __future__ import annotations

import csv
from pathlib import Path
import urllib.error
import urllib.request

# Vega Datasets: 2922 observaciones diarias de Seattle y Nueva York, 2012-2015.
# Fuente: https://vega.github.io/vega-datasets/datasets/weather/
DATASET_URL = "https://raw.githubusercontent.com/vega/vega-datasets/master/data/weather.csv"
REQUERIDAS = {"location", "date", "temp_max", "temp_min", "precipitation"}


def validar_csv(ruta: Path) -> None:
    """Exige CSV no vacío y esquema meteorológico mínimo antes de usarlo."""
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el CSV: {ruta}")
    if ruta.stat().st_size == 0:
        raise ValueError("El CSV está vacío")
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.reader(archivo)
        columnas = next(lector, [])
        faltantes = REQUERIDAS - set(columnas)
        if faltantes:
            raise ValueError(f"Columnas faltantes en {ruta.name}: {sorted(faltantes)}")
        if next(lector, None) is None:
            raise ValueError("El CSV contiene cabecera pero no datos")


def obtener_completo(destino: Path, actualizar: bool = False) -> Path:
    """Descarga de forma atómica solo si no existe o se solicita actualizar."""
    if destino.exists() and not actualizar:
        validar_csv(destino)
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".descarga")
    try:
        solicitud = urllib.request.Request(
            DATASET_URL, headers={"User-Agent": "DSII-Preentrega6-educativo/1.0"}
        )
        with urllib.request.urlopen(solicitud, timeout=25) as respuesta:
            contenido = respuesta.read(3_000_001)
        if len(contenido) > 3_000_000:
            raise ValueError("El CSV supera el límite de seguridad de 3 MB")
        temporal.write_bytes(contenido)
        validar_csv(temporal)
        temporal.replace(destino)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        temporal.unlink(missing_ok=True)
        raise RuntimeError(
            f"No se pudo obtener el dataset completo desde {DATASET_URL}: {exc}. "
            "La muestra incluida sigue disponible con 'python main.py'."
        ) from exc
    return destino


def registrar_vistas(conexion, archivo: Path) -> None:
    """Crea solo vistas TEMPORALES de DuckDB sobre el CSV: jamás importa filas a una BD."""
    validar_csv(archivo)
    # DuckDB interpreta la ruta como literal SQL, escapando comillas simples.
    ruta_sql = archivo.resolve().as_posix().replace("'", "''")
    conexion.execute(f"""
        CREATE OR REPLACE TEMP VIEW clima_crudo AS
        SELECT
            NULLIF(TRIM(location), '') AS ubicacion,
            TRY_CAST(date AS DATE) AS fecha,
            TRY_CAST(NULLIF(TRIM(temp_max), '') AS DOUBLE) AS temp_max_c,
            TRY_CAST(NULLIF(TRIM(temp_min), '') AS DOUBLE) AS temp_min_c,
            TRY_CAST(NULLIF(TRIM(precipitation), '') AS DOUBLE) AS precipitacion_mm
        FROM read_csv_auto('{ruta_sql}', all_varchar = true)
    """)
    conexion.execute("""
        CREATE OR REPLACE TEMP VIEW clima_valido AS
        WITH depurado AS (
            SELECT
                ubicacion, fecha, temp_max_c, temp_min_c, precipitacion_mm,
                ROW_NUMBER() OVER (
                    PARTITION BY ubicacion, fecha
                    ORDER BY temp_max_c DESC, temp_min_c DESC
                ) AS nro
            FROM clima_crudo
            WHERE ubicacion IS NOT NULL
              AND fecha IS NOT NULL
              AND temp_max_c IS NOT NULL AND temp_min_c IS NOT NULL
              AND temp_min_c <= temp_max_c
              AND temp_max_c BETWEEN -60 AND 60
              AND temp_min_c BETWEEN -60 AND 60
        )
        SELECT
            ubicacion, fecha, temp_max_c, temp_min_c, precipitacion_mm,
            (temp_max_c + temp_min_c) / 2 AS temperatura_media_c
        FROM depurado WHERE nro = 1
    """)
