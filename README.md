# ⚖️ Legal — Sistema Automatizado Jurídico (Laboral & Sucesiones)

Sistema integral con inteligencia artificial (**Google Gemini**) para monitorear sentencias, fallos judiciales y reclamos laborales / sucesiones en Argentina, extraer montos económicos de condena, redactar posts para redes sociales (Instagram, TikTok), generar guiones de video corto, links inteligentes de conversión a WhatsApp y diseñar carátulas gráficas de alto impacto.

---

## 🚀 Inicio Rápido

### 1. Instalación de dependencias
```bash
cd legal-bot
pip install -r requirements.txt
```

### 2. Configuración del entorno
Copiá el archivo `.env.example` como `.env` y agregá tu API key:
```bash
cp .env.example .env
```
Editá `.env` con tu clave de [Google AI Studio](https://aistudio.google.com/):
```env
GEMINI_API_KEY=tu_api_key_aqui
OUTPUT_DIR=output
DB_PATH=db.sqlite
```

### 3. Ejecutar el Panel Web
En Windows podés hacer doble clic en:
```text
legal-bot/abrir_panel.bat
```
O directamente desde la consola:
```bash
cd legal-bot
python server.py
```
Abrí tu navegador en **`http://localhost:5000`**.

---

## ✨ Características Principales

- **Conector Judicial e Ingesta:** Ingesta de fuentes judiciales oficiales, NinoLegal y medios de prensa jurídica con normalización de fechas y montos.
- **Doble Vertical:** Soporte completo para **Derecho Laboral** (despidos, indemnizaciones, ART, monotributo/fraude laboral) y **Sucesiones** (declaratoria de herederos, división de herencias, tracto abreviado).
- **Diseñador Gráfico Automatizado:** Creación de carátulas (1:1, 4:5 y 9:16) con tipografía adaptativa y montos destacados.
- **Copywriting y Guiones de Video:** Generación de copies empáticos para Instagram/TikTok y guiones estructurados (30-45s) con ganchos de alta retención.
- **Conversión a WhatsApp:** Enlaces dinámicos `wa.me` pre-redactados para captar consultas legales al instante.
- **Panel Web Administrativo:** Gestión integral con escaneo en vivo, filtrado temporal (24h, 7d, 30d), generación en 1 clic y ciclo de vida de publicaciones (archivar y eliminar).

---

## 📁 Estructura del Repositorio

```text
Legal/
└── legal-bot/
    ├── abrir_panel.bat          # Acceso directo para iniciar el panel
    ├── server.py                # Servidor HTTP y API REST local
    ├── main.py                  # Modo interactivo por consola
    ├── scraper.py               # Lector y normalizador de fuentes judiciales
    ├── ai_engine.py             # Motor de IA (Gemini) para análisis y copies
    ├── designer.py              # Generador de piezas gráficas
    ├── whatsapp_builder.py      # Generador de links dinámicos de WhatsApp
    ├── ninolegal_client.py      # Conector cliente NinoLegal
    ├── ninolegal_fixtures.py    # Fixtures de alta fidelidad jurídica
    ├── web/
    │   └── index.html           # Interfaz web moderna
    ├── assets/
    │   └── images/              # Fondos y recursos visuales
    ├── tests/                   # Batería completa de tests E2E
    └── requirements.txt         # Dependencias de Python
```

---

## 📄 Licencia
Este proyecto es de uso privado / desarrollo profesional.
