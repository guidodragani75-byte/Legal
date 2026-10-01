"""
publisher.py - Motor de publicación automática multi-red para Legal Bot.
Soporta: Instagram Graph API, TikTok for Business API, Facebook Graph API.
Modo degradado semi-automático cuando faltan credenciales API.
"""

import os
import json
import requests
from urllib.parse import quote


# ─── Credenciales por variable de entorno ────────────────────────────────────
INSTAGRAM_TOKEN       = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_IG_ID       = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
INSTAGRAM_CONTAINER_URL = "https://graph.facebook.com/v19.0"

TIKTOK_CLIENT_KEY     = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_ACCESS_TOKEN   = os.getenv("TIKTOK_ACCESS_TOKEN", "")

FACEBOOK_PAGE_TOKEN   = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_PAGE_ID      = os.getenv("FACEBOOK_PAGE_ID", "")

PUBLIC_BASE_URL       = os.getenv("PUBLIC_BASE_URL", "")  # ej: https://mi-servidor.ngrok.io


def get_modo_red(red: str) -> str:
    """Retorna el modo de publicación disponible para una red: 'auto' | 'semi_auto'."""
    if red == "instagram":
        return "auto" if (str(INSTAGRAM_TOKEN or "").strip() and str(INSTAGRAM_IG_ID or "").strip()) else "semi_auto"
    elif red == "tiktok":
        return "auto" if (str(TIKTOK_CLIENT_KEY or "").strip() and str(TIKTOK_ACCESS_TOKEN or "").strip()) else "semi_auto"
    elif red == "facebook":
        return "auto" if (str(FACEBOOK_PAGE_TOKEN or "").strip() and str(FACEBOOK_PAGE_ID or "").strip()) else "semi_auto"
    return "semi_auto"


def get_status_configuracion() -> dict:
    """Devuelve el estado de configuración de APIs."""
    return {
        "instagram": {
            "modo": get_modo_red("instagram"),
            "configurado": bool(str(INSTAGRAM_TOKEN or "").strip() and str(INSTAGRAM_IG_ID or "").strip())
        },
        "tiktok": {
            "modo": get_modo_red("tiktok"),
            "configurado": bool(str(TIKTOK_CLIENT_KEY or "").strip() and str(TIKTOK_ACCESS_TOKEN or "").strip())
        },
        "facebook": {
            "modo": get_modo_red("facebook"),
            "configurado": bool(str(FACEBOOK_PAGE_TOKEN or "").strip() and str(FACEBOOK_PAGE_ID or "").strip())
        }
    }


def _get_imagen_path_para_red(post: dict, red: str) -> str:
    """Elige el path de imagen óptimo según la red."""
    caratulas = post.get("caratulas") or post.get("caratulas_json") or {}
    if isinstance(caratulas, str):
        try:
            caratulas = json.loads(caratulas)
        except Exception:
            caratulas = {}

    if red == "instagram":
        return caratulas.get("4:5") or caratulas.get("1:1") or post.get("caratula_path") or post.get("imagen_path", "")
    elif red == "tiktok":
        return caratulas.get("9:16") or caratulas.get("4:5") or post.get("caratula_path") or post.get("imagen_path", "")
    elif red == "facebook":
        return caratulas.get("1:1") or caratulas.get("4:5") or post.get("caratula_path") or post.get("imagen_path", "")
    return post.get("caratula_path") or post.get("imagen_path", "")


def _get_imagen_url_publica(local_path: str) -> str:
    """Construye la URL pública de una imagen local (requiere PUBLIC_BASE_URL)."""
    if not PUBLIC_BASE_URL:
        return ""
    local_path = local_path.replace("\\", "/")
    if not local_path.startswith("output/"):
        local_path = f"output/{os.path.basename(local_path)}"
    return f"{PUBLIC_BASE_URL.rstrip('/')}/{local_path}"


# ─── Instagram (Meta Graph API) ───────────────────────────────────────────────

def publicar_instagram(post: dict) -> dict:
    """Publica una imagen en Instagram vía Meta Graph API."""
    if not INSTAGRAM_TOKEN or not INSTAGRAM_IG_ID:
        return _resultado_semi_auto(post, "instagram")

    imagen_path = _get_imagen_path_para_red(post, "instagram")
    imagen_url  = _get_imagen_url_publica(imagen_path)
    if not imagen_url:
        return {
            "status": "error",
            "red": "instagram",
            "error": "PUBLIC_BASE_URL no configurado. No se puede subir imagen sin URL pública.",
            "modo": "semi_auto"
        }

    caption = post.get("caption") or post.get("copy_ig", "")
    hashtags = post.get("hashtags") or []
    if isinstance(hashtags, str):
        try:
            hashtags = json.loads(hashtags)
        except Exception:
            hashtags = []
    if hashtags:
        caption = caption + "\n\n" + " ".join(hashtags)

    try:
        # Step 1: Crear media container
        r1 = requests.post(
            f"{INSTAGRAM_CONTAINER_URL}/{INSTAGRAM_IG_ID}/media",
            data={
                "image_url": imagen_url,
                "caption": caption,
                "access_token": INSTAGRAM_TOKEN
            },
            timeout=15
        )
        r1_data = r1.json()
        media_id = r1_data.get("id")
        if not media_id:
            return {"status": "error", "red": "instagram", "error": r1_data, "modo": "auto"}

        # Step 2: Publicar container
        r2 = requests.post(
            f"{INSTAGRAM_CONTAINER_URL}/{INSTAGRAM_IG_ID}/media_publish",
            data={
                "creation_id": media_id,
                "access_token": INSTAGRAM_TOKEN
            },
            timeout=15
        )
        r2_data = r2.json()
        ig_post_id = r2_data.get("id")
        if ig_post_id:
            return {"status": "published", "red": "instagram", "ig_media_id": ig_post_id, "modo": "auto"}
        else:
            return {"status": "error", "red": "instagram", "error": r2_data, "modo": "auto"}

    except Exception as e:
        return {"status": "error", "red": "instagram", "error": str(e), "modo": "auto"}


# ─── TikTok (Content Posting API) ────────────────────────────────────────────

def publicar_tiktok(post: dict) -> dict:
    """Publica una imagen/video en TikTok vía Content Posting API."""
    if not TIKTOK_CLIENT_KEY or not TIKTOK_ACCESS_TOKEN:
        return _resultado_semi_auto(post, "tiktok")

    imagen_path = _get_imagen_path_para_red(post, "tiktok")
    imagen_url  = _get_imagen_url_publica(imagen_path)
    if not imagen_url:
        return {
            "status": "error",
            "red": "tiktok",
            "error": "PUBLIC_BASE_URL no configurado.",
            "modo": "semi_auto"
        }

    caption = post.get("copy_tiktok") or post.get("caption") or ""

    try:
        headers = {
            "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        payload = {
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_cover_index": 0,
                "photo_images": [imagen_url]
            },
            "media_type": "PHOTO",
            "post_mode": "DIRECT_POST"
        }
        r = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/content/init/",
            headers=headers,
            json=payload,
            timeout=15
        )
        r_data = r.json()
        if r_data.get("data", {}).get("publish_id"):
            return {
                "status": "published",
                "red": "tiktok",
                "tiktok_publish_id": r_data["data"]["publish_id"],
                "modo": "auto"
            }
        else:
            return {"status": "error", "red": "tiktok", "error": r_data, "modo": "auto"}

    except Exception as e:
        return {"status": "error", "red": "tiktok", "error": str(e), "modo": "auto"}


# ─── Facebook (Graph API) ─────────────────────────────────────────────────────

def traducir_error_meta(error_info) -> dict:
    """
    Traduce errores técnicos de Meta Graph API y excepciones de red
    a diagnósticos y recomendaciones accionables en español.
    """
    if isinstance(error_info, str):
        err_lower = error_info.lower()
        if "timed out" in err_lower or "timeout" in err_lower:
            return {
                "codigo": "TIMEOUT",
                "diagnostico": "Tiempo de espera agotado al conectar con Meta Graph API.",
                "accion": "Verificá tu conexión a Internet o reintentá en unos minutos."
            }
        if "connection" in err_lower or "failed to resolve" in err_lower:
            return {
                "codigo": "CONNECTION_ERROR",
                "diagnostico": "No se pudo conectar con los servidores de Facebook (graph.facebook.com).",
                "accion": "Verificá tu conectividad de red y cortafuegos."
            }
        return {
            "codigo": "DESCONOCIDO",
            "diagnostico": error_info,
            "accion": "Revisá los logs del sistema."
        }

    err_dict = error_info.get("error", {}) if isinstance(error_info, dict) else {}
    if not err_dict and isinstance(error_info, dict):
        err_dict = error_info

    code = err_dict.get("code")
    subcode = err_dict.get("error_subcode")
    msg = str(err_dict.get("message", ""))

    if code == 190:
        if subcode == 463:
            return {
                "codigo": 190, "subcodigo": 463,
                "diagnostico": "El token de acceso de la Página de Facebook ha expirado.",
                "accion": "Generá un nuevo token en Meta Developer Portal y actualizá FACEBOOK_PAGE_ACCESS_TOKEN en .env."
            }
        elif subcode == 467:
            return {
                "codigo": 190, "subcodigo": 467,
                "diagnostico": "El token de acceso fue invalidado por cierre de sesión o revocación.",
                "accion": "Volvé a generar el token de página desde Graph API Explorer."
            }
        return {
            "codigo": 190, "subcodigo": subcode,
            "diagnostico": "Token de autenticación de Facebook inválido o caducado.",
            "accion": "Comprobá que FACEBOOK_PAGE_ACCESS_TOKEN esté configurado correctamente en .env."
        }
    elif code in (4, 17, 32, 613):
        return {
            "codigo": code, "subcodigo": subcode,
            "diagnostico": "Se alcanzó el límite de solicitudes a la API de Facebook (Rate Limit).",
            "accion": "Aguardá entre 15 y 30 minutos antes del próximo envío o utilizá el modo semi-automático."
        }
    elif code in (10, 200, 283):
        return {
            "codigo": code, "subcodigo": subcode,
            "diagnostico": "La aplicación no tiene permisos suficientes para publicar en esta Página.",
            "accion": "Verificá que el token cuente con los permisos 'pages_manage_posts' y 'pages_read_engagement'."
        }
    elif code == 100:
        return {
            "codigo": 100, "subcodigo": subcode,
            "diagnostico": "Parámetro inválido en la llamada o ID de página incorrecto.",
            "accion": "Revisá que FACEBOOK_PAGE_ID sea correcto y que el archivo de imagen sea compatible."
        }
    elif code == 368:
        return {
            "codigo": 368, "subcodigo": subcode,
            "diagnostico": "Cuenta temporalmente bloqueada por políticas de seguridad de Meta.",
            "accion": "Ingresá a Facebook directamente para comprobar advertencias en la Página."
        }
    elif code in (1, 2):
        return {
            "codigo": code, "subcodigo": subcode,
            "diagnostico": "Error interno o servicio temporalmente no disponible en los servidores de Meta.",
            "accion": "Reintentá la publicación en unos instantes."
        }

    return {
        "codigo": code or "ERROR_API",
        "subcodigo": subcode,
        "diagnostico": msg or "Error no clasificado de Meta Graph API.",
        "accion": "Consultá el detalle del error retornado por Meta."
    }


def publicar_facebook(post: dict) -> dict:
    """
    Publica una foto en Facebook vía Graph API.
    Soporta subida binaria directa multipart/form-data (sin requerir ngrok ni PUBLIC_BASE_URL).
    Si faltan credenciales, degrada limpiamente a modo semi-automático guiado.
    """
    token = str(FACEBOOK_PAGE_TOKEN or "").strip()
    page_id = str(FACEBOOK_PAGE_ID or "").strip()

    if not token or not page_id:
        return _resultado_semi_auto(post, "facebook")

    imagen_path = _get_imagen_path_para_red(post, "facebook")
    caption = post.get("caption") or post.get("copy_ig", "")

    local_file_exists = bool(imagen_path and os.path.isfile(imagen_path) and os.path.getsize(imagen_path) > 0)
    imagen_url = _get_imagen_url_publica(imagen_path) if imagen_path else ""

    endpoint = f"https://graph.facebook.com/v19.0/{page_id}/photos"

    try:
        if local_file_exists:
            mime_type = "image/png" if imagen_path.lower().endswith(".png") else "image/jpeg"
            filename = os.path.basename(imagen_path) or "caratula_1x1.png"
            with open(imagen_path, "rb") as f:
                files = {"source": (filename, f, mime_type)}
                data = {
                    "caption": caption,
                    "access_token": token
                }
                r = requests.post(endpoint, data=data, files=files, timeout=15)
        elif imagen_url:
            data = {
                "url": imagen_url,
                "caption": caption,
                "access_token": token
            }
            r = requests.post(endpoint, data=data, timeout=15)
        else:
            return {
                "status": "error",
                "red": "facebook",
                "error": f"No se encontró archivo de imagen local válido ni URL pública para el post (path: '{imagen_path}').",
                "modo": "semi_auto",
                "fallback": _resultado_semi_auto(post, "facebook")
            }

        r_data = r.json()
        if r_data.get("id"):
            return {
                "status": "published",
                "red": "facebook",
                "fb_post_id": r_data["id"],
                "modo": "auto"
            }
        else:
            diagnostico = traducir_error_meta(r_data)
            return {
                "status": "error",
                "red": "facebook",
                "error": r_data,
                "diagnostico": diagnostico,
                "modo": "auto",
                "fallback": _resultado_semi_auto(post, "facebook")
            }

    except requests.exceptions.Timeout as e:
        err_msg = f"Request to graph.facebook.com timed out: {str(e)}"
        return {
            "status": "error",
            "red": "facebook",
            "error": err_msg,
            "diagnostico": traducir_error_meta(err_msg),
            "modo": "auto",
            "fallback": _resultado_semi_auto(post, "facebook")
        }
    except requests.exceptions.ConnectionError as e:
        err_msg = f"Connection error contacting graph.facebook.com: {str(e)}"
        return {
            "status": "error",
            "red": "facebook",
            "error": err_msg,
            "diagnostico": traducir_error_meta(err_msg),
            "modo": "auto",
            "fallback": _resultado_semi_auto(post, "facebook")
        }
    except Exception as e:
        return {
            "status": "error",
            "red": "facebook",
            "error": str(e),
            "modo": "auto",
            "fallback": _resultado_semi_auto(post, "facebook")
        }


# ─── Publicador Central ───────────────────────────────────────────────────────

def publicar_en_redes(post: dict, redes: list) -> dict:
    """
    Publica un post en las redes indicadas.
    Retorna dict con resultado por red.
    """
    resultados = {}
    for red in redes:
        print(f"  📤 Publicando en {red}...")
        if red == "instagram":
            resultados["instagram"] = publicar_instagram(post)
        elif red == "tiktok":
            resultados["tiktok"] = publicar_tiktok(post)
        elif red == "facebook":
            resultados["facebook"] = publicar_facebook(post)
        else:
            resultados[red] = {"status": "error", "error": f"Red no soportada: {red}"}
        print(f"    → {resultados[red].get('status', 'unknown')}")
    return resultados


# ─── Modo Semi-Auto ───────────────────────────────────────────────────────────

def _resultado_semi_auto(post: dict, red: str) -> dict:
    """Genera resultado semi-automático con instrucciones para publicación manual."""
    formatos_red = {"instagram": "4:5", "tiktok": "9:16", "facebook": "1:1"}
    fmt = formatos_red.get(red, "4:5")
    caratulas = post.get("caratulas") or {}
    if isinstance(caratulas, str):
        try:
            caratulas = json.loads(caratulas)
        except Exception:
            caratulas = {}
    imagen_local = caratulas.get(fmt) or post.get("caratula_path") or post.get("imagen_path", "")
    copy = post.get("copy_tiktok" if red == "tiktok" else "caption") or post.get("copy_ig", "")

    pasos = {
        "instagram": [
            "1. Descargá la imagen 4:5 usando el botón ↓",
            "2. Abrí Instagram en tu celular",
            "3. Tocá + → Publicación → Seleccioná la imagen",
            "4. Pegá el copy generado en la descripción",
            "5. Agregá los hashtags y publicá"
        ],
        "tiktok": [
            "1. Descargá la imagen 9:16 usando el botón ↓",
            "2. Abrí TikTok en tu celular",
            "3. Tocá + → Foto → Seleccioná la imagen",
            "4. Pegá el copy TikTok en la descripción",
            "5. Agregá música de fondo y publicá"
        ],
        "facebook": [
            "1. Descargá la imagen 1:1 usando el botón ↓",
            "2. Abrí Facebook → Tu Página",
            "3. Crear publicación → Agregá la foto",
            "4. Pegá el copy en el texto",
            "5. Publicá en la página"
        ]
    }

    return {
        "status": "semi_auto",
        "red": red,
        "modo": "semi_auto",
        "imagen_local": imagen_local,
        "copy_sugerido": copy,
        "pasos": pasos.get(red, []),
        "mensaje": f"Publicación semi-automática: configurá las credenciales de API en .env para activar publicación automática en {red}."
    }
