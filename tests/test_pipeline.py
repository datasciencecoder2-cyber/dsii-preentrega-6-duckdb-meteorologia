"""Pruebas funcionales DuckDB y controles de la muestra pública."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

from src.fuentes import validar_csv

ROOT = Path(__file__).resolve().parents[1]
DUCKDB_DISPONIBLE = importlib.util.find_spec('duckdb') is not None


class TestDatos(unittest.TestCase):
    def test_muestra_30_observaciones(self):
        with (ROOT / 'datos/muestra_weather.csv').open(encoding='utf-8', newline='') as f:
            self.assertEqual(len(list(csv.DictReader(f))), 30)

    def test_muestra_tiene_dos_ubicaciones(self):
        with (ROOT / 'datos/muestra_weather.csv').open(encoding='utf-8', newline='') as f:
            estaciones = {row['location'] for row in csv.DictReader(f)}
        self.assertEqual(estaciones, {'Seattle', 'New York'})

    def test_muestra_tiene_esquema_esperado(self):
        validar_csv(ROOT / 'datos/muestra_weather.csv')

    def test_csv_con_columna_faltante_se_rechaza(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'invalido.csv'
            p.write_text('location,date,temp_max\nSeattle,2023-01-01,12\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                validar_csv(p)


@unittest.skipUnless(DUCKDB_DISPONIBLE, 'DuckDB no instalado; instalar requirements.txt')
class TestConsultasDuckDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import analizar
        # Prueba completamente offline; no escribe resultados en repo.
        cls.resultados = analizar(ROOT / 'datos/muestra_weather.csv', None)

    def test_calidad_treinta_filas(self):
        self.assertEqual(self.resultados['calidad']['filas_crudas'], 30)
        self.assertEqual(self.resultados['calidad']['filas_validas'], 30)

    def test_promedios_mensuales(self):
        self.assertEqual(len(self.resultados['01_promedios_mensuales']), 4)

    def test_maximos_dos_ciudades(self):
        m = self.resultados['02_maximas_por_ubicacion']
        self.assertEqual(len(m), 2)
        self.assertEqual({x['ubicacion'] for x in m}, {'Seattle', 'New York'})
        self.assertAlmostEqual(next(x for x in m if x['ubicacion']=='New York')['maxima_observada_c'], 17.8)

    def test_conteos_eventos(self):
        e = self.resultados['03_eventos_extremos']
        self.assertEqual(len(e), 2)
        self.assertEqual(sum(x['dias_validos'] for x in e), 30)

    def test_filtro_de_5_dias(self):
        self.assertTrue(all(x['dias_observados'] >= 5 for x in self.resultados['04_meses_mas_calidos']))

    def test_datos_nulos_y_duplicados(self):
        from main import analizar
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fallas.csv'
            p.write_text(
                'location,date,precipitation,temp_max,temp_min,wind,weather\n'
                'Seattle,2023-01-01,0,12,5,3,sun\n'
                'Seattle,2023-01-01,0,12,5,3,sun\n'
                'Seattle,2023-01-02,0,,5,3,sun\n'
                'New York,2023-01-03,10,22,11,4,rain\n'
                'New York,2023-01-04,0,3,9,4,sun\n'
                'New York,malafecha,0,17,9,3,sun\n', encoding='utf-8'
            )
            r = analizar(p, None)
            self.assertEqual(r['calidad']['filas_crudas'], 6)
            self.assertEqual(r['calidad']['filas_validas'], 2)
            self.assertEqual(r['calidad']['filas_descartadas'], 4)
            self.assertEqual(r['calidad']['filas_temperatura_nula'], 1)
            self.assertEqual(r['calidad']['fechas_invalidas'], 1)
            self.assertEqual(r['calidad']['grupos_duplicados'], 1)


if __name__ == '__main__':
    unittest.main()
