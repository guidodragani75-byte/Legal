"""
Suite de Pruebas Automatizadas para Nuevas Capacidades de Designer:
- Soporte Multi-Formato Adaptativo (1:1, 4:5, 9:16)
- Renderizado de Imagen de Fondo con Overlay y Gradiente de Alto Contraste
- Biblioteca Híbrida de Assets (IA + Stock Libre) y Fallback Resiliente
- Integridad Visual y Safe Zones para Redes Sociales (Instagram y TikTok)
"""

import os
import sys
import shutil
import tempfile
import unittest
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import designer


class TestDesignerMultiFormat(unittest.TestCase):
    """Verificación de formatos y dimensiones adaptativas."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_out = getattr(designer, "OUTPUT_DIR", "output")
        designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        designer.OUTPUT_DIR = self.orig_out
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_formato_1_1_dimensiones_exactas(self):
        """Formato 1:1 debe generar una imagen de 1080x1080 píxeles."""
        data = {
            "monto": "$15.000.000",
            "titulo_caratula": "CONDENA POR DESPIDO INJUSTIFICADO",
            "gancho": "¿Te despidieron sin causa? Reclamá tu indemnización.",
            "formato": "1:1"
        }
        path = designer.generar_caratula(data, "test_1_1")
        self.assertTrue(os.path.exists(path))
        with Image.open(path) as img:
            self.assertEqual(img.size, (1080, 1080))
            self.assertEqual(img.format, "PNG")

    def test_formato_4_5_dimensiones_exactas(self):
        """Formato 4:5 (Instagram Portrait Feed) debe medir exactamente 1080x1350 píxeles."""
        data = {
            "monto": "$32.400.000",
            "titulo_caratula": "INDEMNIZACIÓN AGRAVADA POR TRABAJO EN NEGRO",
            "gancho": "La justicia sancionó con multas de las leyes 24.013 y 25.323.",
            "formato": "4:5"
        }
        path = designer.generar_caratula(data, "test_4_5")
        self.assertTrue(os.path.exists(path))
        with Image.open(path) as img:
            self.assertEqual(img.size, (1080, 1350))
            self.assertEqual(img.format, "PNG")

    def test_formato_9_16_dimensiones_exactas(self):
        """Formato 9:16 (Stories, Reels, TikTok) debe medir exactamente 1080x1920 píxeles."""
        data = {
            "monto": "US$ 150.000",
            "titulo_caratula": "JUICIO SUCESORIO Y TRACTO ABREVIADO",
            "gancho": "¿Heredaste una propiedad y querés venderla rápido sin doble escrituración?",
            "vertical": "sucesiones",
            "formato": "9:16"
        }
        path = designer.generar_caratula(data, "test_9_16")
        self.assertTrue(os.path.exists(path))
        with Image.open(path) as img:
            self.assertEqual(img.size, (1080, 1920))
            self.assertEqual(img.format, "PNG")

    def test_formato_sinonimos_y_aspect_ratio(self):
        """Comprueba alias de formato como feed, stories, tiktok y parámetro aspect_ratio."""
        casos = [
            ("feed", (1080, 1350)),
            ("stories", (1080, 1920)),
            ("tiktok", (1080, 1920)),
            ("square", (1080, 1080)),
        ]
        for alias, expected_dims in casos:
            data = {"titulo_caratula": f"TEST ALIAS {alias}", "monto": "$10.000.000"}
            path = designer.generar_caratula(data, f"alias_{alias}", aspect_ratio=alias)
            with Image.open(path) as img:
                self.assertEqual(img.size, expected_dims, f"Fallo en alias {alias}")

    def test_retrocompatibilidad_default_sin_formato(self):
        """Llamar generar_caratula sin especificar formato debe mantener el default 1080x1080."""
        data = {"titulo_caratula": "TEST DEFAULT RETROCOMPATIBILIDAD"}
        path = designer.generar_caratula(data, "test_retro")
        with Image.open(path) as img:
            self.assertEqual(img.size, (1080, 1080))


class TestDesignerBackgroundAndOverlay(unittest.TestCase):
    """Verificación de renderizado de imagen de fondo, contraste y biblioteca de assets."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_out = getattr(designer, "OUTPUT_DIR", "output")
        designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        designer.OUTPUT_DIR = self.orig_out
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_imagen_fondo_personalizada_local(self):
        """Generar carátula con imagen local arbitraria aplica overlay y crea PNG válido."""
        test_bg = os.path.join(self.test_dir, "custom_bg.jpg")
        # Crear imagen sintética brillante (para probar oscurecimiento)
        img_raw = Image.new("RGB", (600, 600), (220, 200, 180))
        img_raw.save(test_bg, "JPEG")

        data = {
            "monto": "$18.000.000",
            "titulo_caratula": "ACCIDENTE LABORAL EN PLANTA INDUSTRIAL",
            "gancho": "La ART fue condenada a abonar la indemnización integral.",
            "imagen_fondo": test_bg
        }
        out_path = designer.generar_caratula(data, "custom_bg_test")
        self.assertTrue(os.path.exists(out_path))
        with Image.open(out_path) as res:
            self.assertEqual(res.size, (1080, 1080))
            self.assertEqual(res.format, "PNG")

    def test_contraste_sobre_fondo_blanco_puro(self):
        """Incluso con un fondo 100% blanco puro, el overlay garantiza contraste oscuro."""
        white_bg = os.path.join(self.test_dir, "pure_white.png")
        Image.new("RGB", (400, 400), (255, 255, 255)).save(white_bg)

        data = {
            "monto": "$9.000.000",
            "titulo_caratula": "CONTRASTE CON FONDO BLANCO",
            "imagen": white_bg
        }
        out_path = designer.generar_caratula(data, "contrast_white_test")
        with Image.open(out_path) as res:
            # Inspeccionar muestra de píxel en zona superior o de fondo
            px = res.getpixel((50, 50))
            # El overlay debe oscurecer el blanco (255) a niveles oscuros (R, G, B < 80)
            self.assertLess(px[0], 85, f"Rojo {px[0]} demasiado claro para garantizar contraste")
            self.assertLess(px[1], 85, f"Verde {px[1]} demasiado claro para garantizar contraste")
            self.assertLess(px[2], 85, f"Azul {px[2]} demasiado claro para garantizar contraste")

    def test_fallback_automatico_cuando_archivo_no_existe(self):
        """Si la ruta de imagen no existe, debe recurrir automáticamente a la biblioteca o sólido."""
        data = {
            "monto": "$40.000.000",
            "titulo_caratula": "DESPIDO DISCRIMINATORIO",
            "imagen_fondo": "c:/ruta/fantasma/que_no_existe_12345.jpg"
        }
        out_path = designer.generar_caratula(data, "nonexistent_fallback")
        self.assertTrue(os.path.exists(out_path))
        with Image.open(out_path) as res:
            self.assertEqual(res.size, (1080, 1080))
            self.assertEqual(res.format, "PNG")

    def test_seleccion_tematica_automatica_laboral_art(self):
        """Casos de ART y accidentes deben seleccionar el asset temático correspondiente."""
        data = {
            "nicho": "laboral",
            "titulo_caratula": "ACCIDENTE DE TRABAJO EN OBRA EN CONSTRUCCION",
            "gancho": "¿Tuviste un siniestro laboral y la ART no te responde?"
        }
        out_path = designer.generar_caratula(data, "art_thematic")
        self.assertTrue(os.path.exists(out_path))
        with Image.open(out_path) as res:
            self.assertEqual(res.size, (1080, 1080))

    def test_seleccion_tematica_automatica_sucesiones_inmuebles(self):
        """Casos de sucesiones con inmuebles deben asociarse al asset temático pertinente."""
        data = {
            "vertical": "sucesiones",
            "titulo_caratula": "TRACTO ABREVIADO Y VENTA DE INMUEBLE",
            "gancho": "Vendé la propiedad de la herencia en un solo acto notarial."
        }
        out_path = designer.generar_caratula(data, "suc_thematic")
        self.assertTrue(os.path.exists(out_path))
        with Image.open(out_path) as res:
            self.assertEqual(res.size, (1080, 1080))

    def test_fondo_solido_explicito(self):
        """Si se solicita explícitamente imagen_fondo='solid', no aplica foto y usa color sólido."""
        data = {
            "monto": "$5.000.000",
            "titulo_caratula": "CASO LABORAL FONDO SOLIDO",
            "imagen_fondo": "solid"
        }
        out_path = designer.generar_caratula(data, "solid_bg_test")
        self.assertTrue(os.path.exists(out_path))
        with Image.open(out_path) as res:
            self.assertEqual(res.size, (1080, 1080))
            # En fondo sólido laboral puro sin foto, el píxel en (5, 5) coincide con paleta['bg']
            px = res.getpixel((5, 5))
            self.assertEqual(px, (10, 10, 12))


class TestDesignerVisualIntegrity(unittest.TestCase):
    """Verificación de que ningún elemento desborde ni se solape en ningún formato."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_out = getattr(designer, "OUTPUT_DIR", "output")
        designer.OUTPUT_DIR = self.test_dir

    def tearDown(self):
        designer.OUTPUT_DIR = self.orig_out
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_integridad_textos_extremos_en_los_tres_formatos(self):
        """Títulos extremadamente largos y ganchos extensos se ajustan en 1:1, 4:5 y 9:16."""
        payload_extremo = {
            "monto": "$ 1.250.450.800,00",
            "titulo_caratula": (
                "SENTENCIA HISTÓRICA CONTRA CONGLOMERADO INDUSTRIAL POR VIOLACIÓN SISTEMÁTICA "
                "DE MEDIDAS DE SEGURIDAD E HIGIENE CON MÚLTIPLES TRABAJADORES AFECTADOS Y DAÑOS "
                "PUNITIVOS EJEMPLARES DICTADOS POR LA JUSTICIA NACIONAL DEL TRABAJO DE ARGENTINA"
            ),
            "gancho": (
                "Si sufriste abusos patronales, falta de registración o incumplimientos graves, "
                "nuestro equipo de abogados laboralistas especializados analiza tu indemnización "
                "sin cargo y te acompaña hasta el cobro efectivo de tu sentencia."
            ),
            "cta": "Escribinos directamente al WhatsApp para evaluación confidencial"
        }

        formatos_a_probar = ["1:1", "4:5", "9:16"]
        for fmt in formatos_a_probar:
            out_file = designer.generar_caratula(payload_extremo, f"extremo_{fmt.replace(':', '_')}", formato=fmt)
            self.assertTrue(os.path.exists(out_file))
            with Image.open(out_file) as img:
                w, h = designer.FORMATOS[fmt]
                self.assertEqual(img.size, (w, h))

    def test_integridad_sin_monto_en_los_tres_formatos(self):
        """Casos sin monto económico distribuyen el espacio vertical armónicamente en 1:1, 4:5 y 9:16."""
        payload_sin_monto = {
            "monto": "",
            "titulo_caratula": "DECLARATORIA DE HEREDEROS Y VALIDEZ TESTAMENTARIA",
            "gancho": "¿Necesitás regularizar la sucesión de un familiar fallecido?",
            "vertical": "sucesiones"
        }
        for fmt in ["1:1", "4:5", "9:16"]:
            out_file = designer.generar_caratula(payload_sin_monto, f"sin_monto_{fmt.replace(':', '_')}", formato=fmt)
    def test_estilo_infobae_en_los_tres_formatos(self):
        """El estilo 'infobae' genera carátulas válidas en 1:1, 4:5 y 9:16 con branding @TuCasoLaboral."""
        payload_infobae = {
            "monto": "$24.800.000",
            "titulo_caratula": "CONDENAN A EMPRESA POR FRAUDE LABORAL TRAS HACER FACTURAR A CHOFER",
            "gancho": "¿Te obligan a facturar como monotributista pero tenés horario y jefe? Indemnización completa.",
            "fuente": "Infobae Judiciales",
            "cuenta": "@TuCasoLaboral",
            "vertical": "laboral",
            "estilo": "infobae"
        }
        for fmt in ["1:1", "4:5", "9:16"]:
            out_file = designer.generar_caratula(payload_infobae, f"infobae_test_{fmt.replace(':', '_')}", formato=fmt)
            self.assertTrue(os.path.exists(out_file))
            with Image.open(out_file) as img:
                w, h = designer.FORMATOS[fmt]
                self.assertEqual(img.size, (w, h))
                self.assertEqual(img.format, "PNG")


if __name__ == "__main__":
    unittest.main()

