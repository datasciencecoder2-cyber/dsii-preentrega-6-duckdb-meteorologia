"""Consultas analíticas DuckDB. Todos los resultados salen directamente de CSV."""

# Se valida cuántas filas se conservan, cuáles tienen temperatura nula y cuáles
# se descartan por anomalías o duplicación de (ubicación, fecha).
CALIDAD = """
SELECT
    (SELECT COUNT(*) FROM clima_crudo) AS filas_crudas,
    (SELECT COUNT(*) FROM clima_valido) AS filas_validas,
    (SELECT COUNT(*) FROM clima_crudo) -
        (SELECT COUNT(*) FROM clima_valido) AS filas_descartadas,
    (SELECT COUNT(*) FROM clima_crudo
     WHERE temp_max_c IS NULL OR temp_min_c IS NULL) AS filas_temperatura_nula,
    (SELECT COUNT(*) FROM clima_crudo WHERE fecha IS NULL) AS fechas_invalidas,
    (SELECT COUNT(*) FROM (
        SELECT ubicacion, fecha FROM clima_crudo
        WHERE ubicacion IS NOT NULL AND fecha IS NOT NULL
        GROUP BY ubicacion, fecha HAVING COUNT(*) > 1
    )) AS grupos_duplicados
"""

# Consulta 1: temperaturas medias mensuales por ubicación, más días válidos.
PROMEDIOS_MENSUALES = """
SELECT
    ubicacion,
    strftime(fecha, '%Y-%m') AS mes,
    COUNT(*) AS dias_observados,
    ROUND(AVG(temperatura_media_c), 2) AS temperatura_media_c,
    ROUND(AVG(temp_max_c), 2) AS promedio_maximas_c,
    ROUND(AVG(temp_min_c), 2) AS promedio_minimas_c,
    ROUND(SUM(COALESCE(precipitacion_mm, 0)), 2) AS precipitacion_acumulada_mm
FROM clima_valido
GROUP BY ubicacion, strftime(fecha, '%Y-%m')
ORDER BY ubicacion, mes
"""

# Consulta 2: máxima absoluta observada en el período POR UBICACIÓN.
# El CSV de Vega agrega por ciudad y no identifica un sensor físico específico.
MAXIMAS_POR_UBICACION = """
WITH ranking AS (
    SELECT
        ubicacion,
        fecha,
        temp_max_c,
        ROW_NUMBER() OVER (
            PARTITION BY ubicacion
            ORDER BY temp_max_c DESC, fecha ASC
        ) AS posicion
    FROM clima_valido
)
SELECT
    ubicacion,
    strftime(fecha, '%Y-%m-%d') AS fecha_record,
    temp_max_c AS maxima_observada_c
FROM ranking
WHERE posicion = 1
ORDER BY ubicacion
"""

# Consulta 3: conteo y filtro de eventos extremos (calor y lluvias intensas).
EVENTOS_EXTREMOS = """
SELECT
    ubicacion,
    COUNT(*) AS dias_validos,
    SUM(CASE WHEN temp_max_c >= 30 THEN 1 ELSE 0 END) AS dias_calor_30c,
    SUM(CASE WHEN precipitacion_mm >= 10 THEN 1 ELSE 0 END) AS dias_lluvia_10mm,
    SUM(CASE WHEN precipitacion_mm >= 10 AND temp_max_c >= 20
             THEN 1 ELSE 0 END) AS dias_calidos_y_lluviosos
FROM clima_valido
GROUP BY ubicacion
ORDER BY ubicacion
"""

# Consulta 4: ranking de meses más cálidos con filtro sobre días observados.
MESES_MAS_CALIDOS = """
SELECT
    ubicacion,
    strftime(fecha, '%Y-%m') AS mes,
    COUNT(*) AS dias_observados,
    ROUND(AVG(temperatura_media_c), 2) AS temperatura_media_c
FROM clima_valido
GROUP BY ubicacion, strftime(fecha, '%Y-%m')
HAVING COUNT(*) >= 5
ORDER BY temperatura_media_c DESC, ubicacion, mes
LIMIT 10
"""

CONSULTAS = {
    "01_promedios_mensuales": PROMEDIOS_MENSUALES,
    "02_maximas_por_ubicacion": MAXIMAS_POR_UBICACION,
    "03_eventos_extremos": EVENTOS_EXTREMOS,
    "04_meses_mas_calidos": MESES_MAS_CALIDOS,
}
