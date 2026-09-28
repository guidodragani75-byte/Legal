# ⚖️ Legal Bot — Panel de Control Web y Automatización Jurídica

Sistema automatizado con **Google Gemini** para monitorear sentencias, demandas y fallos laborales en Argentina, extraer montos de condena (`$24.800.000`), redactar posts para Instagram/TikTok y generar carátulas minimalistas de alto impacto.

---

## 🚀 Cómo usar el Panel Web (Recomendado)

Podés usar todo el sistema visualmente desde tu navegador:

1. **Hacé doble clic en:**
   ```text
   abrir_panel.bat
   ```
   *(O desde la terminal ejecutá `python server.py`)*

2. Se abrirá automáticamente tu navegador en **`http://localhost:5000`**.

3. **Desde el panel podés:**
   * Presionar **"🔍 Escanear Fallos y Juicios"** para buscar noticias en vivo.
   * Ver cada sentencia con su **monto en pesos**, situación del trabajador y resumen.
   * Marcar los casilleros de las noticias que te interesen.
   * Presionar **"⚡ Generar Seleccionadas"** para crear las carátulas y los textos.
   * Copiar el post con 1 clic y descargar las imágenes 1080x1080.

---

## 🛠️ Uso por Consola (Opcional)

Si preferís usarlo desde la terminal:
```bash
python main.py
```
Te listará los fallos con sus números y montos, y te preguntará cuál querés publicar.

---

## 📁 Estructura del Proyecto

```
legal-bot/
├── abrir_panel.bat      ← Acceso directo con doble clic
├── server.py            ← Servidor web local
├── main.py              ← Modo consola interactivo
├── scraper.py           ← Lector de RSS judiciales
├── ai_engine.py         ← Gemini (filtro estricto + montos + copies)
├── designer.py          ← Diseñador minimalista 1080x1080
├── web/
│   └── index.html       ← Interfaz web oscura y moderna
├── output/              ← Carátulas .png generadas e historial
└── .env                 ← Configuración de GEMINI_API_KEY
```
