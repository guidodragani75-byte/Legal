"""
Módulo de diseño visual y generación de carátulas minimalistas (1080x1080 PNG).
Implementa jerarquía visual de alto impacto para redes sociales (Instagram, TikTok),
paletas cromáticas diferenciadas por vertical (Laboral y Sucesiones) y motor tipográfico
dinámico anti-desborde con presupuesto de altura y protección total contra recortes.
"""

import io
import os
import re
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageOps

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.getenv("ASSETS_DIR", os.path.join(BASE_DIR, "assets", "images"))

# Formatos soportados para redes sociales
FORMATOS = {
    "1:1": (1080, 1080),   # Feed cuadrado estándar (Instagram / Facebook)
    "4:5": (1080, 1350),   # Feed vertical optimizado (Instagram Portrait)
    "9:16": (1080, 1920)   # Pantalla completa vertical (Stories, Reels, TikTok)
}
DEFAULT_FORMATO = "1:1"

# Caché en memoria para optimizar rendimiento de re-renderizado
_IMAGE_CACHE: dict[str, Image.Image] = {}

# Paletas de color optimizadas para alto impacto editorial por vertical
PALETAS = {
    "laboral": {
        "bg": (10, 10, 12),           # Negro carbón puro (#0a0a0c)
        "accent": (250, 204, 21),      # Amarillo eléctrico / Gold (#facc15)
        "accent_label": (239, 68, 68), # Rojo / Carmesí alerta (#ef4444)
        "text_primary": (255, 255, 255),
        "text_muted": (161, 161, 170),
        "border": (39, 39, 42),
        "header_tag": "SENTENCIA LABORAL  •  ARGENTINA",
        "monto_tag": "CONDENA JUDICIAL:"
    },
    "sucesiones": {
        "bg": (12, 18, 30),           # Azul naval oscuro / Pizarra profundo (#0c121e)
        "accent": (226, 177, 106),     # Dorado champán cálido (#e2b16a)
        "accent_label": (56, 189, 248),# Azul cielo suave (#38bdf8)
        "text_primary": (248, 250, 252),
        "text_muted": (148, 163, 184),
        "border": (30, 41, 59),
        "header_tag": "SUCESIONES & HERENCIAS  •  ARGENTINA",
        "monto_tag": "PATRIMONIO EN JUEGO:"
    }
}

# Constantes retrocompatibles
BG_COLOR = (10, 10, 12)
TEXT_WHITE = (255, 255, 255)
TEXT_MUTED = (161, 161, 170)
HIGHLIGHT_COLOR = (250, 204, 21)
BORDER_SUBTLE = (39, 39, 42)


def _get_font(size: int, bold: bool = False):
    """Carga fuentes limpias sans-serif del sistema Windows con fallback seguro."""
    candidates = [
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _sanitize_text(text: str) -> str:
    """Elimina etiquetas HTML y normaliza espacios en blanco."""
    if text is None:
        return ""
    # Quitar tags HTML (ej: <script>...</script> o <b>...</b>)
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    # Colapsar espacios múltiples y saltos innecesarios
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """
    Divide el texto para que ninguna línea exceda max_width.
    Maneja palabras ultra-largas sin romper límites ni lanzar excepciones.
    """
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current_line = []

    for word in words:
        # Verificar si la palabra individual desborda el ancho total
        bbox_w = draw.textbbox((0, 0), word, font=font)
        word_w = bbox_w[2] - bbox_w[0]

        if word_w > max_width:
            # Vaciar la línea en curso
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
            # Fragmentar palabra larga carácter por carácter
            chunk = ""
            for ch in word:
                test_chunk = chunk + ch
                bb = draw.textbbox((0, 0), test_chunk, font=font)
                if (bb[2] - bb[0]) <= max_width:
                    chunk = test_chunk
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            if chunk:
                current_line = [chunk]
            continue

        test_line = " ".join(current_line + [word]) if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    max_h: int,
    start_size: int = 60,
    min_size: int = 24,
    bold: bool = True
) -> tuple[ImageFont.ImageFont, list[str], int]:
    """
    Calcula dinámicamente el tamaño de fuente decreciendo progresivamente
    para que el texto quepa en el presupuesto [max_w, max_h].
    Si a tamaño mínimo aún desborda, trunca con elipsis de forma limpia.
    """
    size = start_size
    while size >= min_size:
        font = _get_font(size, bold=bold)
        lines = _wrap_text(draw, text, font, max_w)
        line_h = int(size * 1.25)
        if len(lines) * line_h <= max_h:
            return font, lines, line_h
        size -= 2

    font = _get_font(min_size, bold=bold)
    lines = _wrap_text(draw, text, font, max_w)
    line_h = int(min_size * 1.25)

    max_lines = max(1, max_h // line_h)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > 3:
            lines[-1] = last[:-3].rstrip() + "..."
        else:
            lines[-1] = last + "..."

    return font, lines, line_h


def _detectar_vertical(contenido: dict) -> str:
    """Detecta si el caso corresponde a Laboral o Sucesiones."""
    nicho = str(
        contenido.get("nicho")
        or contenido.get("vertical")
        or contenido.get("especialidad")
        or ""
    ).lower().strip()

    if "suc" in nicho or "fam" in nicho:
        return "sucesiones"
    if "lab" in nicho:
        return "laboral"

    # Inferencia por texto en caso de no especificarse
    subcat = str(contenido.get("sub_categoria") or contenido.get("subvertical") or "").lower()
    titulo = str(contenido.get("titulo_caratula") or contenido.get("titulo") or "").lower()
    gancho = str(contenido.get("gancho") or "").lower()
    full_text = f"{subcat} {titulo} {gancho}"

    suc_keywords = ["sucesion", "sucesión", "herencia", "heredero", "particion", "partición", "testamento", "tracto abreviado"]
    if any(k in full_text for k in suc_keywords):
        return "sucesiones"

    return "laboral"


def _normalizar_formato(fmt: str | None) -> str:
    """Normaliza identificadores de formato a las claves canónicas '1:1', '4:5' o '9:16'."""
    if not fmt:
        return DEFAULT_FORMATO
    s = str(fmt).strip().lower()
    if s in ("4:5", "4x5", "feed", "portrait", "vertical_feed"):
        return "4:5"
    if s in ("9:16", "9x16", "story", "stories", "reels", "reel", "tiktok"):
        return "9:16"
    return "1:1"


def _get_layout_config(formato: str, W: int, H: int) -> dict:
    """
    Calcula parámetros de Safe Zones, tipografía y márgenes adaptativos por formato.
    - '1:1' (1080x1080): feed tradicional cuadrado.
    - '4:5' (1080x1350): feed vertical Instagram, safe zone central optimizada.
    - '9:16' (1080x1920): Stories / Reels / TikTok con respeto estricto a safe zones
      superiores (status bar / audio) e inferiores (captions / UI).
    """
    if formato == "4:5":
        return {
            "margin_x_left": 90,
            "margin_x_right": 90,
            "max_w": W - 180,
            "header_y": 145,
            "header_line_y": 195,
            "header_size": 23,
            "y_cursor_start": 245,
            "monto_label_size": 25,
            "monto_label_offset": 40,
            "monto_start_size": 96,
            "monto_min_size": 42,
            "monto_max_h": 180,
            "monto_spacing": 35,
            "title_start_size": 62,
            "title_min_size": 34,
            "title_spacing": 35,
            "title_cap_has_monto": 420,
            "title_cap_no_monto": 540,
            "hook_start_size": 32,
            "hook_min_size": 22,
            "hook_min_budget": 130,
            "footer_line_y": H - 170,
            "cta_y": H - 125,
            "cta_size": 24,
            "footer_limit_y": H - 185,
        }
    elif formato == "9:16":
        return {
            "margin_x_left": 90,
            "margin_x_right": 130,  # Margen derecho ampliado para evitar botones de TikTok/Reels
            "max_w": W - (90 + 130),
            "header_y": 270,        # Safe zone superior (Stories / TikTok)
            "header_line_y": 325,
            "header_size": 24,
            "y_cursor_start": 380,
            "monto_label_size": 26,
            "monto_label_offset": 44,
            "monto_start_size": 104,
            "monto_min_size": 46,
            "monto_max_h": 220,
            "monto_spacing": 45,
            "title_start_size": 68,
            "title_min_size": 36,
            "title_spacing": 40,
            "title_cap_has_monto": 520,
            "title_cap_no_monto": 680,
            "hook_start_size": 36,
            "hook_min_size": 24,
            "hook_min_budget": 160,
            "footer_line_y": 1560,  # Safe zone inferior
            "cta_y": 1605,
            "cta_size": 25,
            "footer_limit_y": 1540,
        }
    else:  # '1:1'
        return {
            "margin_x_left": 90,
            "margin_x_right": 90,
            "max_w": W - 180,
            "header_y": 80,
            "header_line_y": 125,
            "header_size": 22,
            "y_cursor_start": 170,
            "monto_label_size": 24,
            "monto_label_offset": 38,
            "monto_start_size": 92,
            "monto_min_size": 40,
            "monto_max_h": 150,
            "monto_spacing": 30,
            "title_start_size": 58,
            "title_min_size": 32,
            "title_spacing": 30,
            "title_cap_has_monto": 320,
            "title_cap_no_monto": 420,
            "hook_start_size": 30,
            "hook_min_size": 20,
            "hook_min_budget": 100,
            "footer_line_y": H - 140,
            "cta_y": H - 98,
            "cta_size": 23,
            "footer_limit_y": H - 150,
        }


def _cargar_imagen_fondo(ruta_o_url: str | None) -> Image.Image | None:
    """
    Carga de forma segura una imagen de fondo desde ruta local o URL pública,
    con normalización de orientación EXIF y caché en memoria.
    """
    if not ruta_o_url or not isinstance(ruta_o_url, str):
        return None

    src = ruta_o_url.strip()
    if not src or src.lower() in ("none", "null", "false", "solid", "color", "paleta"):
        return None

    if src in _IMAGE_CACHE:
        return _IMAGE_CACHE[src].copy()

    img = None
    if src.startswith("http://") or src.startswith("https://"):
        try:
            req = urllib.request.Request(
                src,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalBot/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
            raw = Image.open(io.BytesIO(data))
            raw.load()
            img = ImageOps.exif_transpose(raw)
        except Exception:
            return None
    else:
        try:
            abs_path = os.path.abspath(os.path.expanduser(src))
            if os.path.isfile(abs_path):
                raw = Image.open(abs_path)
                raw.load()
                img = ImageOps.exif_transpose(raw)
        except Exception:
            return None

    if img is not None:
        if img.mode != "RGB":
            img = img.convert("RGB")
        if len(_IMAGE_CACHE) < 50:
            _IMAGE_CACHE[src] = img.copy()
        return img

    return None


def _seleccionar_asset_tematico(vertical: str, contenido: dict) -> str | None:
    """
    Selecciona automáticamente la imagen más afín temáticamente de la biblioteca de assets
    (generación IA + stock libre) para la vertical especificada.
    """
    assets_base = globals().get("ASSETS_DIR", ASSETS_DIR)
    v_dir = os.path.join(assets_base, vertical)
    if not os.path.isdir(v_dir):
        return None

    try:
        available = [f for f in os.listdir(v_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    except Exception:
        return None

    if not available:
        return None

    subcat = str(contenido.get("sub_categoria") or contenido.get("subvertical") or "")
    titulo = str(contenido.get("titulo_caratula") or contenido.get("titulo") or "")
    gancho = str(contenido.get("gancho") or contenido.get("bajada") or "")
    situacion = str(contenido.get("situacion_hecho") or contenido.get("razon") or "")
    texto_total = f"{subcat} {titulo} {gancho} {situacion}".lower()

    if vertical == "sucesiones":
        # Temáticas sucesiones
        if any(k in texto_total for k in ["inmueble", "propiedad", "casa", "terreno", "tracto abreviado", "escritura", "departamento", "patrimonio", "lote"]):
            for cand in ["ai_patrimonio_inmuebles.jpg", "stock_propiedad_patrimonio.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["testamento", "herencia", "heredero", "legado", "fallecido", "causante", "declaratoria", "legitima", "legítima"]):
            for cand in ["ai_herencia_testamento.jpg", "stock_firma_contrato.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["particion", "partición", "conflicto", "litigio", "disputa", "juzgado civil", "colacion", "colación", "tribunal"]):
            for cand in ["ai_balanza_justicia.jpg", "stock_balanza_clasica.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["notaria", "notaría", "escribano", "escribania", "escribanía", "tramite", "trámite", "cesion", "cesión"]):
            for cand in ["ai_notaria_tramite.jpg", "stock_firma_contrato.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)

        # Fallbacks preferidos para sucesiones
        for pref in ["ai_herencia_testamento.jpg", "ai_balanza_justicia.jpg", "ai_patrimonio_inmuebles.jpg"]:
            if pref in available:
                return os.path.join(v_dir, pref)
    else:
        # Temáticas laboral
        if any(k in texto_total for k in ["accidente", "art", "siniestro", "incapacidad", "lesion", "lesión", "salud", "obra", "construccion", "construcción", "chofer", "transporte", "logistica", "logística"]):
            for cand in ["ai_accidente_art.jpg", "stock_trabajo_industria.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["despido", "indemniz", "sueldo", "salario", "liquidacion", "liquidación", "condena", "multa", "agravante", "pesos", "millon", "millón", "interes", "interés"]):
            for cand in ["ai_indemnizacion_despido.jpg", "stock_martillo_ley.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["juicio", "tribunal", "juez", "fallo", "sentencia", "camara", "cámara", "plenario", "corte", "resolucion", "resolución"]):
            for cand in ["ai_tribunal_juez.jpg", "stock_martillo_ley.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)
        if any(k in texto_total for k in ["monotributo", "factur", "oficina", "corporativo", "empresa", "banco", "teletrabajo", "home office", "dependencia"]):
            for cand in ["ai_oficina_abogado.jpg", "stock_edificio_corporativo.jpg"]:
                if cand in available:
                    return os.path.join(v_dir, cand)

        # Fallbacks preferidos para laboral
        for pref in ["ai_indemnizacion_despido.jpg", "ai_oficina_abogado.jpg", "ai_accidente_art.jpg"]:
            if pref in available:
                return os.path.join(v_dir, pref)

    return os.path.join(v_dir, available[0])


def _crear_overlay(w: int, h: int, bg_color: tuple) -> Image.Image:
    """
    Genera un overlay cinematográfico semitransparente con gradiente vertical y viñeta
    para garantizar contraste de grado editorial (WCAG AAA) sobre cualquier fotografía.
    """
    # 1. Gradiente vertical de oscuridad progresiva
    gradient_1d = Image.new("RGBA", (1, h))
    for y in range(h):
        p = y / float(h)
        if p < 0.15:
            # Zona superior (header): semi-oscuro para lectura de categoría
            a = 180 + (p / 0.15) * 25
        elif p < 0.85:
            # Zona central (monto, título y bajada): oscuro profundo de alto contraste
            a = 205 + ((p - 0.15) / 0.70) * 25
        else:
            # Zona inferior (footer / CTA): oscurecimiento máximo
            a = 230 + ((p - 0.85) / 0.15) * 15
        gradient_1d.putpixel((0, y), (bg_color[0], bg_color[1], bg_color[2], int(a)))

    overlay_v = gradient_1d.resize((w, h), Image.Resampling.BILINEAR)

    # 2. Viñeta radial suave para enfocar la lectura en el centro
    vw = 64
    vh = max(64, int(64 * (h / float(w))))
    vignette_small = Image.new("RGBA", (vw, vh))
    cx, cy = vw / 2.0, vh / 2.0
    max_dist = (cx**2 + cy**2) ** 0.5
    for vx in range(vw):
        for vy in range(vh):
            dist = ((vx - cx)**2 + (vy - cy)**2) ** 0.5
            norm = min(1.0, dist / max_dist)
            va = int((norm ** 2.2) * 50)
            vignette_small.putpixel((vx, vy), (0, 0, 0, va))
    vignette = vignette_small.resize((w, h), Image.Resampling.BICUBIC)

    return Image.alpha_composite(overlay_v, vignette)


def _aplicar_fondo_con_overlay(w: int, h: int, bg_img: Image.Image | None, bg_color: tuple) -> Image.Image:
    """
    Combina la imagen de fondo (con escalado y recorte centrado inteligente)
    con el overlay protector, o genera un fondo sólido uniforme si no hay imagen.
    """
    if bg_img is None:
        return Image.new("RGB", (w, h), bg_color)

    try:
        # Ajustar y recortar la imagen al encuadre exacto (W, H)
        bg_fitted = ImageOps.fit(bg_img, (w, h), method=Image.Resampling.LANCZOS)
        bg_rgba = bg_fitted.convert("RGBA")
        overlay = _crear_overlay(w, h, bg_color)
        composite = Image.alpha_composite(bg_rgba, overlay)
        return composite.convert("RGB")
    except Exception:
        return Image.new("RGB", (w, h), bg_color)


def _crear_overlay_infobae(w: int, h: int) -> Image.Image:
    """
    Overlay editorial estilo Infobae:
    - Zona superior: viñeta suave para asegurar lectura del kicker y fuente.
    - Zona central-alta: transparencia alta para destacar la fotografía periodística.
    - Zona media a inferior: gradiente profundo a negro carbón (#0c0d10) para alojar el titular y monto con 100% contraste.
    """
    gradient_1d = Image.new("RGBA", (1, h))
    for y in range(h):
        p = y / float(h)
        if p < 0.18:
            a = int(140 - (p / 0.18) * 80)
        elif p < 0.42:
            a = int(60 + ((p - 0.18) / 0.24) * 30)
        elif p < 0.72:
            t = (p - 0.42) / 0.30
            a = int(90 + (t ** 1.6) * 150)
        else:
            a = 248
        gradient_1d.putpixel((0, y), (12, 13, 16, a))

    return gradient_1d.resize((w, h), Image.Resampling.BILINEAR)


def _generar_caratula_infobae(
    contenido: dict,
    file_path: str,
    fmt_norm: str,
    W: int,
    H: int,
    vertical: str,
    bg_img: Image.Image | None
) -> str:
    """Renderiza una carátula editorial con el estilo periodístico de Infobae para @TuCasoLaboral."""
    if bg_img is not None:
        try:
            bg_fitted = ImageOps.fit(bg_img, (W, H), method=Image.Resampling.LANCZOS)
            bg_rgba = bg_fitted.convert("RGBA")
            overlay = _crear_overlay_infobae(W, H)
            img = Image.alpha_composite(bg_rgba, overlay).convert("RGB")
        except Exception:
            img = Image.new("RGB", (W, H), (12, 13, 16))
    else:
        img = Image.new("RGB", (W, H), (12, 13, 16))

    draw = ImageDraw.Draw(img)

    # Tratamiento del Monto
    raw_monto = contenido.get("monto")
    monto_str = _sanitize_text(raw_monto) if raw_monto is not None else ""
    has_monto = bool(monto_str and monto_str.lower() not in ["none", "null", "undefined"])

    # Configuración de márgenes y safe zones según relación de aspecto
    if fmt_norm == "1:1":
        margin_x = 75
        max_w = W - 150
        header_y = 65
        footer_y = H - 100
        y_cursor = H - 600 if has_monto else H - 500
    elif fmt_norm == "4:5":
        margin_x = 80
        max_w = W - 160
        header_y = 75
        footer_y = H - 120
        y_cursor = H - 740 if has_monto else H - 610
    else:  # 9:16 vertical TikTok / Reels
        margin_x = 90
        max_w = W - 180
        header_y = 200
        footer_y = H - 240
        y_cursor = H - 980 if has_monto else H - 840

    # 1. Cabecera / Kicker estilo Infobae
    cuenta = str(contenido.get("cuenta") or "@TuCasoLaboral").strip()
    font_brand = _get_font(22, bold=True)
    bb_brand = draw.textbbox((0, 0), cuenta, font=font_brand)
    bw = (bb_brand[2] - bb_brand[0]) + 28
    bh = 38

    ORANGE = (255, 90, 0)
    TEXT_MUTED = (209, 213, 219)

    # Pastilla de marca
    draw.rounded_rectangle(
        [margin_x, header_y, margin_x + bw, header_y + bh],
        radius=8,
        fill=ORANGE
    )
    draw.text((margin_x + 14, header_y + 7), cuenta, font=font_brand, fill=(255, 255, 255))

    # Categoría editorial
    cat_text = "•  DERECHO LABORAL" if vertical == "laboral" else "•  SUCESIONES & HERENCIAS"
    font_cat = _get_font(20, bold=True)
    draw.text((margin_x + bw + 14, header_y + 8), cat_text, font=font_cat, fill=(243, 244, 246))

    # Fuente de la noticia
    fuente = str(contenido.get("fuente") or (contenido.get("noticia") or {}).get("fuente") or "").strip()
    if fuente:
        fuente_clean = fuente.upper()
        if not fuente_clean.startswith("FUENTE"):
            fuente_str = f"FUENTE: {fuente_clean}"
        else:
            fuente_str = fuente_clean

        font_fuente = _get_font(18, bold=True)
        bb_f = draw.textbbox((0, 0), fuente_str, font=font_fuente)
        fw = bb_f[2] - bb_f[0]
        draw.text((W - margin_x - fw, header_y + 9), fuente_str, font=font_fuente, fill=(180, 185, 195))

    # Línea sutil superior
    line_y = header_y + bh + 18
    draw.line([(margin_x, line_y), (W - margin_x, line_y)], fill=(55, 60, 70), width=1)

    # 2. Tratamiento de Monto (Destacado y de Gran Impacto)
    if has_monto:
        monto_tag = "CONDENA JUDICIAL" if vertical == "laboral" else "PATRIMONIO EN JUEGO"
        accent_color = (250, 204, 21) if vertical == "laboral" else (226, 177, 106)

        # Etiqueta cápsula sobre el monto
        font_tag = _get_font(19, bold=True)
        bb_tag = draw.textbbox((0, 0), monto_tag, font=font_tag)
        tag_w = (bb_tag[2] - bb_tag[0]) + 24
        tag_h = 32
        draw.rounded_rectangle([margin_x, y_cursor, margin_x + tag_w, y_cursor + tag_h], radius=6, fill=ORANGE)
        draw.text((margin_x + 12, y_cursor + 6), monto_tag, font=font_tag, fill=(255, 255, 255))
        y_cursor += tag_h + 10

        # Monto gigante de alto impacto (adaptativo anti-desborde)
        font_monto, lines_monto, lh_monto = _fit_text(
            draw, monto_str, max_w, max_h=120, start_size=74, min_size=42, bold=True
        )
        for line in lines_monto:
            draw.text((margin_x, y_cursor), line, font=font_monto, fill=accent_color)
            y_cursor += lh_monto

        y_cursor += 16

    # 3. Titular Periodístico de Alto Impacto
    raw_titulo = contenido.get("titulo_caratula") or contenido.get("titulo")
    titulo = _sanitize_text(raw_titulo)
    if not titulo:
        titulo = "SENTENCIA LABORAL EJEMPLAR" if vertical == "laboral" else "SUCESIÓN Y DECLARATORIA DE HEREDEROS"
    titulo = titulo.upper()

    espacio_restante = max(120, (footer_y - 40) - y_cursor)
    title_max_h = min(280, int(espacio_restante * 0.58))
    hook_max_h = max(90, espacio_restante - title_max_h - 30)

    font_title, lines_title, lh_title = _fit_text(
        draw, titulo, max_w, max_h=title_max_h, start_size=56, min_size=32, bold=True
    )
    for line in lines_title:
        draw.text((margin_x, y_cursor), line, font=font_title, fill=(255, 255, 255))
        y_cursor += lh_title

    y_cursor += 18

    # 4. Bajada / Gancho explicativo
    raw_gancho = contenido.get("gancho") or contenido.get("bajada")
    gancho = _sanitize_text(raw_gancho)
    if gancho:
        font_hook, lines_hook, lh_hook = _fit_text(
            draw, gancho, max_w, max_h=hook_max_h, start_size=28, min_size=20, bold=False
        )
        for line in lines_hook:
            draw.text((margin_x, y_cursor), line, font=font_hook, fill=TEXT_MUTED)
            y_cursor += lh_hook

    # 5. Footer con CTA y red social
    draw.line([(margin_x, footer_y - 20), (W - margin_x, footer_y - 20)], fill=(55, 60, 70), width=1)

    raw_cta = contenido.get("cta") or "Escribinos por WhatsApp para analizar tu caso"
    cta_text = _sanitize_text(raw_cta)
    font_cta = _get_font(21, bold=True)
    draw.text((margin_x, footer_y), f"→  {cta_text}", font=font_cta, fill=(255, 255, 255))

    bb_wm = draw.textbbox((0, 0), cuenta, font=font_cta)
    wm_w = bb_wm[2] - bb_wm[0]
    draw.text((W - margin_x - wm_w, footer_y), cuenta, font=font_cta, fill=ORANGE)

    img.save(file_path, "PNG", quality=95)
    return file_path


def generar_caratula(
    contenido_or_monto,
    id_noticia_or_titulo="caratula",
    bajada: str = None,
    nicho: str = None,
    output_path: str = None,
    formato: str = None,
    imagen_fondo: str = None,
    aspect_ratio: str = None,
    imagen: str = None,
    estilo: str = None,
    **kwargs
) -> str:
    """
    Generador de Carátulas Minimalistas de Alto Impacto para Instagram y TikTok.
    Soporta multiformato (1:1 [1080x1080], 4:5 [1080x1350], 9:16 [1080x1920])
    con overlay cinematográfico y gradiente oscuro de alto contraste tipográfico.
    
    Firmas compatibles:
    - generar_caratula(contenido: dict, id_noticia: str, formato="1:1", imagen_fondo=...)
    - generar_caratula(monto: str, titulo: str, bajada: str, nicho: str, output_path: str, formato="1:1")
    """
    current_out_dir = globals().get("OUTPUT_DIR", OUTPUT_DIR)
    os.makedirs(current_out_dir, exist_ok=True)

    if isinstance(contenido_or_monto, dict):
        contenido = dict(contenido_or_monto)
        id_noticia = str(id_noticia_or_titulo or contenido.get("id", "caratula"))
        file_path = output_path or os.path.join(current_out_dir, f"{id_noticia}.png")
    else:
        contenido = {
            "monto": str(contenido_or_monto or "").strip(),
            "titulo_caratula": str(id_noticia_or_titulo or "").strip(),
            "gancho": str(bajada or "").strip(),
            "nicho": str(nicho or "laboral").strip()
        }
        file_path = output_path or os.path.join(current_out_dir, "caratula.png")

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    # 1. Determinar Paleta, Vertical y Formato
    vertical = _detectar_vertical(contenido)
    paleta = PALETAS.get(vertical, PALETAS["laboral"])

    raw_fmt = (
        formato
        or aspect_ratio
        or (contenido.get("formato") if isinstance(contenido, dict) else None)
        or (contenido.get("aspect_ratio") if isinstance(contenido, dict) else None)
        or kwargs.get("formato")
        or kwargs.get("aspect_ratio")
        or DEFAULT_FORMATO
    )
    fmt_norm = _normalizar_formato(raw_fmt)
    W, H = FORMATOS[fmt_norm]
    layout = _get_layout_config(fmt_norm, W, H)

    # 2. Selección de Imagen de Fondo (Parámetro -> Asset Temático -> Fallback Sólido)
    bg_source = (
        imagen_fondo
        or imagen
        or (contenido.get("imagen_fondo") if isinstance(contenido, dict) else None)
        or (contenido.get("imagen") if isinstance(contenido, dict) else None)
        or (contenido.get("background") if isinstance(contenido, dict) else None)
        or kwargs.get("imagen_fondo")
        or kwargs.get("imagen")
    )

    bg_img = None
    is_explicit_solid = isinstance(bg_source, str) and bg_source.strip().lower() in ("solid", "none", "color", "paleta")

    if not is_explicit_solid:
        if bg_source:
            bg_img = _cargar_imagen_fondo(bg_source)

        # Fallback automático a la biblioteca híbrida temática
        if bg_img is None:
            asset_path = _seleccionar_asset_tematico(vertical, contenido)
            if asset_path:
                bg_img = _cargar_imagen_fondo(asset_path)

    # 3. Despacho por estilo (Infobae / Periodístico vs Minimalista Default)
    raw_estilo = (
        estilo
        or (contenido.get("estilo") if isinstance(contenido, dict) else None)
        or (contenido.get("template") if isinstance(contenido, dict) else None)
        or kwargs.get("estilo")
        or kwargs.get("template")
        or "default"
    )
    if str(raw_estilo).strip().lower() in ("infobae", "periodistico", "editorial", "noticias"):
        return _generar_caratula_infobae(
            contenido=contenido,
            file_path=file_path,
            fmt_norm=fmt_norm,
            W=W,
            H=H,
            vertical=vertical,
            bg_img=bg_img
        )

    # 4. Composición de Fondo con Overlay Seguro (Estilo Minimalista Default)
    img = _aplicar_fondo_con_overlay(W, H, bg_img, paleta["bg"])
    draw = ImageDraw.Draw(img)

    margin_x = layout["margin_x_left"]
    margin_right = layout["margin_x_right"]
    max_w = layout["max_w"]

    # 4. Header Minimalista: Categoría y Bandera
    font_category = _get_font(layout["header_size"], bold=True)
    draw.text((margin_x, layout["header_y"]), paleta["header_tag"], font=font_category, fill=paleta["text_muted"])

    # Línea divisoria superior sutil
    draw.line([(margin_x, layout["header_line_y"]), (W - margin_right, layout["header_line_y"])], fill=paleta["border"], width=1)

    # 5. Tratamiento del Monto Económico
    raw_monto = contenido.get("monto")
    monto_str = _sanitize_text(raw_monto) if raw_monto is not None else ""
    has_monto = bool(monto_str and monto_str.lower() not in ["none", "null", "undefined"])

    y_cursor = layout["y_cursor_start"]

    if has_monto:
        # Etiqueta sobre el monto
        font_pre = _get_font(layout["monto_label_size"], bold=True)
        draw.text((margin_x, y_cursor), paleta["monto_tag"], font=font_pre, fill=paleta["text_muted"])
        y_cursor += layout["monto_label_offset"]

        # Monto destacado gigante con color de acento
        font_monto, lines_monto, lh_monto = _fit_text(
            draw, monto_str, max_w, max_h=layout["monto_max_h"], start_size=layout["monto_start_size"], min_size=layout["monto_min_size"], bold=True
        )
        for line in lines_monto:
            draw.text((margin_x, y_cursor), line, font=font_monto, fill=paleta["accent"])
            y_cursor += lh_monto

        y_cursor += layout["monto_spacing"]

    # 6. Título Principal de Impacto (adaptativo anti-desborde)
    raw_titulo = contenido.get("titulo_caratula") or contenido.get("titulo")
    titulo = _sanitize_text(raw_titulo)
    if not titulo:
        titulo = "SENTENCIA LABORAL EJEMPLAR" if vertical == "laboral" else "SUCESIÓN Y DECLARATORIA DE HEREDEROS"
    titulo = titulo.upper()

    footer_limit_y = layout["footer_limit_y"]
    espacio_restante = max(100, footer_limit_y - y_cursor)

    if has_monto:
        title_max_h = min(layout["title_cap_has_monto"], int(espacio_restante * 0.58))
        hook_max_h = max(layout["hook_min_budget"], espacio_restante - title_max_h - layout["title_spacing"])
    else:
        title_max_h = min(layout["title_cap_no_monto"], int(espacio_restante * 0.62))
        hook_max_h = max(layout["hook_min_budget"], espacio_restante - title_max_h - layout["title_spacing"])

    font_title, lines_title, lh_title = _fit_text(
        draw, titulo, max_w, max_h=title_max_h, start_size=layout["title_start_size"], min_size=layout["title_min_size"], bold=True
    )
    for line in lines_title:
        draw.text((margin_x, y_cursor), line, font=font_title, fill=paleta["text_primary"])
        y_cursor += lh_title

    y_cursor += layout["title_spacing"]

    # 7. Gancho Empático Interpelador
    raw_gancho = contenido.get("gancho") or contenido.get("bajada")
    gancho = _sanitize_text(raw_gancho)
    if gancho:
        font_hook, lines_hook, lh_hook = _fit_text(
            draw, gancho, max_w, max_h=hook_max_h, start_size=layout["hook_start_size"], min_size=layout["hook_min_size"], bold=False
        )
        for line in lines_hook:
            draw.text((margin_x, y_cursor), line, font=font_hook, fill=paleta["text_muted"])
            y_cursor += lh_hook

    # 8. Footer Minimalista con Llamado a la Acción y Safe Zones
    draw.line([(margin_x, layout["footer_line_y"]), (W - margin_right, layout["footer_line_y"])], fill=paleta["border"], width=1)

    raw_cta = contenido.get("cta")
    cta_text = _sanitize_text(raw_cta) if raw_cta is not None else ""
    if not cta_text:
        cta_text = "Escribinos por WhatsApp para analizar tu caso"

    font_cta = _get_font(layout["cta_size"], bold=True)
    cta_full = f"→  {cta_text}"
    draw.text((margin_x, layout["cta_y"]), cta_full, font=font_cta, fill=paleta["text_primary"])

    # Guardar en disco en formato PNG
    img.save(file_path, "PNG", quality=95)
    return file_path


def generar_dashboard(items_procesados: list) -> str:
    """Genera el visor web minimalista resumen.html para compatibilidad."""
    current_out_dir = globals().get("OUTPUT_DIR", OUTPUT_DIR)
    os.makedirs(current_out_dir, exist_ok=True)
    html_path = os.path.join(current_out_dir, "resumen.html")

    cards_html = []
    for item in items_procesados:
        n = item.get("noticia", {})
        a = item.get("analisis", {})
        nid = n.get("id", "post")
        img_name = f"{nid}.png"
        monto_badge = f'<span class="monto-badge">{a.get("monto", "")}</span>' if a.get("monto") else ""

        puntos_li = "".join([f"<li>{p}</li>" for p in a.get("puntos_clave", [])])
        hashtags_str = " ".join(a.get("hashtags", []))

        card = f"""
        <article class="card">
            <div class="card-visual">
                <img src="{img_name}" alt="Carátula" class="caratula-img">
                <a href="{img_name}" download class="btn-download">Descargar carátula</a>
            </div>
            <div class="card-content">
                <div class="card-header">
                    <span class="badge">⚖️ Sentencia</span>
                    {monto_badge}
                    <span class="source-tag">{n.get('fuente', 'Medio Judicial')}</span>
                </div>
                
                <h2 class="card-title">
                    <a href="{n.get('link', '#')}" target="_blank" rel="noopener">{n.get('titulo', '')}</a>
                </h2>
                
                <p class="card-reason"><strong>Resumen:</strong> {a.get('razon', '')}</p>

                <div class="key-points">
                    <strong>Puntos clave:</strong>
                    <ul>{puntos_li}</ul>
                </div>

                <div class="caption-box">
                    <div class="caption-header">
                        <span>Copy Redes</span>
                        <button class="copy-btn" onclick="copiarTexto(this)">Copiar</button>
                    </div>
                    <pre class="caption-text">{a.get('caption', '')}\n\n{hashtags_str}</pre>
                </div>
            </div>
        </article>
        """
        cards_html.append(card)

    template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal Bot — Publicaciones</title>
    <style>
        :root {{
            --bg: #0a0a0c;
            --surface: #141417;
            --border: #27272a;
            --accent: #facc15;
            --text: #f4f4f5;
            --muted: #a1a1aa;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 40px 20px; min-height: 100vh; }}
        .container {{ max-width: 1050px; margin: 0 auto; }}
        header {{ margin-bottom: 36px; border-bottom: 1px solid var(--border); padding-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.5px; }}
        .stats {{ background: var(--surface); padding: 6px 14px; border-radius: 9999px; font-size: 13px; border: 1px solid var(--border); color: var(--muted); }}
        .grid {{ display: flex; flex-direction: column; gap: 28px; }}
        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; display: grid; grid-template-columns: 320px 1fr; gap: 24px; padding: 24px; }}
        @media (max-width: 800px) {{ .card {{ grid-template-columns: 1fr; }} }}
        .card-visual {{ display: flex; flex-direction: column; gap: 12px; }}
        .caratula-img {{ width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid var(--border); }}
        .btn-download {{ display: block; text-align: center; background: #1f1f23; color: var(--text); padding: 8px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 500; border: 1px solid var(--border); }}
        .btn-download:hover {{ background: #27272a; }}
        .card-content {{ display: flex; flex-direction: column; gap: 14px; }}
        .card-header {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .badge {{ background: #27272a; color: var(--text); padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .monto-badge {{ background: rgba(250, 204, 21, 0.15); color: var(--accent); padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; border: 1px solid rgba(250, 204, 21, 0.3); }}
        .source-tag {{ color: var(--muted); font-size: 12px; }}
        .card-title a {{ color: var(--text); text-decoration: none; font-size: 18px; font-weight: 600; line-height: 1.4; }}
        .card-title a:hover {{ color: var(--accent); }}
        .card-reason {{ font-size: 14px; color: var(--muted); line-height: 1.5; }}
        .key-points {{ background: #0a0a0c; padding: 12px 16px; border-radius: 6px; font-size: 13px; border: 1px solid var(--border); }}
        .key-points ul {{ margin-left: 20px; margin-top: 6px; }}
        .caption-box {{ background: #0a0a0c; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
        .caption-header {{ background: #18181b; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-weight: 500; color: var(--muted); }}
        .copy-btn {{ background: var(--text); color: #000; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; }}
        .copy-btn:hover {{ background: #fff; }}
        .caption-text {{ padding: 12px; white-space: pre-wrap; font-size: 13px; color: #e4e4e7; max-height: 170px; overflow-y: auto; line-height: 1.5; }}
        #toast {{ position: fixed; bottom: 24px; right: 24px; background: #22c55e; color: #000; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 13px; display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚖️ Legal Bot — Publicaciones</h1>
            <div class="stats">{len(items_procesados)} listas</div>
        </header>
        <div class="grid">
            {''.join(cards_html) if cards_html else '<p style="color:var(--muted); text-align:center; padding: 40px;">No hay publicaciones seleccionadas.</p>'}
        </div>
    </div>
    <div id="toast">✅ ¡Copiado al portapapeles!</div>
    <script>
        function copiarTexto(btn) {{
            const pre = btn.closest('.caption-box').querySelector('pre');
            navigator.clipboard.writeText(pre.innerText).then(() => {{
                const toast = document.getElementById('toast');
                toast.style.display = 'block';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 2500);
            }});
        }}
    </script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(template)
    return html_path
