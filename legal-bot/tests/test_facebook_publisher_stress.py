"""
tests/test_facebook_publisher_stress.py
Empirical stress-testing and adversarial challenge for Facebook Publisher in publisher.py.
Milestone M2 Verification - Challenger M2.1.
"""

import os
import io
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
import publisher


class TestMetaErrorTranslationEmpirical(unittest.TestCase):
    """
    Stress-testing traducir_error_meta with standard, edge-case, and adversarial inputs.
    Verifies Spanish diagnosis and actionable recommendations.
    """

    def test_meta_code_190_expired_subcode_463(self):
        """Code 190 with subcode 463 must diagnose expired page token in Spanish."""
        err_input = {"error": {"code": 190, "error_subcode": 463, "message": "Session has expired"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 190)
        self.assertEqual(res["subcodigo"], 463)
        self.assertIn("expirado", res["diagnostico"].lower())
        self.assertIn("facebook_page_access_token", res["accion"].lower())

    def test_meta_code_190_invalidated_subcode_467(self):
        """Code 190 with subcode 467 must diagnose invalidated token in Spanish."""
        err_input = {"error": {"code": 190, "error_subcode": 467, "message": "Session is invalid"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 190)
        self.assertEqual(res["subcodigo"], 467)
        self.assertIn("invalidado", res["diagnostico"].lower())
        self.assertIn("graph api explorer", res["accion"].lower())

    def test_meta_code_190_generic(self):
        """Code 190 without subcode must diagnose invalid/expired token in Spanish."""
        err_input = {"error": {"code": 190, "message": "Invalid OAuth access token"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 190)
        self.assertIn("token", res["diagnostico"].lower())
        self.assertIn("inválido", res["diagnostico"].lower())

    def test_meta_rate_limit_codes(self):
        """Rate limit codes (4, 17, 32, 613) must advise rate-limit waiting in Spanish."""
        for code in (4, 17, 32, 613):
            err_input = {"error": {"code": code, "message": f"User request limit reached for code {code}"}}
            res = publisher.traducir_error_meta(err_input)
            self.assertEqual(res["codigo"], code)
            self.assertIn("límite de solicitudes", res["diagnostico"].lower())
            self.assertIn("rate limit", res["diagnostico"].lower())
            self.assertIn("minutos", res["accion"].lower())

    def test_meta_permission_codes(self):
        """Permission codes (10, 200, 283) must explain missing page post permissions."""
        for code in (10, 200, 283):
            err_input = {"error": {"code": code, "message": f"Permissions error {code}"}}
            res = publisher.traducir_error_meta(err_input)
            self.assertEqual(res["codigo"], code)
            self.assertIn("permisos suficientes", res["diagnostico"].lower())
            self.assertIn("pages_manage_posts", res["accion"].lower())

    def test_meta_code_100_invalid_parameter(self):
        """Code 100 must diagnose invalid parameter or Facebook Page ID."""
        err_input = {"error": {"code": 100, "message": "Invalid parameter"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 100)
        self.assertIn("parámetro inválido", res["diagnostico"].lower())
        self.assertIn("facebook_page_id", res["accion"].lower())

    def test_meta_code_368_security_block(self):
        """Code 368 must diagnose account security block."""
        err_input = {"error": {"code": 368, "message": "Temporarily blocked for security reasons"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 368)
        self.assertIn("bloqueada", res["diagnostico"].lower())

    def test_meta_server_codes_1_and_2(self):
        """Codes 1 and 2 must diagnose Meta internal server unavailability."""
        for code in (1, 2):
            err_input = {"error": {"code": code, "message": "An unknown error has occurred"}}
            res = publisher.traducir_error_meta(err_input)
            self.assertEqual(res["codigo"], code)
            self.assertIn("error interno", res["diagnostico"].lower())

    def test_meta_unwrapped_error_dict(self):
        """Flat dictionary without outer 'error' key must be correctly processed."""
        err_input = {"code": 283, "error_subcode": None, "message": "Requires pages_manage_posts"}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 283)
        self.assertIn("permisos suficientes", res["diagnostico"].lower())

    def test_meta_unknown_numeric_code(self):
        """Unknown numeric code must pass through cleanly with default action."""
        err_input = {"error": {"code": 8888, "message": "Unseen custom Meta error"}}
        res = publisher.traducir_error_meta(err_input)
        self.assertEqual(res["codigo"], 8888)
        self.assertEqual(res["diagnostico"], "Unseen custom Meta error")
        self.assertIn("detalle", res["accion"].lower())

    def test_string_network_timeout(self):
        """String error indicating timeout must return TIMEOUT code."""
        err_str = "HTTPSConnectionPool(host='graph.facebook.com'): Read timed out. (read timeout=15)"
        res = publisher.traducir_error_meta(err_str)
        self.assertEqual(res["codigo"], "TIMEOUT")
        self.assertIn("tiempo de espera agotado", res["diagnostico"].lower())
        self.assertIn("conexión", res["accion"].lower())

    def test_string_connection_error(self):
        """String error indicating connection failure must return CONNECTION_ERROR code."""
        for phrase in [
            "Failed to establish a new connection: [Errno 11001] getaddrinfo failed",
            "Connection reset by peer",
            "Failed to resolve graph.facebook.com"
        ]:
            res = publisher.traducir_error_meta(phrase)
            self.assertEqual(res["codigo"], "CONNECTION_ERROR")
            self.assertIn("no se pudo conectar", res["diagnostico"].lower())

    def test_string_generic_unclassified(self):
        """Arbitrary string error returns DESCONOCIDO."""
        err_str = "SSL certificate verify failed: certificate has expired"
        res = publisher.traducir_error_meta(err_str)
        self.assertEqual(res["codigo"], "DESCONOCIDO")
        self.assertEqual(res["diagnostico"], err_str)

    def test_adversarial_malformed_inputs(self):
        """Robustness against None, empty dict, empty string, primitives, exceptions."""
        cases = [
            (None, "ERROR_API"),
            ({}, "ERROR_API"),
            ({"error": {}}, "ERROR_API"),
            ({"error": None}, "ERROR_API"),
            ("", "DESCONOCIDO"),
            (12345, "ERROR_API"),
            (["error", 190], "ERROR_API"),
            (Exception("Sample exc"), "ERROR_API"),
        ]
        for val, expected_code in cases:
            res = publisher.traducir_error_meta(val)
            self.assertIsInstance(res, dict)
            self.assertIn("codigo", res)
            self.assertIn("diagnostico", res)
            self.assertIn("accion", res)
            self.assertEqual(res["codigo"], expected_code)


class TestFacebookPublisherSemiAutoEmpirical(unittest.TestCase):
    """
    Stress-testing publicar_facebook fallback and 5-step checklist behavior.
    """

    def setUp(self):
        # Save original publisher credentials
        self._orig_token = publisher.FACEBOOK_PAGE_TOKEN
        self._orig_page_id = publisher.FACEBOOK_PAGE_ID

    def tearDown(self):
        publisher.FACEBOOK_PAGE_TOKEN = self._orig_token
        publisher.FACEBOOK_PAGE_ID = self._orig_page_id

    def test_unconfigured_credentials_scenarios(self):
        """Verify semi_auto is returned for empty, whitespace, and None combinations."""
        credential_combos = [
            ("", ""),
            (None, None),
            ("   ", "   "),
            ("valid_token", ""),
            ("", "valid_page_id"),
            (None, "12345"),
            ("valid_token", None),
        ]
        post = {
            "caption": "Fallo relevante sobre derecho laboral",
            "caratula_path": "output/test.png"
        }
        for token, page_id in credential_combos:
            publisher.FACEBOOK_PAGE_TOKEN = token
            publisher.FACEBOOK_PAGE_ID = page_id
            res = publisher.publicar_facebook(post)
            self.assertEqual(res["status"], "semi_auto")
            self.assertEqual(res["red"], "facebook")
            self.assertEqual(res["modo"], "semi_auto")
            self.assertEqual(len(res["pasos"]), 5)

    def test_facebook_5_step_checklist_content(self):
        """Check all 5 steps contain required guidance (1:1, Facebook, Página, Copy, Publicá)."""
        post = {
            "caption": "Importante fallo de la CSJN.",
            "caratulas": {"1:1": "output/caso_1x1.png", "4:5": "output/caso_4x5.png"}
        }
        publisher.FACEBOOK_PAGE_TOKEN = ""
        publisher.FACEBOOK_PAGE_ID = ""
        res = publisher.publicar_facebook(post)

        pasos = res["pasos"]
        self.assertEqual(len(pasos), 5)
        self.assertIn("1:1", pasos[0])
        self.assertTrue("facebook" in pasos[1].lower() or "página" in pasos[1].lower() or "pagina" in pasos[1].lower())
        self.assertTrue("crear" in pasos[2].lower() or "foto" in pasos[2].lower())
        self.assertTrue("copy" in pasos[3].lower() or "descripción" in pasos[3].lower() or "texto" in pasos[3].lower())
        self.assertTrue("publicá" in pasos[4].lower() or "publica" in pasos[4].lower())

    def test_image_path_resolution_priorities_for_facebook(self):
        """
        Verify image path resolution strictly prioritizes 1:1 format for Facebook:
        1:1 > 4:5 > caratula_path > imagen_path
        """
        # Case A: Dict with 1:1 and 4:5
        p1 = {"caratulas": {"1:1": "path/1x1.png", "4:5": "path/4x5.png"}}
        self.assertEqual(publisher._get_imagen_path_para_red(p1, "facebook"), "path/1x1.png")

        # Case B: Dict with only 4:5
        p2 = {"caratulas": {"4:5": "path/4x5.png"}}
        self.assertEqual(publisher._get_imagen_path_para_red(p2, "facebook"), "path/4x5.png")

        # Case C: JSON string caratulas
        p3 = {"caratulas": json.dumps({"1:1": "path/json_1x1.png", "9:16": "path/json_9x16.png"})}
        self.assertEqual(publisher._get_imagen_path_para_red(p3, "facebook"), "path/json_1x1.png")

        # Case D: JSON string with caratulas_json key
        p4 = {"caratulas_json": json.dumps({"1:1": "path/json2_1x1.png"})}
        self.assertEqual(publisher._get_imagen_path_para_red(p4, "facebook"), "path/json2_1x1.png")

        # Case E: Malformed JSON string fallback to caratula_path
        p5 = {"caratulas": "{invalid json", "caratula_path": "path/fallback.png"}
        self.assertEqual(publisher._get_imagen_path_para_red(p5, "facebook"), "path/fallback.png")

        # Case F: No caratulas, fallback to imagen_path
        p6 = {"imagen_path": "path/legacy_img.png"}
        self.assertEqual(publisher._get_imagen_path_para_red(p6, "facebook"), "path/legacy_img.png")


class TestFacebookPublisherBinaryMultipartEmpirical(unittest.TestCase):
    """
    Stress-testing binary multipart upload payload construction, mock network calls,
    response translation, and file descriptor lifecycle.
    """

    def setUp(self):
        self._orig_token = publisher.FACEBOOK_PAGE_TOKEN
        self._orig_page_id = publisher.FACEBOOK_PAGE_ID
        publisher.FACEBOOK_PAGE_TOKEN = "EAAGtesttoken123"
        publisher.FACEBOOK_PAGE_ID = "998877665544"

        # Create temporary dummy image file
        self.temp_dir = tempfile.mkdtemp()
        self.test_img_path = os.path.join(self.temp_dir, "test_post_1x1.png")
        with open(self.test_img_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    def tearDown(self):
        publisher.FACEBOOK_PAGE_TOKEN = self._orig_token
        publisher.FACEBOOK_PAGE_ID = self._orig_page_id
        if os.path.exists(self.test_img_path):
            try:
                os.remove(self.test_img_path)
            except Exception:
                pass
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except Exception:
                pass

    @patch("requests.post")
    def test_binary_multipart_payload_structure(self, mock_post):
        """
        Verify that requests.post is invoked with:
        - endpoint: https://graph.facebook.com/v19.0/{page_id}/photos
        - files={'source': (filename, binary_stream, mime_type)}
        - data={'caption': caption, 'access_token': token}
        - timeout=15
        """
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_photo_123456789", "post_id": "998877665544_fb_photo_123456789"}
        mock_post.return_value = mock_resp

        post = {
            "caption": "Juicio por daños y perjuicios - Análisis jurídico.",
            "caratulas": {"1:1": self.test_img_path}
        }

        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "published")
        self.assertEqual(res["red"], "facebook")
        self.assertEqual(res["fb_post_id"], "fb_photo_123456789")
        self.assertEqual(res["modo"], "auto")

        # Verify call arguments
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args

        # 1. Endpoint
        expected_url = f"https://graph.facebook.com/v19.0/{publisher.FACEBOOK_PAGE_ID}/photos"
        self.assertEqual(call_args[0], expected_url)

        # 2. Form data
        self.assertEqual(call_kwargs["data"]["caption"], post["caption"])
        self.assertEqual(call_kwargs["data"]["access_token"], publisher.FACEBOOK_PAGE_TOKEN)

        # 3. Timeout
        self.assertEqual(call_kwargs["timeout"], 15)

        # 4. Files multipart dictionary
        self.assertIn("files", call_kwargs)
        self.assertIn("source", call_kwargs["files"])
        source_tuple = call_kwargs["files"]["source"]
        self.assertEqual(len(source_tuple), 3)

        filename, file_obj, mime_type = source_tuple
        self.assertEqual(filename, os.path.basename(self.test_img_path))
        self.assertEqual(mime_type, "image/png")

    @patch("requests.post")
    def test_meta_api_error_response_handling(self, mock_post):
        """
        Verify that when Meta returns an API error (e.g. code 190 subcode 463),
        publicar_facebook returns status='error', embeds diagnostic translation,
        and includes semi-automatic guided fallback.
        """
        meta_err = {
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
                "error_subcode": 463,
                "fbtrace_id": "A1B2C3D4E5"
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = meta_err
        mock_post.return_value = mock_resp

        post = {
            "caption": "Post de prueba",
            "caratulas": {"1:1": self.test_img_path}
        }

        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["red"], "facebook")
        self.assertEqual(res["error"], meta_err)
        self.assertIn("diagnostico", res)
        self.assertEqual(res["diagnostico"]["codigo"], 190)
        self.assertEqual(res["diagnostico"]["subcodigo"], 463)
        self.assertIn("expirado", res["diagnostico"]["diagnostico"].lower())

        # Fallback presence
        self.assertIn("fallback", res)
        self.assertEqual(res["fallback"]["status"], "semi_auto")
        self.assertEqual(len(res["fallback"]["pasos"]), 5)

    @patch("requests.post")
    def test_network_timeout_exception_handling(self, mock_post):
        """Timeout exception must be caught, translated to TIMEOUT diagnosis with fallback."""
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout while calling graph.facebook.com")

        post = {
            "caption": "Post con timeout",
            "caratulas": {"1:1": self.test_img_path}
        }

        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["red"], "facebook")
        self.assertIn("diagnostico", res)
        self.assertEqual(res["diagnostico"]["codigo"], "TIMEOUT")
        self.assertIn("fallback", res)
        self.assertEqual(res["fallback"]["status"], "semi_auto")

    @patch("requests.post")
    def test_network_connection_error_handling(self, mock_post):
        """ConnectionError exception must be caught, translated to CONNECTION_ERROR diagnosis."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to resolve graph.facebook.com")

        post = {
            "caption": "Post con error de conexión",
            "caratulas": {"1:1": self.test_img_path}
        }

        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["red"], "facebook")
        self.assertIn("diagnostico", res)
        self.assertEqual(res["diagnostico"]["codigo"], "CONNECTION_ERROR")
        self.assertIn("fallback", res)
        self.assertEqual(res["fallback"]["status"], "semi_auto")

    def test_missing_image_file_and_no_public_url(self):
        """When local image does not exist and no PUBLIC_BASE_URL, return error with fallback."""
        post = {
            "caption": "Post sin imagen",
            "caratulas": {"1:1": "output/non_existent_image_123.png"}
        }
        res = publisher.publicar_facebook(post)
        self.assertEqual(res["status"], "error")
        self.assertIn("No se encontró archivo", res["error"])
        self.assertIn("fallback", res)
        self.assertEqual(res["fallback"]["status"], "semi_auto")

    @patch("requests.post")
    def test_zero_byte_image_file_edge_case(self, mock_post):
        """A 0-byte image file must not be uploaded as a valid local file."""
        zero_byte_path = os.path.join(self.temp_dir, "empty_0byte.png")
        with open(zero_byte_path, "wb") as f:
            pass  # create 0 byte file

        post = {
            "caption": "Post con archivo vacío",
            "caratulas": {"1:1": zero_byte_path}
        }
        res = publisher.publicar_facebook(post)
        # Should detect local_file_exists as False (since getsize == 0) and fallback
        self.assertEqual(res["status"], "error")
        self.assertIn("No se encontró archivo", res["error"])
        mock_post.assert_not_called()

        if os.path.exists(zero_byte_path):
            os.remove(zero_byte_path)

    @patch("requests.post")
    def test_unicode_and_spaces_in_image_path(self, mock_post):
        """Image filenames with Unicode characters and spaces are handled correctly."""
        unicode_img_name = "fallo cámara contencioso administrativo año 2026.png"
        unicode_path = os.path.join(self.temp_dir, unicode_img_name)
        with open(unicode_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_photo_unicode_test"}
        mock_post.return_value = mock_resp

        post = {
            "caption": "Fallo con tilde y espacios",
            "caratulas": {"1:1": unicode_path}
        }
        res = publisher.publicar_facebook(post)
        self.assertEqual(res["status"], "published")
        self.assertEqual(res["fb_post_id"], "fb_photo_unicode_test")

        # Verify filename in multipart tuple
        source_tuple = mock_post.call_args[1]["files"]["source"]
        self.assertEqual(source_tuple[0], unicode_img_name)

        if os.path.exists(unicode_path):
            os.remove(unicode_path)

    @patch("requests.post")
    def test_jpeg_mime_type_detection(self, mock_post):
        """Verify .jpg / .jpeg files are assigned image/jpeg MIME type."""
        jpg_path = os.path.join(self.temp_dir, "cover.jpg")
        with open(jpg_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_jpg_123"}
        mock_post.return_value = mock_resp

        post = {"caption": "Test JPEG", "caratulas": {"1:1": jpg_path}}
        res = publisher.publicar_facebook(post)
        self.assertEqual(res["status"], "published")

        source_tuple = mock_post.call_args[1]["files"]["source"]
        self.assertEqual(source_tuple[2], "image/jpeg")

        if os.path.exists(jpg_path):
            os.remove(jpg_path)

    @patch("requests.post")
    def test_file_closure_and_descriptor_safety(self, mock_post):
        """
        Verify that binary file opened during upload is properly closed
        even if requests.post raises an exception.
        """
        mock_post.side_effect = requests.exceptions.Timeout("Timeout simulation")

        post = {"caption": "Check descriptor leak", "caratulas": {"1:1": self.test_img_path}}
        res = publisher.publicar_facebook(post)
        self.assertEqual(res["status"], "error")

        # In Windows, if a file handle is kept open, attempting to delete or overwrite it can raise PermissionError
        # Test that we can open it in write mode without error
        try:
            with open(self.test_img_path, "a+b") as test_f:
                test_f.write(b" ")
            can_write = True
        except PermissionError:
            can_write = False

        self.assertTrue(can_write, "File descriptor was leaked and remained locked by publisher!")

    @patch("requests.post")
    def test_html_non_json_error_response_502_bad_gateway(self, mock_post):
        """
        When upstream proxy or Meta returns non-JSON HTML (e.g. 502 Bad Gateway),
        JSONDecodeError is caught cleanly without crashing, returning error with fallback.
        """
        mock_resp = MagicMock()
        mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "<html>502 Bad Gateway</html>", 0)
        mock_post.return_value = mock_resp

        post = {"caption": "Post con respuesta 502", "caratulas": {"1:1": self.test_img_path}}
        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "error")
        self.assertEqual(res["red"], "facebook")
        self.assertIn("fallback", res)
        self.assertEqual(res["fallback"]["status"], "semi_auto")

    @patch("requests.post")
    def test_caption_with_none_values(self, mock_post):
        """When caption and copy_ig are both None, request succeeds without throwing."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_none_cap_123"}
        mock_post.return_value = mock_resp

        post = {"caption": None, "copy_ig": None, "caratulas": {"1:1": self.test_img_path}}
        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "published")
        self.assertEqual(res["fb_post_id"], "fb_none_cap_123")

    @patch("requests.post")
    def test_caption_with_emojis_and_long_text(self, mock_post):
        """Caption containing rich Unicode legal emojis and long text is preserved."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_emoji_123"}
        mock_post.return_value = mock_resp

        rich_caption = "⚖️🏛️ CSJN: Causa 'Vialidad' — Sentencia confirmada.\n" + ("Jurisprudencia penal.\n" * 500)
        post = {"caption": rich_caption, "caratulas": {"1:1": self.test_img_path}}
        res = publisher.publicar_facebook(post)

        self.assertEqual(res["status"], "published")
        mock_post.assert_called_once()
        sent_caption = mock_post.call_args[1]["data"]["caption"]
        self.assertEqual(sent_caption, rich_caption)

    @patch("requests.post")
    def test_public_url_fallback_when_local_absent(self, mock_post):
        """When local image does not exist but PUBLIC_BASE_URL is configured, falls back to URL upload."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "fb_url_upload_123"}
        mock_post.return_value = mock_resp

        orig_base_url = publisher.PUBLIC_BASE_URL
        try:
            publisher.PUBLIC_BASE_URL = "https://legalbot.ngrok.io"
            post = {
                "caption": "Post URL fallback",
                "caratula_path": "output/caso_remoto.png"
            }
            res = publisher.publicar_facebook(post)
            self.assertEqual(res["status"], "published")
            self.assertEqual(res["fb_post_id"], "fb_url_upload_123")

            call_kwargs = mock_post.call_args[1]
            self.assertNotIn("files", call_kwargs)
            self.assertIn("url", call_kwargs["data"])
            self.assertEqual(call_kwargs["data"]["url"], "https://legalbot.ngrok.io/output/caso_remoto.png")
        finally:
            publisher.PUBLIC_BASE_URL = orig_base_url


class TestMultiNetworkIntegrationEmpirical(unittest.TestCase):
    """
    Stress-testing publicar_en_redes with facebook and multi-channel combinations.
    """

    def test_publicar_en_redes_with_facebook_only(self):
        """publicar_en_redes with ['facebook'] invokes publicar_facebook."""
        with patch("publisher.publicar_facebook") as mock_fb:
            mock_fb.return_value = {"status": "published", "fb_post_id": "test_id"}
            post = {"caption": "Test post"}
            resultados = publisher.publicar_en_redes(post, ["facebook"])
            self.assertIn("facebook", resultados)
            self.assertEqual(resultados["facebook"]["status"], "published")
            mock_fb.assert_called_once_with(post)

    def test_publicar_en_redes_unsupported_network(self):
        """Unsupported networks return clean error status without throwing."""
        post = {"caption": "Test post"}
        resultados = publisher.publicar_en_redes(post, ["linkedin", "twitter"])
        self.assertEqual(resultados["linkedin"]["status"], "error")
        self.assertIn("no soportada", resultados["linkedin"]["error"].lower())
        self.assertEqual(resultados["twitter"]["status"], "error")


class TestConfigurationStatusEmpirical(unittest.TestCase):
    """
    Stress-testing get_status_configuracion and get_modo_red for Facebook.
    """

    def setUp(self):
        self._orig_token = publisher.FACEBOOK_PAGE_TOKEN
        self._orig_page_id = publisher.FACEBOOK_PAGE_ID

    def tearDown(self):
        publisher.FACEBOOK_PAGE_TOKEN = self._orig_token
        publisher.FACEBOOK_PAGE_ID = self._orig_page_id

    def test_facebook_configuration_permutations(self):
        cases = [
            ("", "", False, "semi_auto"),
            ("   ", "   ", False, "semi_auto"),
            ("token_only", "", False, "semi_auto"),
            ("", "page_id_only", False, "semi_auto"),
            ("valid_token", "123456", True, "auto"),
        ]
        for token, page_id, expected_configured, expected_modo in cases:
            publisher.FACEBOOK_PAGE_TOKEN = token
            publisher.FACEBOOK_PAGE_ID = page_id

            modo = publisher.get_modo_red("facebook")
            self.assertEqual(modo, expected_modo)

            status = publisher.get_status_configuracion()
            self.assertIn("facebook", status)
            self.assertEqual(status["facebook"]["configurado"], expected_configured)
            self.assertEqual(status["facebook"]["modo"], expected_modo)


if __name__ == "__main__":
    unittest.main(verbosity=2)

