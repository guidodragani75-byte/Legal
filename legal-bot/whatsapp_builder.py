"""
Módulo de construcción de embudo directo y enlaces inteligentes de WhatsApp.
Genera enlaces https://wa.me/<phone>?text=<encoded_msg> con mensajes pre-redactados
adaptados por vertical (Laboral, Sucesiones) y subcategoría de caso judicial.
"""

import os
import re
import urllib.parse

DEFAULT_PHONE = "5491100000000"


def normalize_phone(phone: str) -> str:
    """
    Normaliza el número de teléfono a dígitos E.164 limpios.
    Elimina '+', '-', '(', ')', espacios y caracteres no numéricos.
    Si está vacío o es inválido, aplica el fallback de WHATSAPP_PHONE o número demo.
    """
    if not phone or not str(phone).strip():
        env_phone = os.getenv("WHATSAPP_PHONE", DEFAULT_PHONE)
        clean_env = "".join(filter(str.isdigit, str(env_phone)))
        return clean_env if clean_env else DEFAULT_PHONE

    clean = "".join(filter(str.isdigit, str(phone)))
    if not clean:
        env_phone = os.getenv("WHATSAPP_PHONE", DEFAULT_PHONE)
        clean_env = "".join(filter(str.isdigit, str(env_phone)))
        return clean_env if clean_env else DEFAULT_PHONE

    return clean


def build_whatsapp_link(phone: str, message: str) -> str:
    """
    Construye una URL Click-to-Chat de WhatsApp con teléfono normalizado y mensaje codificado.
    """
    clean_phone = normalize_phone(phone)
    encoded_text = urllib.parse.quote(str(message or "").strip())
    return f"https://wa.me/{clean_phone}?text={encoded_text}"


def construir_mensaje_caso(case_data: dict) -> str:
    """
    Genera un mensaje pre-redactado persuasivo y empático según el nicho,
    subcategoría y monto económico del caso judicial.
    """
    if not case_data or not isinstance(case_data, dict):
        return "Hola, vi su publicación y quiero consultar mi caso legal."

    nicho = str(case_data.get("nicho") or case_data.get("vertical") or "").lower().strip()
    subcat = str(case_data.get("sub_categoria") or case_data.get("subvertical") or case_data.get("sub_categoria_caso") or "").lower().strip()
    titulo = str(case_data.get("titulo") or case_data.get("titulo_caratula") or "").strip()
    titulo_lower = titulo.lower()

    monto = str(case_data.get("monto") or case_data.get("monto_economico") or case_data.get("monto_extraido") or "").strip()
    has_monto = bool(monto and monto not in ["$0", "0", "$0.0", "None", "null", "undefined"])

    # Detección de Vertical Sucesiones
    is_sucesiones = (
        nicho in ["sucesiones", "sucesion", "familia"]
        or any(w in subcat for w in ["sucesion", "sucesión", "herencia", "heredero", "particion", "partición", "testamento", "tracto"])
        or any(w in titulo_lower for w in ["sucesion", "sucesión", "herencia", "heredero", "particion", "partición", "testamento", "tracto abreviado"])
    )

    if is_sucesiones:
        # Subcaso: Partición de bienes / conflicto entre coherederos
        if "particion" in subcat or "particion" in titulo_lower or "partición" in titulo_lower or "dividir" in titulo_lower:
            if has_monto:
                return f"Hola, tenemos bienes en herencia para dividir valuados en {monto} y quiero asesorarme sobre la partición y el trámite de sucesión."
            return "Hola, tenemos bienes en herencia para dividir y quiero asesorarme sobre la partición y el trámite de sucesión."

        # Subcaso: Declaratoria de herederos / trámite de sucesión general
        if has_monto:
            return f"Hola, quiero iniciar una declaratoria de herederos / trámite de sucesión por un acervo de {monto} y consultar los pasos a seguir."
        return "Hola, quiero iniciar una declaratoria de herederos / trámite de sucesión y consultar los plazos y costos del proceso."

    # Vertical Laboral (predeterminada o explícita)
    # Subcaso: Despido con o sin causa
    if "despido" in subcat or "despido" in titulo_lower:
        if has_monto:
            return f"Hola, vi la sentencia de {monto} por despido y quiero consultar mi caso y liquidación."
        return "Hola, vi su publicación sobre despido y quiero consultar mi caso y liquidación laboral."

    # Subcaso: Patología específica (hernia, fractura, esguince, disfonía, túnel carpiano)
    situacion = str(case_data.get("situacion_hecho") or case_data.get("resumen") or "").lower()
    full_text = f"{subcat} {titulo_lower} {situacion}"
    
    patologia_nombre = None
    if "hernia" in full_text:
        patologia_nombre = "hernia de disco"
    elif "fractura" in full_text:
        patologia_nombre = "fractura"
    elif "esguince" in full_text:
        patologia_nombre = "esguince de tobillo"
    elif "disfon" in full_text:
        patologia_nombre = "disfonía"
    elif "túnel" in full_text or "tunel" in full_text:
        patologia_nombre = "túnel carpiano"

    if patologia_nombre:
        if has_monto:
            return f"Hola, vi la indemnización de {monto} por {patologia_nombre} y quiero consultar mi caso con un abogado laboralista."
        return f"Hola, tengo un diagnóstico de {patologia_nombre} y quiero consultar con un abogado laboralista para reclamar a la ART."

    # Subcaso: Accidente de trabajo / ART / Incapacidad
    if any(w in subcat for w in ["art", "accidente", "enfermedad_profesional"]) or any(w in titulo_lower for w in ["art", "accidente", "incapacidad", "siniestro"]):
        if has_monto:
            return f"Hola, sufrí un accidente laboral / rechazo de ART y vi la sentencia de {monto}, quiero consultar mi caso e indemnización."
        return "Hola, sufrí un accidente laboral / rechazo de ART y quiero consultar cómo iniciar mi reclamo."

    # Subcaso: Monotributo encubierto / Trabajo no registrado (en negro)
    if any(w in subcat for w in ["monotributo", "negro", "no_registrado", "fraude"]) or any(w in titulo_lower for w in ["monotributo", "en negro", "no registrado", "fraude laboral"]):
        if has_monto:
            return f"Hola, trabajo bajo monotributo/en negro y vi la sentencia de {monto}, quiero asesorarme para reclamar mi indemnización."
        return "Hola, trabajo bajo monotributo/en negro y quiero asesorarme sobre mis derechos y liquidación."

    # Fallback general laboral
    if has_monto:
        return f"Hola, vi la sentencia de {monto} y quiero consultar mi caso con un abogado especialista."
    return "Hola, vi su publicación legal y quiero hacer una consulta sobre mi situación laboral."


def generar_link_whatsapp(case_data: dict, phone: str = None) -> str:
    """
    Genera el enlace inteligente completo de WhatsApp para un caso judicial determinado.
    """
    if not phone:
        phone = os.getenv("WHATSAPP_PHONE", DEFAULT_PHONE)
    mensaje = construir_mensaje_caso(case_data)
    return build_whatsapp_link(phone, mensaje)
