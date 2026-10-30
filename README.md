# Data Science II — Pre-entrega 6

## Análisis de datos meteorológicos con DuckDB y SQL

**Objetivo.** Analizar registros meteorológicos de **Seattle y Nueva York** mediante consultas SQL directas sobre un CSV, sin cargarlo previamente en Pandas ni crear archivos de bases de datos. Se calculan promedios mensuales, máximas observadas por ubicación, conteos de eventos extremos y un ranking de meses cálidos.

### Fuente y alcance

El conjunto de referencia es **`weather.csv` de Vega Datasets**, construido a partir de datos de **NOAA** y destinado a fines educativos: **2.922 registros diarios**, **2 ubicaciones** (Seattle y Nueva York), entre el **01/01/2012 y el 31/12/2015**. Las temperaturas se expresan en °C y la precipitación en mm. El indicador categórico `weather` es una variable derivada por Vega, no una observación primaria de NOAA.

- Descripción y ficha de campos: <https://vega.github.io/vega-datasets/datasets/weather/>
- Repositorio de datos: <https://github.com/vega/vega-datasets/tree/master/data>
- CSV directo para descarga: <https://raw.githubusercontent.com/vega/vega-datasets/master/data/weather.csv>
- Procedencia del extracto educativo: registros publicados por Vega/Observable y sus copias públicas.

**Dos modos de trabajo, sin confundir resultados:**

1. **Muestra incluida:** `datos/muestra_weather.csv` contiene **30 registros reales seleccionados** del archivo público. Permite verificar rápidamente las consultas y las pruebas sin conexión. **No representa el conjunto histórico completo.**
2. **Dataset completo:** la opción `--completo` descarga la serie de Vega (2.922 registros, según su ficha pública) a `datos/weather_completo.csv` y ejecuta las mismas consultas. Si la descarga falla, se informa el problema sin inventar datos. El archivo completo es opcional y se ignora en Git.

**Nota de precisión:** el campo `location` identifica la **ciudad**, no el ID único de una estación física. Las "máximas por estación" de esta práctica se interpretan y rotulan correctamente como *máximas por ubicación*. Para estudiar estaciones instrumentales específicas habría que incorporar identificadores de estación desde NOAA.

## Estructura del repositorio

```text
.
├── main.py                 # Orquestador + medición de tiempos de consultas
├── src/
│   ├── fuentes.py          # Validación, descarga y vistas temporales de CSV
│   └── consultas.py        # SQL: calidad y cuatro análisis
├── datos/
│   └── muestra_weather.csv # 30 registros reales seleccionados
├── tests/
│   └── test_pipeline.py    # 10 controles, incluyendo nulos y duplicados
├── evidencia/
│   └── control_muestra.txt # Resultados esperados y límites de la verificación
├── requirements.txt
├── .gitignore
└── README.md
```

**No hay archivos `.db` ni `.duckdb`**. Se usa `duckdb.connect(database=":memory:")` solo para crear vistas temporales. La lectura de datos se hace con `read_csv_auto(..., all_varchar = true)` **directamente sobre el CSV**. DuckDB realiza la lectura, limpieza y agregación en SQL.

## Instalar y ejecutar (Windows / PowerShell)

Desde la raíz de la carpeta descargada:

```powershell
py -m pip install -r requirements.txt
py main.py
py -m unittest discover -s tests -v
```

El comando principal analiza la muestra de 30 lecturas públicas sin acceso a Internet; imprime filas utilizadas, hallazgos y tiempo en milisegundos para cada consulta. También guarda los cuatro CSV de resultados en `resultados/` (carpeta ignorada por Git, porque son archivos regenerables).

Para trabajar con **los 2.922 registros del dataset histórico completo** (requiere Internet la primera vez):

```powershell
py main.py --completo
```

Para forzar una nueva descarga: `py main.py --completo --actualizar`.
Para utilizar otro CSV con el mismo esquema: `py main.py --archivo ruta/al/archivo.csv`.
Para no guardar resultados: `py main.py --sin-exportar`.

Si la URL pública no estuviera accesible, descargá manualmente el `weather.csv` desde la página de Vega y usá `py main.py --archivo RUTA_DEL_CSV`.

## Etapas del análisis y limpieza

| Etapa | Operación | Razón |
|---|---|---|
| Ingesta | `read_csv_auto` directamente sobre archivo | Evita carga previa en un DataFrame; DuckDB infiere o controla tipos |
| Normalización | `TRIM`, `NULLIF` y `TRY_CAST` de fechas, máximas, mínimas y precipitación | Datos vacíos/inválidos se reconocen como `NULL` sin romper el análisis |
| Control de calidad | Descarte de filas sin fecha/ubicación o temperatura válida | No inventar temperaturas ni sesgar promedios con imputaciones artificiales |
| Consistencia | Exige `temp_min <= temp_max` y rango físico de -60 a 60 °C | Evita valores imposibles en este escenario educativo |
| Duplicados | `ROW_NUMBER` por ubicación+fecha, conserva una observación | Evita contar dos veces un día |
| Análisis | SQL `AVG`, `COUNT`, `SUM`, `HAVING`, `ROW_NUMBER` | Promedios, extremos y filtros reproducibles |

El **promedio diario de referencia** se define explícitamente como `(temp_max + temp_min) / 2`, no como un promedio de mediciones horarias. Los promedios mensuales son el promedio de ese valor aproximado en los **días disponibles**; no deben interpretarse como una climatología mensual oficial cuando hay cobertura parcial.

### Cuatro consultas analíticas

1. `01_promedios_mensuales.csv`: cantidad de días observados, temperatura de referencia media por mes, medias de máximas y mínimas, lluvia acumulada.
2. `02_maximas_por_ubicacion.csv`: fecha y máxima observada para cada ciudad, con desempate reproducible por fecha.
3. `03_eventos_extremos.csv`: días válidos, días con máximas de 30 °C o más, lluvia de al menos 10 mm y combinación de ambos filtros.
4. `04_meses_mas_calidos.csv`: diez meses con mayor temperatura media entre los que cuentan con al menos cinco observaciones (`HAVING`).

Una consulta adicional `CALIDAD` muestra filas originales, válidas, descartadas, temperaturas nulas, fechas inválidas y grupos repetidos. Las pruebas agregan datos artificiales *solo para verificar la limpieza*, separados de los registros NOAA/Vega.

## Hallazgos verificables de la muestra (30 registros)

Estos son los resultados **calculados sobre la muestra incluida**, mediante un control aritmético independiente. **No son los resultados de la serie de 2.922 registros.**

| Ciudad | Mes seleccionado | Días | Media de referencia °C | Lluvia acumulada mm |
|---|---|---:|---:|---:|
| New York | 2012-01 | 10 | 2,78 | 1,8 |
| New York | 2012-02 | 5 | 5,79 | 0,8 |
| Seattle | 2012-01 | 10 | 6,50 | 41,1 |
| Seattle | 2015-12 | 5 | 2,87 | 10,1 |

- Máxima de **New York en la muestra**: **17,8 °C**, el **01/02/2012**.
- Máxima de **Seattle en la muestra**: **12,8 °C**, el **01/01/2012**.
- En la muestra no se detectaron temperaturas nulas. La prueba `test_datos_nulos_y_duplicados` comprueba explícitamente que el pipeline rechaza filas incompletas o inconsistentes.
- **Tiempos**: el programa mide con `time.perf_counter()` los milisegundos de cada consulta en tu computadora. No se informan tiempos ficticios ni se extrapola rendimiento desde la muestra al dataset completo.

## Pruebas y reproducción

`py -m unittest discover -s tests -v` contiene **10 pruebas**: cuatro verifican la muestra y los archivos; seis ejecutan DuckDB de forma real cuando está instalado (incluyendo nulos, duplicados, máximas, agregaciones y conteos).

**Control durante la preparación:** la estructura Python compiló y las cuatro verificaciones independientes del archivo CSV pasaron. La ejecución con el motor DuckDB **requiere instalar la dependencia** y validarla en el equipo de presentación; las seis pruebas DuckDB se omiten explícitamente si no está instalado. El proyecto no afirma tiempos ni resultados de una ejecución que no haya ocurrido.

## Criterios de calidad y limitaciones

- Consultas directamente sobre archivos, sin exportar ni versionar bases de datos binarias.
- Datos públicos, ejemplos reducidos auditables, comandos exactos y tests.
- No confundir *ubicación* con *estación instrumental* ni extrapolar una muestra parcial a cuatro años.
- Las filas sin temperaturas válidas se descartan para las métricas térmicas; se registra su cantidad.
- Para producción se agregarían cobertura temporal mínima por mes, metadatos de estación, validación de unidad, control de versiones del origen y pruebas de rendimiento con el dataset completo.

**Curso:** Data Science II · **Pre-entrega:** 6 · **Tema:** DuckDB y SQL meteorológico.
