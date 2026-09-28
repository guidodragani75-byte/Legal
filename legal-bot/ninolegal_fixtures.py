"""
ninolegal_fixtures.py - High-fidelity Argentine judicial fixtures for NinoLegal.

Contains realistic judicial cases from Argentine courts (CNAT, SCBA, Juzgados Civiles)
for both Laboral (despido, ART, monotributo) and Sucesiones (declaratorias, partición, acervo),
conforming strictly to the JudicialCase schema in PROJECT.md.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any


@dataclass
class JudicialCase:
    id: str
    fuente: str  # e.g., 'ninolegal_laboral', 'ninolegal_sucesiones', 'infobae_judiciales'
    nicho: str   # 'laboral' | 'sucesiones'
    sub_categoria: str  # e.g., 'despido_sin_causa', 'accidente_art', 'declaratoria_herederos'
    titulo: str
    tribunal: str
    caratula: str
    fecha: str   # ISO-8601 YYYY-MM-DD
    fecha_timestamp: int  # Unix epoch seconds
    situacion_hecho: str
    decision_judicial: str
    monto_economico: str  # e.g. "$ 24.500.000" or "$ 120.000.000"
    monto_numerico: float
    link: str

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like subscripting case['field']."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Allow dict-like get method case.get('field')."""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert case object to standard dictionary representation."""
        return asdict(self)


# Raw fixture templates with day offsets relative to query timestamp
FIXTURE_TEMPLATES = [
    # -------------------- VERTICAL LABORAL --------------------
    {
        "id": "nl_lab_cnat_sala8_despido",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "despido_sin_causa",
        "offset_days": 0.2,  # ~5 hours ago (within 24h)
        "titulo": "CNAT Sala VIII declara nula causa de despido inventada y ordena indemnización agravada con multas",
        "tribunal": "Cámara Nacional de Apelaciones del Trabajo - Sala VIII",
        "caratula": "González, Marcelo c/ Logística Rápida S.A. s/ Despido",
        "situacion_hecho": (
            "El trabajador fue despedido con una falsa acusación de pérdida de confianza y supuesto "
            "incumplimiento tras haber intimado por escrito el pago de horas extras y diferencias "
            "salariales acumuladas a lo largo de 3 años de relación laboral continua."
        ),
        "decision_judicial": (
            "La Sala VIII revocó la sentencia de primera instancia, declaró la inexistencia de causal "
            "justificada atribuida por la patronal y condenó a la empresa a abonar la indemnización por "
            "antigüedad, preaviso omitido y los incrementos punitorios por conducta maliciosa procesal."
        ),
        "monto_economico": "$ 34.800.000",
        "monto_numerico": 34800000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cnat-sala8-gonzalez-34800",
    },
    {
        "id": "nl_lab_sanisidro_art_itinere",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "accidente_art",
        "offset_days": 1.5,  # 36 hours ago (within 7d, outside 24h)
        "titulo": "Cámara de San Isidro revoca rechazo de ART en accidente in itinere y ordena reparación integral",
        "tribunal": "Cámara de Apelaciones del Trabajo de San Isidro - Sala I",
        "caratula": "Medina, Roberto c/ Prevención ART S.A. s/ Accidente - Ley especial",
        "situacion_hecho": (
            "Un operario de depósito sufrió un siniestro vial severo en motocicleta regresando de la "
            "planta fabril hacia su vivienda (in itinere), con fracturas múltiples que dejaron secuelas "
            "incapacitantes del 22%. La aseguradora había declinado la cobertura aduciendo un desvío injustificado."
        ),
        "decision_judicial": (
            "El tribunal rechazó la defensa de la aseguradora, acreditó que el itinerario era el habitual "
            "y condenó a la ART a indemnizar la incapacidad física permanente total con aplicación de "
            "intereses moratorios y tasa activa desde la fecha de ocurrencia del infortunio."
        ),
        "monto_economico": "$ 46.300.000",
        "monto_numerico": 46300000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-sanisidro-medina-46300",
    },
    {
        "id": "nl_lab_cnat_sala5_monotributo",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "fraude_monotributo",
        "offset_days": 4.0,  # 4 days ago (within 7d)
        "titulo": "Justicia Laboral condena a empresa por simular relación de empleo mediante monotributo encubierto",
        "tribunal": "Cámara Nacional de Apelaciones del Trabajo - Sala V",
        "caratula": "Fernández, Carlos c/ Distribuidora Metropolitana S.A. s/ Despido",
        "situacion_hecho": (
            "Chofer repartidor obligado a inscribirse como monotributista y emitir facturas mensuales "
            "correlativas bajo relación exclusiva de 9 horas diarias, con órdenes jerárquicas y vestimenta "
            "corporativa provista por la firma demandada durante 4 años continuos."
        ),
        "decision_judicial": (
            "La Cámara ratificó el principio de primacía de la realidad (art. 23 LCT), sentenció el fraude "
            "laboral y condenó a la distribuidora al pago de indemnización por despido incausado con las "
            "sanciones conminatorias de los artículos 8 y 15 de la Ley Nacional de Empleo 24.013."
        ),
        "monto_economico": "$ 28.450.000",
        "monto_numerico": 28450000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cnat-sala5-fernandez-28450",
    },
    {
        "id": "nl_lab_cnat_sala10_sueldo_negro",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "trabajo_no_registrado",
        "offset_days": 12.0,  # 12 days ago (within 30d, outside 7d)
        "titulo": "Fallo condena a cadena gastronómica por pago de salarios fuera de recibo y falta de aportes",
        "tribunal": "Cámara Nacional de Apelaciones del Trabajo - Sala X",
        "caratula": "Benítez, Pablo c/ Gastronómica Centro S.A. s/ Despido",
        "situacion_hecho": (
            "Encargado de turno que cobraba más del 50% de sus haberes en efectivo sin registración contable, "
            "constatando al momento de desvincularse que la patronal había retenido los aportes provisionales "
            "a la seguridad social sin depositarlos en AFIP."
        ),
        "decision_judicial": (
            "La Sala X justificó el despido indirecto e impuso a la patronal la multa por deficiente registración "
            "(art. 10 Ley 24.013) más la sanción mensual conminatoria del art. 132 bis de la LCT por retención "
            "indebida de aportes jubilatorios."
        ),
        "monto_economico": "$ 33.600.000",
        "monto_numerico": 33600000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cnat-sala10-benitez-33600",
    },
    {
        "id": "nl_lab_tt2_sanisidro_discriminatorio",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "despido_discriminatorio",
        "offset_days": 22.0,  # 22 days ago (within 30d, outside 7d)
        "titulo": "Declaran nulo despido a empleada en tratamiento médico y disponen resarcimiento por daño moral",
        "tribunal": "Tribunal del Trabajo N° 2 de San Isidro",
        "caratula": "Albarracín, Lucía c/ Retail Sur S.R.L. s/ Despido incausado",
        "situacion_hecho": (
            "La empleada mercantil fue notificada de despido unilateral mediante carta documento mientras "
            "se encontraba cursando reposo por patología oncológica con licencia médica vigente e informada."
        ),
        "decision_judicial": (
            "El tribunal consideró que el cese configuró un acto nulo por discriminación prohibida en los "
            "términos de la Ley 23.592, haciendo lugar a una indemnización agravada con especial reparación "
            "por daño moral y sufrimiento psíquico."
        ),
        "monto_economico": "$ 21.900.000",
        "monto_numerico": 21900000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-sanisidro-albarracin-21900",
    },
    {
        "id": "nl_lab_art_hernia_disco_chofer",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "hernia_de_disco",
        "patologia": "hernia",
        "rubro": "chofer",
        "offset_days": 1.2,
        "titulo": "Condenan a ART a indemnizar hernia de disco lumbar en chofer de transporte de larga distancia",
        "tribunal": "Cámara Nacional de Apelaciones del Trabajo - Sala VII",
        "caratula": "Ramírez, Jorge c/ La Segunda ART S.A. s/ Accidente - Ley especial",
        "situacion_hecho": (
            "Chofer de camión que sufrió hernia discal L4-L5 por esfuerzos de carga y vibraciones del vehículo. "
            "La ART le otorgó el alta médica con 0% de incapacidad alegando que la lesión era degenerativa e inculpable."
        ),
        "decision_judicial": (
            "La pericia médica oficial constató nexo de causalidad laboral y 24.5% de incapacidad permanente. "
            "El tribunal condenó a la aseguradora a pagar la indemnización tarifada con actualización por RIPTE e intereses."
        ),
        "monto_economico": "$ 31.400.000",
        "monto_numerico": 31400000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cnat-ramirez-hernia-31400",
    },
    {
        "id": "nl_lab_art_esguince_repositor",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "esguince_de_tobillo",
        "patologia": "esguince",
        "rubro": "repositor",
        "offset_days": 2.8,
        "titulo": "Tribunal del Trabajo condena a ART por esguince grave de tobillo con secuelas en repositor de hipermercado",
        "tribunal": "Tribunal del Trabajo N° 3 de Morón",
        "caratula": "Sosa, Esteban c/ Galeno ART S.A. s/ Accidente de trabajo",
        "situacion_hecho": (
            "Repositor que pisó un desnivel resbaladizo en depósito sufriendo esguince grado III de tobillo derecho "
            "con rotura parcial de ligamentos. La ART cerró el tratamiento kinesiológico sin otorgar porcentaje indemnizatorio."
        ),
        "decision_judicial": (
            "La sentencia determinó inestabilidad articular crónica con 16% de incapacidad física parcial y permanente, "
            "ordenando a la aseguradora el depósito judicial inmediato del resarcimiento con costas."
        ),
        "monto_economico": "$ 17.850.000",
        "monto_numerico": 17850000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-tt3-moron-sosa-esguince-17850",
    },
    {
        "id": "nl_lab_art_fractura_operario",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "fractura",
        "patologia": "fractura",
        "rubro": "operario",
        "offset_days": 3.5,
        "titulo": "Histórico fallo condena a ART por fractura múltiple de muñeca en operario metalúrgico",
        "tribunal": "Cámara del Trabajo de Córdoba - Sala I",
        "caratula": "Peralta, Néstor c/ Federación Patronal ART S.A. s/ Incapacidad laboral",
        "situacion_hecho": (
            "Operario de prensa hidráulica que sufrió fractura de radio y cúbito con desplazamiento requiriendo "
            "osteosíntesis con placa y tornillos. La aseguradora liquidó un importe irrisorio desconociendo la limitación de movilidad."
        ),
        "decision_judicial": (
            "La Justicia comprobó 32% de incapacidad total del miembro superior y condenó a la ART a abonar la suma "
            "completa de la prestación dineraria con intereses fijados según tasa activa bancaria."
        ),
        "monto_economico": "$ 42.600.000",
        "monto_numerico": 42600000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cba-peralta-fractura-42600",
    },
    {
        "id": "nl_lab_art_disfonia_docente",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "disfonia",
        "patologia": "disfonia",
        "rubro": "docente",
        "offset_days": 5.1,
        "titulo": "Justicia reconoce disfonía crónica como enfermedad profesional en docente y condena a ART",
        "tribunal": "Tribunal del Trabajo N° 1 de La Plata",
        "caratula": "Méndez, Silvina c/ Provincia ART S.A. s/ Enfermedad profesional",
        "situacion_hecho": (
            "Docente de nivel inicial con 14 años frente a grado que desarrolló hiato cordal y disfonía funcional irreversible. "
            "La Comisión Médica de la SRT había rechazado el reclamo caratulándolo como enfermedad no listada."
        ),
        "decision_judicial": (
            "El tribunal acreditó que el uso intensivo de la voz fue el factor determinante del daño laringológico, "
            "declaró la responsabilidad objetiva de la ART y fijó una indemnización integral por 19% de incapacidad vocal."
        ),
        "monto_economico": "$ 23.900.000",
        "monto_numerico": 23900000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-tt1-laplata-mendez-disfonia-23900",
    },
    {
        "id": "nl_lab_art_tunel_carpiano_cajera",
        "fuente": "ninolegal_laboral",
        "nicho": "laboral",
        "sub_categoria": "tunel_carpiano",
        "patologia": "tunel_carpiano",
        "rubro": "cajera",
        "offset_days": 6.3,
        "titulo": "Cámara Laboral ordena indemnizar síndrome de túnel carpiano bilateral en cajera de supermercado",
        "tribunal": "Cámara Nacional de Apelaciones del Trabajo - Sala III",
        "caratula": "Giménez, Romina c/ SMG ART S.A. s/ Accidente - Ley especial",
        "situacion_hecho": (
            "Cajera con jornadas continuas de escaneo repetitivo de mercadería pesada que requirió descompresión quirúrgica "
            "en ambas muñecas. La ART negó la cobertura alegando factores constitucionales extra laborales."
        ),
        "decision_judicial": (
            "La Sala III revocó el rechazo patronal, acreditó trauma acumulativo por movimientos repetitivos y otorgó "
            "el pago de indemnización por 21% de incapacidad física laboral permanente."
        ),
        "monto_economico": "$ 19.500.000",
        "monto_numerico": 19500000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/laboral-y-previsional/fallo-cnat-gimenez-tunelcarpiano-19500",
    },

    # -------------------- VERTICAL SUCESIONES --------------------
    {
        "id": "nl_suc_juzgcivil14_particion",
        "fuente": "ninolegal_sucesiones",
        "nicho": "sucesiones",
        "sub_categoria": "particion_bienes",
        "offset_days": 0.4,  # ~10 hours ago (within 24h)
        "titulo": "Juzgado Civil dicta declaratoria de herederos y homologa partición judicial de tres inmuebles",
        "tribunal": "Juzgado Nacional de Primera Instancia en lo Civil N° 14",
        "caratula": "García, Osvaldo s/ Sucesión Ab-Intestato",
        "situacion_hecho": (
            "Dos herederos forzosos y la cónyuge supérstite mantenían discrepancias sobre la valuación "
            "y atribución de 3 departamentos y cuentas bancarias dejadas por el causante sin acuerdo previo."
        ),
        "decision_judicial": (
            "El magistrado dictó sentencia de declaratoria de herederos, validó el inventario pericial del "
            "acervo hereditario y homologó el acuerdo de adjudicación en especie entre coherederos, evitando "
            "el remate judicial de los bienes de la herencia."
        ),
        "monto_economico": "$ 120.000.000",
        "monto_numerico": 120000000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones/causa-civil14-garcia-120000",
    },
    {
        "id": "nl_suc_juzgcivil6_tracto_abreviado",
        "fuente": "ninolegal_sucesiones",
        "nicho": "sucesiones",
        "sub_categoria": "tracto_abreviado",
        "offset_days": 2.5,  # 2.5 days ago (within 7d, outside 24h)
        "titulo": "Autorizan venta inmobiliaria por tracto abreviado para coherederos sin doble tributación",
        "tribunal": "Juzgado de Primera Instancia en lo Civil y Comercial N° 6 de San Martín",
        "caratula": "Rossi, Elena s/ Sucesión Testamentaria y Ab-Intestato",
        "situacion_hecho": (
            "Herederos universales con comprador interesado acordado requerían enajenar urgentemente "
            "una propiedad familiar indivisa para saldar cargas tributarias sin esperar inscripciones intermedias."
        ),
        "decision_judicial": (
            "El tribunal aprobó la venta judicial por tracto abreviado registral (art. 16 Ley 17.801), "
            "designó escribano autorizante y ordenó el libramiento de oficios para la inscripción directa a nombre del adquirente."
        ),
        "monto_economico": "$ 85.000.000",
        "monto_numerico": 85000000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones/causa-sanmartin6-rossi-85000",
    },
    {
        "id": "nl_suc_camciv_salaf_exclusion",
        "fuente": "ninolegal_sucesiones",
        "nicho": "sucesiones",
        "sub_categoria": "exclusion_conyuge",
        "offset_days": 5.0,  # 5 days ago (within 7d)
        "titulo": "Cámara Civil excluye de la herencia a cónyuge supérstite por separación de hecho prolongada",
        "tribunal": "Cámara Nacional de Apelaciones en lo Civil - Sala F",
        "caratula": "Herrera, Jorge c/ Mansilla, Marta s/ Exclusión de vocación hereditaria",
        "situacion_hecho": (
            "Los descendientes del causante acreditaron que la cónyuge supérstite llevaba separada de hecho "
            "más de 7 años sin voluntad de unirse al momento del fallecimiento, peticionando la pérdida de su porción legítima."
        ),
        "decision_judicial": (
            "La Sala F confirmó la aplicación del artículo 2437 del Código Civil y Comercial, declarando "
            "la extinción del derecho hereditario del cónyuge separado y concentrando el acervo en los hijos del causante."
        ),
        "monto_economico": "$ 160.000.000",
        "monto_numerico": 160000000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones/causa-camciv-salaf-herrera-160000",
    },
    {
        "id": "nl_suc_juzgcivil22_colacion",
        "fuente": "ninolegal_sucesiones",
        "nicho": "sucesiones",
        "sub_categoria": "declaratoria_herederos",
        "offset_days": 18.0,  # 18 days ago (within 30d, outside 7d)
        "titulo": "Sentencia de colación de donaciones anticipadas y determinación de legítima en sucesión indivisa",
        "tribunal": "Juzgado Nacional de Primera Instancia en lo Civil N° 22",
        "caratula": "Pereyra, Manuel s/ Sucesión Ab-Intestato",
        "situacion_hecho": (
            "Juicio sucesorio donde uno de los herederos había recibido una donación de propiedad en vida "
            "por parte del causante que vulneraba la porción legítima de sus coherederos forzosos."
        ),
        "decision_judicial": (
            "El tribunal ordenó colacionar el valor real actualizado del inmueble donado computándolo "
            "dentro de la masa partible y compensando económicamente a los restantes herederos en la hijuela final."
        ),
        "monto_economico": "$ 95.000.000",
        "monto_numerico": 95000000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones/causa-civil22-pereyra-95000",
    },
    {
        "id": "nl_suc_juzgcivil8_testamento_olocr",
        "fuente": "ninolegal_sucesiones",
        "nicho": "sucesiones",
        "sub_categoria": "testamento",
        "offset_days": 45.0,  # 45 days ago (outside 30d)
        "titulo": "Validez judicial de testamento y protocolización notarial de disposiciones patrimoniales",
        "tribunal": "Juzgado Nacional de Primera Instancia en lo Civil N° 8",
        "caratula": "Duarte, Carlos s/ Sucesión Testamentaria",
        "situacion_hecho": (
            "Presentación de instrumento testamentario por acto público disponiendo de la porción disponible "
            "del causante en favor de una fundación de bien público sin afectar la legítima de herederos."
        ),
        "decision_judicial": (
            "Sentencia aprobatoria del testamento en cuanto a sus formas extrínsecas y orden de protocolización "
            "notarial e inscripción de legados con cancelación de cargas hereditarias."
        ),
        "monto_economico": "$ 72.000.000",
        "monto_numerico": 72000000.0,
        "link": "https://ninolegal.com/dashboard/assistants/legal/familia-y-sucesiones/causa-civil8-duarte-72000",
    },
]


def get_fixtures(
    nicho: Optional[str] = None,
    max_age_days: Optional[float] = None,
    base_time: Optional[datetime] = None,
    vertical: Optional[str] = None,
    patologia: Optional[str] = None,
    rubro: Optional[str] = None,
    excluir_ids: Optional[List[str]] = None,
    limite: Optional[int] = None,
    **kwargs: Any,
) -> List[JudicialCase]:
    """
    Returns high-fidelity judicial cases populated with dynamic timestamps
    relative to base_time, with multi-dimensional filtering (nicho, patologia, rubro, exclusion).
    """
    if vertical and not nicho:
        nicho = vertical

    if base_time is None:
        base_time = datetime.now(timezone.utc)
    base_ts = int(base_time.timestamp())

    results: List[JudicialCase] = []
    excluir_set = set(excluir_ids or [])

    for template in FIXTURE_TEMPLATES:
        # Exclude IDs if requested
        if template["id"] in excluir_set:
            continue

        # Filter by nicho if specified
        if nicho and nicho.lower() not in ("all", "todas", "todos", "ambos"):
            if template["nicho"] != nicho.lower():
                continue

        # Filter by patologia if specified (substring match in sub_categoria, titulo, situacion_hecho)
        if patologia and str(patologia).strip():
            pat_clean = str(patologia).strip().lower()
            text_full = f"{template.get('patologia', '')} {template.get('sub_categoria', '')} {template['titulo']} {template['situacion_hecho']}".lower()
            if pat_clean not in text_full:
                continue

        # Filter by rubro if specified
        if rubro and str(rubro).strip() and str(rubro).strip().lower() not in ("todos", "todas", "cualquiera", "all"):
            rubro_clean = str(rubro).strip().lower()
            text_rubro = f"{template.get('rubro', '')} {template['titulo']} {template['situacion_hecho']}".lower()
            if rubro_clean not in text_rubro:
                continue

        offset_days = template["offset_days"]

        # Filter by max_age_days if specified
        if max_age_days is not None and max_age_days > 0:
            if offset_days > max_age_days:
                continue

        case_dt = base_time - timedelta(days=offset_days)
        case_ts = int(case_dt.timestamp())
        case_date_str = case_dt.strftime("%Y-%m-%d")

        case = JudicialCase(
            id=template["id"],
            fuente=template["fuente"],
            nicho=template["nicho"],
            sub_categoria=template["sub_categoria"],
            titulo=template["titulo"],
            tribunal=template["tribunal"],
            caratula=template["caratula"],
            fecha=case_date_str,
            fecha_timestamp=case_ts,
            situacion_hecho=template["situacion_hecho"],
            decision_judicial=template["decision_judicial"],
            monto_economico=template["monto_economico"],
            monto_numerico=template["monto_numerico"],
            link=template["link"],
        )
        results.append(case)

        if limite and len(results) >= limite:
            break

    return results
