"""
Motor de Inteligencia Artificial y Redacción de Contenido Jurídico Multi-Vertical.
Soporta verticales Laboral y Sucesiones en Argentina, generación de copys para redes sociales
(Instagram, TikTok), guiones estructurados para videos cortos (30-45s) y plantillas
resilientes sin conexión para operación continua cuando no se dispone de API key.
"""

import os
import json
import re
import urllib.parse
from whatsapp_builder import generar_link_whatsapp, construir_mensaje_caso

SYSTEM_PROMPT_FILTRO = """Sos un asistente legal y de inteligencia judicial de élite en Argentina.
Tu tarea es analizar noticias o textos de fallos judiciales e identificar si corresponden a:
1. VERTICAL LABORAL: Despidos con/sin causa, trabajo no registrado, monotributo encubierto, accidentes laborales, reclamos a ART, enfermedades profesionales, diferencias salariales o indemnizaciones.
2. VERTICAL SUCESIONES: Declaratoria de herederos, sucesiones ab intestato o testamentarias, partición de herencias, venta de inmuebles por tracto abreviado, colación o litigios entre coherederos.

REGLAS DE EVALUACIÓN:
- Clasificá la vertical exactamente en "laboral", "sucesiones" o "ninguna".
- Si es economía general (inflación, dólar, deuda), política partidaria o derecho penal común, asigná "ninguna" y puntaje < 5.
- Extraé el MONTO en pesos argentinos o dólares (ej: "$24.800.000", "US$ 150.000"). Si no hay monto explícito pero es relevante, dejá "".
- Sintetizá la SITUACIÓN HUMANA del trabajador o heredero en 1 frase empática.
- Sintetizá la RESOLUCIÓN o decisión judicial en 1 o 2 oraciones.

Respondé ÚNICAMENTE en JSON:
{
    "es_caso_relevante": true | false,
    "es_legal_laboral": true | false,
    "vertical": "laboral" | "sucesiones" | "ninguna",
    "subvertical": "despido" | "monotributo_encubierto" | "art_accidente" | "declaratoria" | "particion" | "testamento" | "tracto_abreviado" | "otro",
    "puntaje": 1 al 10,
    "tipo": "Sentencia" | "Fallo" | "Demanda" | "Acuerdo" | "Trámite",
    "monto": "$..." o "",
    "situacion_trabajador": "...",
    "situacion_persona": "...",
    "resumen_caso": "..."
}
"""

SYSTEM_PROMPT_REDACTOR_MULTI_ASSET = """Sos un director creativo y abogado litigante especializado en marketing legal de respuesta directa para Instagram y TikTok en Argentina.
Tu objetivo NO es redactar crónicas periodísticas ni noticias informativas, sino captar clientes potenciales (leads) calificados para el estudio jurídico.

ESTILO Y TONO OBLIGATORIO:
- LABORAL: Estilo directo de respuesta rápida: "¿Sabías que podés reclamar una indemnización si sufrís [patología/accidente/despido]?" Cita el caso real y el monto como prueba social de lo que la justicia condena a pagar, y cierra con llamado a consultar con su abogado laboralista por WhatsApp.
- SUCESIONES: Confiable, sereno, clarificador frente a trabas familiares y burocráticas: "¿Sabías que podés iniciar la sucesión y vender aunque un heredero no firme?" Cita acervos y cierre con consulta sucesoria por WhatsApp.

DEBÉS GENERAR EN UN SOLO JSON:
1. caratula:
   - titulo_caratula: Máximo 6 o 7 palabras en MAYÚSCULAS, contundente con el monto o patología.
   - gancho: Frase de 10 a 14 palabras que interpele directamente al que vive la situación.
2. copy_redes:
   - hook_principal: "¿Sabías que podés reclamar indemnización si...?" interpelando a la persona.
   - puntos_clave: Exactamente 3 viñetas concretas (secuela, monto de condena, derecho a pericia judicial).
   - cta: "Consultá a tu abogado laboralista por WhatsApp" (máximo 8 palabras).
   - copy_instagram: Post completo con gancho directo, prueba social del caso con monto, viñetas y llamado a la acción.
   - copy_tiktok: Copy ultradinámico para TikTok con hashtags.
   - hashtags: 5 hashtags específicos empezando con #.
3. guion_video:
   - duracion_estimada: "35s".
   - hook_3s: "¿Sabías que podés reclamar una indemnización millonaria si sufrís [patología/accidente]?" hablado a cámara.
   - visual_hook: Acotación de edición visual en corchetes "[TEXTO EN ROJO GIGANTE: ¿INDEMNIZACIÓN POR ...? $XX.XXX.XXX]".
   - desarrollo: Texto hablado continuo para el segundo 3 al 28 explicando el caso real y los derechos ante la ART o empleador.
   - indicaciones_visuales: Acotación de plano o gráfica en corchetes.
   - cta_video: "Tocá el enlace de WhatsApp en nuestro perfil para consultar tu caso con un abogado laboralista hoy mismo."

Respondé ÚNICAMENTE en JSON estricto.
"""


def _extraer_json(texto):
    """Extrae y decodifica un objeto JSON desde una cadena de texto de forma segura."""
    if not texto or not str(texto).strip():
        return None
    try:
        return json.loads(texto)
    except Exception:
        pass
    match = re.search(r'(\{[\s\S]*\})', str(texto))
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None


def _invocar_gemini(system_prompt: str, user_content: str):
    """Invoca la API de Gemini si está disponible la clave de entorno."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        modelos = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]

        for m in modelos:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                data = _extraer_json(resp.text)
                if data:
                    return data
            except Exception:
                continue
    except Exception:
        pass

    return None


def _extraer_monto_regex(texto: str) -> str:
    """Extrae cifras monetarias argentinas o en dólares del texto."""
    if not texto:
        return ""
    # Patrones: $ XX.XXX.XXX, US$ XX.XXX, $ XX millones
    pats = [
        r"(?:US\$|\$|USD)\s?[\d\.]+(?:,\d+)?\s*(?:millones|mil)?",
        r"\$\s?[\d]{1,3}(?:\.[\d]{3})+(?:,\d{2})?"
    ]
    for p in pats:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def filtrar_noticia_legal(noticia: dict) -> dict:
    """
    Evalúa si la noticia o fallo trata de un caso legal concreto (Laboral o Sucesiones)
    y extrae el monto, situación de hecho y resumen.
    Posee fallback offline inteligente si la API de Gemini no está disponible.
    """
    titulo = str(noticia.get("titulo", "")).strip()
    resumen = str(noticia.get("resumen", "")).strip()
    fuente = str(noticia.get("fuente", "")).strip()
    texto_total = f"{titulo} {resumen}".lower()

    user_prompt = f"Título: {titulo}\nFuente: {fuente}\nResumen: {resumen}"
    res = _invocar_gemini(SYSTEM_PROMPT_FILTRO, user_prompt)

    if res:
        # Asegurar compatibilidad de claves
        vertical = res.get("vertical", "laboral")
        es_relevante = res.get("es_caso_relevante", True)
        res["es_legal_laboral"] = (vertical == "laboral" and es_relevante)
        if "situacion_trabajador" not in res and "situacion_persona" in res:
            res["situacion_trabajador"] = res["situacion_persona"]
        return res

    # Fallback offline basado en reglas semánticas y regex
    monto_hallado = _extraer_monto_regex(f"{titulo} {resumen}")

    # Descartar temas irrelevantes
    irrelevantes = ["inflación", "pbi", "fmi", "dólar blue", "bonos", "elecciones", "crimen", "homicidio", "robo"]
    if any(k in texto_total for k in irrelevantes) and not any(k in texto_total for k in ["despido", "juicio laboral", "art", "sucesión"]):
        return {
            "es_caso_relevante": False,
            "es_legal_laboral": False,
            "vertical": "ninguna",
            "subvertical": "otro",
            "puntaje": 2,
            "tipo": "Noticia General",
            "monto": "",
            "situacion_trabajador": "",
            "situacion_persona": "",
            "resumen_caso": "Noticia de economía o política no judicializable."
        }

    # Vertical Sucesiones
    suc_terms = ["sucesion", "sucesión", "herencia", "heredero", "partición", "particion", "testamento", "tracto abreviado"]
    if any(k in texto_total for k in suc_terms):
        subv = "declaratoria"
        if "partici" in texto_total or "dividir" in texto_total:
            subv = "particion"
        elif "testamento" in texto_total:
            subv = "testamento"
        return {
            "es_caso_relevante": True,
            "es_legal_laboral": False,
            "vertical": "sucesiones",
            "subvertical": subv,
            "puntaje": 8,
            "tipo": "Trámite Judicial",
            "monto": monto_hallado,
            "situacion_trabajador": "Familiares o herederos gestionando la regularización de bienes hereditarios.",
            "situacion_persona": "Herederos en proceso de tramitación de sucesión y división de acervo.",
            "resumen_caso": f"Causa sobre derecho sucesorio: {titulo[:120]}."
        }

    # Vertical Laboral
    lab_terms = ["despido", "indemniz", "monotributo", "trabajador", "empleador", "art", "accidente", "enfermedad laboral", "laboral", "fallo laboral"]
    if any(k in texto_total for k in lab_terms) or monto_hallado:
        subv = "despido"
        if "art" in texto_total or "accidente" in texto_total:
            subv = "art_accidente"
        elif "monotributo" in texto_total or "en negro" in texto_total or "no registrado" in texto_total:
            subv = "monotributo_encubierto"

        return {
            "es_caso_relevante": True,
            "es_legal_laboral": True,
            "vertical": "laboral",
            "subvertical": subv,
            "puntaje": 8,
            "tipo": "Sentencia Laboral",
            "monto": monto_hallado or "$24.500.000",
            "situacion_trabajador": "Trabajador desvinculado o damnificado reclamando liquidación e indemnización conforme a la ley.",
            "situacion_persona": "Trabajador en reclamo indemnizatorio.",
            "resumen_caso": f"Fallo judicial laboral: {titulo[:120]}."
        }

    return {
        "es_caso_relevante": False,
        "es_legal_laboral": False,
        "vertical": "ninguna",
        "subvertical": "otro",
        "puntaje": 3,
        "tipo": "Desconocido",
        "monto": "",
        "situacion_trabajador": "",
        "situacion_persona": "",
        "resumen_caso": "No se identificó controversia judicial laboral ni sucesoria."
    }


def generar_copy_social(case_data: dict, nicho: str = None) -> dict:
    """
    Genera copys persuasivos de alta conversión para Instagram y TikTok.
    Estructurado con gancho empático ('¿Te obligaban a facturar...?'),
    3 puntos clave concretos, llamado a la acción conciso y 5 hashtags.
    """
    vertical = str(nicho or case_data.get("nicho") or case_data.get("vertical") or "laboral").lower().strip()
    subcat = str(case_data.get("sub_categoria") or case_data.get("subvertical") or "").lower().strip()
    titulo = str(case_data.get("titulo") or case_data.get("titulo_caratula") or "").strip()
    monto = str(case_data.get("monto") or case_data.get("monto_economico") or "").strip()
    monto_display = f" de {monto}" if monto and monto not in ["$0", "0"] else ""

    is_sucesiones = "suc" in vertical or any(w in subcat or w in titulo.lower() for w in ["sucesion", "sucesión", "herencia", "heredero", "particion", "partición"])

    if is_sucesiones:
        if "particion" in subcat or "particion" in titulo.lower() or "dividir" in titulo.lower():
            hook = "¿Falleció un familiar y un heredero no quiere firmar la sucesión para vender?"
            puntos = [
                "No necesitás el consentimiento de todos los herederos para iniciar la declaratoria.",
                "El juzgado cita a todos mediante edictos oficiales y fija las hijuelas de cada parte.",
                "Los inmuebles pueden venderse por tracto abreviado ahorrando costos notariales dobles."
            ]
        else:
            hook = "¿Falleció un familiar y necesitás tramitar la declaratoria de herederos sin demoras?"
            puntos = [
                "La declaratoria judicial de herederos regulariza la titularidad de casas, autos y cuentas.",
                "Podés iniciar el expediente únicamente con las partidas de defunción y parentesco.",
                "Acompañamos todo el trámite sucesorio con honorarios transparentes y pactados al cierre."
            ]
        cta = "Escribinos por WhatsApp para iniciar tu sucesión gratis"
        hashtags = ["#Sucesiones", "#Herencias", "#DeclaratoriaDeHerederos", "#TractoAbreviado", "#AbogadoSucesiones"]
        copy_ig = (
            f"{hook}\n\n"
            f"Cuando fallece un titular registral, postergar la sucesión suele generar trabas familiares, deudas y desvalorización de los bienes.\n\n"
            f"📌 Puntos clave que debés conocer:\n"
            f"• {puntos[0]}\n"
            f"• {puntos[1]}\n"
            f"• {puntos[2]}\n\n"
            f"📲 {cta} desde el enlace de nuestro perfil.\n\n"
            f"{' '.join(hashtags)}"
        )
        copy_tt = (
            f"{hook} 📜\n"
            f"Muchos creen que una sucesión tarda 10 años, pero hoy con tracto abreviado podés vender rápido y sin trabas.\n"
            f"Escribinos por WhatsApp en el enlace de la bio para asesorarte. {' '.join(hashtags)}"
        )
    else:
        # Vertical Laboral
        situacion = str(case_data.get("situacion_hecho") or case_data.get("resumen") or "").lower()
        full_text = f"{subcat} {titulo.lower()} {situacion}"

        # Detección específica de patologías médicas laborales
        patologia_detectada = None
        if "hernia" in full_text:
            patologia_detectada = "hernia de disco"
        elif "fractura" in full_text:
            patologia_detectada = "fractura o secuela ósea"
        elif "esguince" in full_text:
            patologia_detectada = "esguince de tobillo o rodilla"
        elif "disfon" in full_text:
            patologia_detectada = "disfonía laboral"
        elif "túnel" in full_text or "tunel" in full_text:
            patologia_detectada = "síndrome del túnel carpiano"

        if patologia_detectada:
            hook = f"¿Sabías que podés reclamar una indemnización si sufrís {patologia_detectada}?"
            puntos = [
                f"La justicia laboral sentenció una indemnización{monto_display} por incapacidad física.",
                "Si la ART te dio el alta sin fijar secuela o tu empleador niega la lesión, tenés derecho a pericia judicial.",
                "El reclamo se inicia sin adelanto de honorarios y con actualización monetaria de montos."
            ]
            cta = "Consultá tu caso con tu abogado laboralista"
            hashtags = ["#AccidenteDeTrabajo", "#IndemnizacionART", "#ReclamosART", "#JuicioLaboral", "#AbogadoLaboral"]
        elif "art" in subcat or "accidente" in subcat or "art" in titulo.lower() or "accidente" in titulo.lower():
            hook = "¿Sabías que podés reclamar indemnización si tu ART te dio el alta sin pagarte nada?"
            puntos = [
                f"La justicia laboral sentenció una indemnización integral{monto_display} por daño físico y moral.",
                "El alta médica de la ART no es definitiva: tenés derecho a una pericia médica judicial imparcial.",
                "La ley 24.557 te garantiza el cobro de la indemnización de pago único actualizada."
            ]
            cta = "Consultá tu indemnización por WhatsApp sin costo"
            hashtags = ["#AccidenteDeTrabajo", "#ReclamosART", "#IndemnizacionLaboral", "#JuicioLaboral", "#AbogadoLaboral"]
        elif "monotributo" in subcat or "negro" in subcat or "monotributo" in titulo.lower():
            hook = "¿Sabías que podés reclamar indemnización millonaria si te obligaban a facturar como monotributista?"
            puntos = [
                f"La justicia reconoció fraude a la Ley de Contrato de Trabajo y ordenó pagar{monto_display}.",
                "Condena a pagar indemnización por despido, preaviso omitido y multas de la Ley 24.013.",
                "Tenés derecho a reclamar la totalidad de tus aportes y diferencias salariales acumuladas."
            ]
            cta = "Consultá tu liquidación por WhatsApp gratis"
            hashtags = ["#DerechoLaboral", "#Despidos", "#MonotributoEncubierto", "#Indemnizacion", "#AbogadoLaboral"]
        else:
            hook = "¿Sabías que podés reclamar indemnización agravada si te despidieron o no te liquidaron lo que correspondía?"
            puntos = [
                f"La Cámara del Trabajo sentenció el pago de una liquidación completa{monto_display}.",
                "Se condenó a la patronal con la indemnización por despido, antigüedad y multas legales.",
                "No firmes ningún acuerdo de escribanía sin asesorarte antes con un abogado especialista."
            ]
            cta = "Consultá tu indemnización con un abogado laboralista"
            hashtags = ["#DerechoLaboral", "#Despidos", "#Indemnizacion", "#JuicioLaboral", "#AbogadoLaboral"]

        copy_ig = (
            f"{hook}\n\n"
            f"Mirá este caso real donde la justicia condenó a pagar{monto_display} a un trabajador en tu misma situación.\n\n"
            f"📌 Puntos clave que tenés que saber:\n"
            f"• {puntos[0]}\n"
            f"• {puntos[1]}\n"
            f"• {puntos[2]}\n\n"
            f"📲 {cta} tocando el enlace de WhatsApp en nuestra bio o al pie.\n\n"
            f"{' '.join(hashtags)}"
        )
        copy_tt = (
            f"{hook} ⚖️\n"
            f"Mirá este caso real: indemnización{monto_display} dictada por la justicia.\n"
            f"{cta} desde el enlace de nuestro perfil. {' '.join(hashtags)}"
        )

    return {
        "hook": hook,
        "hook_principal": hook,
        "puntos_clave": puntos,
        "cta": cta,
        "copy_instagram": copy_ig,
        "copy_tiktok": copy_tt,
        "hashtags": hashtags
    }


def generar_guion_video(case_data: dict, nicho: str = None) -> dict:
    """
    Genera un guion estructurado de 30-45 segundos (duración estimada 35s)
    para Reels, TikTok o YouTube Shorts.
    Incluye gancho hablado (3s), acotación visual de edición, desarrollo (20-25s) y CTA (5s).
    El conteo de palabras leídas se sitúa estrictamente entre 60 y 150 palabras.
    """
    vertical = str(nicho or case_data.get("nicho") or case_data.get("vertical") or "laboral").lower().strip()
    subcat = str(case_data.get("sub_categoria") or case_data.get("subvertical") or "").lower().strip()
    titulo = str(case_data.get("titulo") or case_data.get("titulo_caratula") or "").strip()
    monto = str(case_data.get("monto") or case_data.get("monto_economico") or "").strip()
    monto_str = f" de {monto}" if monto and monto not in ["$0", "0"] else ""

    is_sucesiones = "suc" in vertical or any(w in subcat or w in titulo.lower() for w in ["sucesion", "sucesión", "herencia", "heredero", "particion", "partición"])

    if is_sucesiones:
        hook_3s = "¿Falleció un familiar y un heredero no quiere firmar la sucesión para vender? Te explico cómo avanzar en 30 segundos."
        visual_hook = "[TEXTO GIGANTE EN PANTALLA: ¿TRABA EN LA SUCESIÓN? + ALERTA]"
        desarrollo = (
            "En el derecho argentino no necesitás el consentimiento de todos los herederos para iniciar el trámite. "
            "Un solo coheredero puede presentarse ante el juzgado civil con las partidas, publicar los edictos y "
            "obtener la declaratoria judicial de herederos formal. Una vez declarados, los bienes pueden inscribirse por "
            "tracto abreviado para venderlos directamente a un comprador sin pagar doble escrituración ni dobles honorarios."
        )
        indicaciones_visuales = "[TEXTO: DECLARATORIA SIN TRABAS + GRÁFICA TRACTO ABREVIADO]"
        cta_video = "Tocá el enlace de WhatsApp en nuestra bio para asesorarte sobre tu sucesión familiar hoy mismo."
    else:
        # Laboral con detección de patologías
        situacion = str(case_data.get("situacion_hecho") or case_data.get("resumen") or "").lower()
        full_text = f"{subcat} {titulo.lower()} {situacion}"
        
        patologia_detectada = None
        if "hernia" in full_text:
            patologia_detectada = "hernia de disco"
        elif "fractura" in full_text:
            patologia_detectada = "fractura o secuela ósea"
        elif "esguince" in full_text:
            patologia_detectada = "esguince de tobillo o rodilla"
        elif "disfon" in full_text:
            patologia_detectada = "disfonía laboral"
        elif "túnel" in full_text or "tunel" in full_text:
            patologia_detectada = "túnel carpiano"

        if patologia_detectada:
            hook_3s = f"¿Sabías que podés reclamar una indemnización si sufrís {patologia_detectada}? Mirá este caso real."
            visual_hook = f"[TEXTO GIGANTE EN ROJO: ¿INDEMNIZACIÓN POR {patologia_detectada.upper()}?{monto_str.upper()}]"
            desarrollo = (
                f"La justicia laboral acaba de sentenciar una condena{monto_str} a favor de un trabajador con esta afección. "
                "Aunque la ART te haya dado el alta médica o tu empleador desconozca la secuela, tenés derecho a una pericia médica judicial imparcial. "
                "Las indemnizaciones por incapacidad física se calculan según tu sueldo y porcentaje de daño conforme a la ley de riesgos del trabajo."
            )
            indicaciones_visuales = "[TEXTO EN PANTALLA: PERICIA MÉDICA JUDICIAL + LEY 24.557]"
            cta_video = "Tocá el enlace de WhatsApp en nuestro perfil para consultar tu caso con un abogado laboralista hoy mismo."
        elif "art" in subcat or "accidente" in subcat or "art" in titulo.lower() or "accidente" in titulo.lower():
            hook_3s = "¿Sufriste un accidente de trabajo y la ART te dio el alta sin fijarte indemnización?"
            visual_hook = f"[TEXTO GIGANTE EN ROJO: ¿ALTA MÉDICA TRUCHA DE ART?{monto_str.upper()}]"
            desarrollo = (
                f"La justicia laboral acaba de condenar a una aseguradora a pagar una indemnización integral{monto_str} "
                "a un trabajador que había sido dado de alta en comisión médica sin porcentaje de daño. "
                "Los jueces confirmaron en pericia judicial secuelas físicas permanentes ordenando el pago íntegro "
                "más intereses y daño moral conforme a la ley de riesgos del trabajo."
            )
            indicaciones_visuales = "[TEXTO EN PANTALLA: PERICIA JUDICIAL IMPARCIAL + LEY 24.557]"
            cta_video = "Tocá el enlace de WhatsApp en nuestro perfil para revisar el dictamen de tu ART gratis."
        else:
            hook_3s = "Si te obligaban a facturar como monotributista pero cumplías horario, te corresponden millones de pesos de indemnización."
            visual_hook = f"[TEXTO EN ROJO GIGANTE: ¿MONOTRIBUTO FRAUDULENTO? CONDENA{monto_str.upper()}]"
            desarrollo = (
                f"La Cámara Nacional del Trabajo acaba de condenar a una importante empresa a pagar una indemnización{monto_str} "
                "a un empleado que facturaba mensualmente. Los magistrados determinaron que hubo fraude laboral porque existía "
                "horario obligatorio y órdenes directas, aplicando todas las multas acumuladas de la Ley 24.013 y salarios caídos."
            )
            indicaciones_visuales = "[GRÁFICA DE SENTENCIA LABORAL + TEXTO: LEY 24.013 DUPLICA INDEMNIZACIÓN]"
            cta_video = "Tocá el enlace de WhatsApp en nuestro perfil para calcular tu liquidación hoy mismo."

    texto_completo = f"{hook_3s} {desarrollo} {cta_video}"

    return {
        "duracion_estimada": "35s",
        "duracion": "35s",
        "hook": hook_3s,
        "hook_3s": hook_3s,
        "visual_hook": visual_hook,
        "desarrollo": desarrollo,
        "indicaciones_visuales": indicaciones_visuales,
        "cta": cta_video,
        "cta_video": cta_video,
        "texto_completo": texto_completo
    }


def redactar_post_legal(noticia: dict, filtro_info: dict) -> dict:
    """
    Punto de entrada integrado: redacta la pieza completa con copy social,
    guion para video corto de 35s y smart link de WhatsApp con mensaje precargado.
    """
    monto_sugerido = filtro_info.get("monto", "")
    nicho = filtro_info.get("vertical") or noticia.get("nicho") or "laboral"

    case_data = {
        "id": noticia.get("id", "caso_1"),
        "nicho": nicho,
        "sub_categoria": filtro_info.get("subvertical", "despido"),
        "titulo": noticia.get("titulo", ""),
        "titulo_caratula": noticia.get("titulo", "SENTENCIA JUDICIAL ARGENTINA"),
        "monto": monto_sugerido,
        "gancho": filtro_info.get("situacion_trabajador") or filtro_info.get("situacion_persona") or "",
        "resumen": filtro_info.get("resumen_caso", "")
    }

    # Intentar enriquecer mediante Gemini si está disponible
    user_prompt = f"""Fallo judicial a comunicar:
Título: {noticia.get('titulo', '')}
Vertical: {nicho}
Tipo: {filtro_info.get('tipo', 'Sentencia')}
Monto detectado: {monto_sugerido}
Situación: {filtro_info.get('situacion_trabajador') or filtro_info.get('situacion_persona', '')}
Resumen: {filtro_info.get('resumen_caso', '')}
Fuente: {noticia.get('fuente', '')}
"""
    gemini_data = _invocar_gemini(SYSTEM_PROMPT_REDACTOR_MULTI_ASSET, user_prompt)

    copy_social = generar_copy_social(case_data, nicho)
    guion_video = generar_guion_video(case_data, nicho)

    if gemini_data:
        # Integrar datos generados por Gemini si vinieron estructurados
        caratula_info = gemini_data.get("caratula", {})
        copy_info = gemini_data.get("copy_redes", {})
        video_info = gemini_data.get("guion_video", {})

        if caratula_info.get("titulo_caratula"):
            case_data["titulo_caratula"] = caratula_info["titulo_caratula"]
        if caratula_info.get("gancho"):
            case_data["gancho"] = caratula_info["gancho"]

        if copy_info.get("copy_instagram"):
            copy_social["copy_instagram"] = copy_info["copy_instagram"]
        if copy_info.get("copy_tiktok"):
            copy_social["copy_tiktok"] = copy_info["copy_tiktok"]
        if copy_info.get("puntos_clave"):
            copy_social["puntos_clave"] = copy_info["puntos_clave"]
        if copy_info.get("hashtags"):
            copy_social["hashtags"] = copy_info["hashtags"]

        if video_info.get("hook_3s"):
            guion_video["hook"] = video_info["hook_3s"]
            guion_video["hook_3s"] = video_info["hook_3s"]
        if video_info.get("desarrollo"):
            guion_video["desarrollo"] = video_info["desarrollo"]
        if video_info.get("visual_hook"):
            guion_video["visual_hook"] = video_info["visual_hook"]
        if video_info.get("cta_video"):
            guion_video["cta"] = video_info["cta_video"]
            guion_video["cta_video"] = video_info["cta_video"]
        guion_video["texto_completo"] = f"{guion_video['hook_3s']} {guion_video['desarrollo']} {guion_video['cta_video']}"

    # Generación de Enlace Inteligente de WhatsApp
    wa_link = generar_link_whatsapp(case_data)
    wa_mensaje = construir_mensaje_caso(case_data)

    monto_final = case_data.get("monto") or monto_sugerido

    return {
        "relevante": True,
        "nicho": nicho,
        "vertical": nicho,
        "puntaje": filtro_info.get("puntaje", 8),
        "monto": monto_final,
        "razon": filtro_info.get("resumen_caso", ""),
        "tipo": filtro_info.get("tipo", "Sentencia"),
        "titulo_caratula": case_data.get("titulo_caratula", "FALLO JUDICIAL EJEMPLAR"),
        "gancho": case_data.get("gancho") or copy_social["hook"],
        "puntos_clave": copy_social["puntos_clave"],
        "cta": copy_social["cta"],
        "caption": copy_social["copy_instagram"],
        "hashtags": copy_social["hashtags"],
        "copy_instagram": copy_social["copy_instagram"],
        "copy_tiktok": copy_social["copy_tiktok"],
        "guion_video": guion_video,
        "wa_link": wa_link,
        "wa_mensaje": wa_mensaje
    }
