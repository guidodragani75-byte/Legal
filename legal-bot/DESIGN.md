# Sistema de Diseño Premium: Legal Bot (`DESIGN.md`)

**Versión**: 2.0.0 (Definitiva y Vinculante)  
**Ámbito**: Frontend (`web/index.html`), Generador Visual (`designer.py`), Ingesta & API (`server.py`), Redes Sociales (`publisher.py`)  
**Fecha de Publicación**: 2026-10-01  
**Autoridad**: Equipo de Arquitectura de Producto Legal Bot  

---

## 1. Principios de Diseño & Filosofía Visual

### 1.1 Sobriedad Jurídica & Autoridad Institucional
Legal Bot está diseñado para estudios jurídicos de primera línea en la República Argentina que litigan en fueros de alta complejidad (Cámara Nacional de Apelaciones del Trabajo, Fuero Civil en Sucesiones, Fuero Comercial y CSJN).

La interfaz gráfica abandona definitivamente el aspecto visual recargado, de tonos oscuros genéricos o estética "gamer/hacker" (fondos negros absolutos `#0a0a0c`, amarillos flúor estridentes `#facc15`, y rojos de emergencia permanente `#ef4444`). En su lugar, adopta una estética institucional sobria inspirada en el derecho corporativo contemporáneo y las bibliotecas jurídicas clásicas:
- **Superficies**: Profundos azules marinos y pizarras oscuros (*Slate / Navy*), que transmiten serenidad analítica, reducen la fatiga visual en jornadas de litigio intensivas y aportan dimensionalidad estratificada.
- **Acentos**: Dorado legal (*Legal Gold*) y bronce champán (*Champagne Bronze*), empleados con disciplina quirúrgica únicamente para jerarquizar llamadas a la acción, estados activos y confirmaciones patrimoniales.
- **Tipografía**: Tipografía editorial con serifa (*Editorial Serif*) para títulos y cabeceras de autoridad institucional, combinada con fuentes sin serifa (*Modern Sans*) de altísima legibilidad para grillas densas, y monoespaciadas tabulares para importes pecuniarios y números de causa.

### 1.2 Trazabilidad de Estado Inmediata (Regla de los < 3 Segundos)
Un abogado o gestor de contenidos debe ser capaz de determinar con certeza absoluta si una noticia o sentencia judicial ya fue procesada/utilizada o si permanece pendiente en **menos de 3 segundos** de escaneo visual.

Para lograrlo, la grilla no se apoya en un simple texto de estado, sino en una **arquitectura sensorial de 5 capas perceptivas preatencionales**:
1. **Indicador de Borde Izquierdo**: Borde discontinuo gris pizarra (`3px dashed #64748b`) en causas pendientes vs. borde continuo dorado o bronce (`3px solid #c5a059`) en piezas generadas.
2. **Tono de Superficie de Fila**: Fondo atenuado profundo para pendientes vs. superficie elevada sólida para piezas ya convertidas en post.
3. **Ancla Visual (Columna 1)**: Icono de expediente/balanza (`⚖️` o `📄`) en caja discontinua para pendientes vs. miniatura nítida (`44x44px`) de la carátula real generada para publicaciones.
4. **Badge de Estado Semántico Dual**: Icono + Color + Texto explícito (`⏳ PENDIENTE`, `📝 BORRADOR`, `⏰ PROGRAMADO`, `✅ PUBLICADO`, `⚠️ ERROR`).
5. **Acción Primaria Contextual**: Botón de alta prominencia `⚡ Generar` para pendientes vs. utilidades neutras `📅 Programar` / `📋 Copiar` para generadas.

### 1.3 Ergonomía de 1-Clic Sin Fricción
Cada operación frecuente en la jornada del estudio jurídico debe completarse con un solo clic directo desde la propia fila de la grilla tabular:
- **Generación en 1-Clic**: Análisis jurídico con IA, redacción de copys multicanal, guion de video y renderizado de carátulas sin requerir navegación intermedia.
- **Copiado Rápido en 1-Clic**: Copiado instantáneo al portapapeles con micro-feedback táctil (cambio de icono a `✓`, texto `¡Copiado!` durante 1.500 ms y confirmación toast).
- **Inspección Lateral Sin Recarga**: Apertura suave del *Slide-over Detail Drawer* manteniendo visible el contexto de la grilla sin perder la posición de scroll.

### 1.4 Integración Equitativa Multi-Red (Instagram, TikTok, Facebook)
Facebook Pages se incorpora como un canal de primer orden con la misma dignidad visual, soporte de formato y opciones de automatización que Instagram y TikTok:
- Presencia visible de insignia de canal (`👥 FB`) en la grilla y en el drawer.
- Casilla de verificación activa por defecto en los modales de publicación y programación.
- Especificación formal para publicaciones fotográficas 1:1 vía Graph API y flujo de contingencia guiado (*Guided Fallback*) de 5 pasos en caso de ausencia de credenciales.

---

## 2. Paleta Cromática & Jerarquía de Superficies

### 2.1 Superficies Canvas & Elevadas (Navy / Slate Hierarchy)

La estructura espacial se compone de seis niveles de superficie en escala pizarra/marino profundo:

| Token CSS | Valor Hex | Equivalente HSL / RGBA | Función y Aplicación en la Interfaz |
|---|---|---|---|
| `--color-bg-canvas` | `#0b1120` | `hsl(222, 47%, 8%)` | Fondo principal (canvas) de la aplicación |
| `--color-bg-surface` | `#111827` | `hsl(220, 39%, 11%)` | Contenedor de la tabla, barras de herramientas y modales |
| `--color-bg-surface-elevated`| `#1e293b` | `hsl(215, 33%, 17%)` | Filas destacadas en hover, cuerpo del drawer lateral |
| `--color-bg-surface-card` | `#0f172a` | `hsl(222, 47%, 11%)` | Tarjetas métricas de KPI, pozos de contenido interior |
| `--color-bg-surface-hover` | `#1f293d` | `rgba(31, 41, 61, 0.90)` | Hover interactivo sobre filas de tabla y botones ghost |
| `--color-bg-surface-active`| `#26334a` | `rgba(38, 51, 74, 1.00)` | Fila seleccionada activa, solapa de navegación activa |

### 2.2 Tokens de Tipografía & Contraste (Cumplimiento WCAG 2.1 AAA / AA)

| Token CSS | Valor Hex | RGBA | Ratio vs Canvas (`#0b1120`) | Ratio vs Surface (`#111827`) | Nivel WCAG | Aplicación |
|---|---|---|---|---|---|---|
| `--color-text-primary` | `#f8fafc` | `rgba(248, 250, 252, 1)` | **17.8 : 1** | **15.4 : 1** | **AAA** | Títulos de causas, encabezados de modales, importes |
| `--color-text-secondary` | `#cbd5e1` | `rgba(203, 213, 225, 1)` | **12.2 : 1** | **10.5 : 1** | **AAA** | Extractos jurídicos, cuerpo de copys, inputs |
| `--color-text-muted` | `#94a3b8` | `rgba(148, 163, 184, 1)` | **6.7 : 1** | **5.8 : 1** | **AA** | Encabezados de columnas de tabla, fechas, fueros |
| `--color-text-dim` | `#64748b` | `rgba(100, 116, 139, 1)` | **3.8 : 1** | **3.2 : 1** | **AA (Grande)** | Micro-etiquetas, iconos inactivos, leyendas |
| `--color-text-inverse` | `#0b1120` | `rgba(11, 17, 32, 1)` | — | — | — | Texto sobre botones dorados e insignias sólidas |

### 2.3 Acentos de Marca & Derecho Corporativo (Legal Gold & Champagne Bronze)

| Token CSS | Valor Hex | RGBA / Alpha | Rol Visual y Aplicación |
|---|---|---|---|
| `--color-accent-gold` | `#c5a059` | `rgb(197, 160, 89)` | Acento primario institucional; botón CTA principal (`⚡ Generar`) |
| `--color-accent-gold-hover` | `#d4af37` | `rgb(212, 175, 55)` | Estado hover del acento dorado |
| `--color-accent-gold-active` | `#a8853b` | `rgb(168, 133, 59)` | Estado de clic/pulsación del botón primario |
| `--color-accent-gold-subtle` | — | `rgba(197, 160, 89, 0.12)` | Fondo de insignia laboral e iluminado sutil de fila |
| `--color-accent-gold-border` | — | `rgba(197, 160, 89, 0.32)` | Borde de contención para componentes de acento |
| `--color-accent-champagne` | `#e2b16a` | `rgb(226, 177, 106)` | Acento para vertical de Sucesiones & Herencias |
| `--color-accent-bronze` | `#927038` | `rgb(146, 112, 56)` | Tono bronce profundo para sellos de tribunal y marcos |

### 2.4 Tokens Semánticos de Estado (Ciclo de Vida Operativo)

| Estado | Token Nombre | Color Hex | Fondo con Transparencia | Borde de Contorno | Significado Operativo |
|---|---|---|---|---|---|
| **⚪ Pendiente** | `--color-status-pending` | `#94a3b8` | `rgba(148, 163, 184, 0.10)` | `rgba(148, 163, 184, 0.25)` | Causa escaneada en BD, sin post social generado |
| **📝 Borrador** | `--color-status-draft` | `#38bdf8` | `rgba(56, 189, 248, 0.12)` | `rgba(56, 189, 248, 0.30)` | Piezas generadas; pendiente de revisión/programación |
| **⏰ Programado** | `--color-status-scheduled`| `#fbbf24` | `rgba(251, 191, 36, 0.12)` | `rgba(251, 191, 36, 0.30)` | Encolado en cronograma con fecha y hora asignadas |
| **✅ Publicado** | `--color-status-published`| `#34d399` | `rgba(52, 211, 153, 0.12)` | `rgba(52, 211, 153, 0.30)` | Publicado en las redes sociales de destino |
| **❌ Error** | `--color-status-error` | `#f87171` | `rgba(248, 113, 113, 0.14)` | `rgba(248, 113, 113, 0.35)` | Falla en publicación vía API; requiere acción guiada |

### 2.5 Identidad de Canales de Redes Sociales (Facebook de Primer Orden)

| Canal | Token CSS de Color | Hex Marca | Fondo Tintado | Borde de Acento | Distintivo |
|---|---|---|---|---|---|
| **Facebook Pages** | `--color-channel-fb` | `#1877f2` | `rgba(24, 119, 242, 0.12)` | `rgba(24, 119, 242, 0.30)` | `👥 FB` |
| **Instagram** | `--color-channel-ig` | `#e1306c` | `rgba(225, 48, 108, 0.12)` | `rgba(225, 48, 108, 0.30)` | `📸 IG` |
| **TikTok** | `--color-channel-tt` | `#22d3ee` | `rgba(34, 211, 238, 0.12)` | `rgba(34, 211, 238, 0.30)` | `🎵 TT` |
| **WhatsApp** | `--color-channel-wa` | `#25d366` | `rgba(37, 211, 102, 0.12)` | `rgba(37, 211, 102, 0.30)` | `💬 WA` |

### 2.6 Especialidades Jurídicas / Verticales

| Especialidad Jurídica | Acento Principal | Etiqueta Canónica | Borde Tintado |
|---|---|---|---|
| **Laboral (ART, Despidos, Accidentes)** | `#c5a059` (Legal Gold) | `⚖️ Sentencia Laboral` | `rgba(197, 160, 89, 0.35)` |
| **Sucesiones & Herencias (Declaratorias)**| `#e2b16a` (Champagne Gold)| `📜 Sucesión & Herencia` | `rgba(226, 177, 106, 0.35)`|

---

### 2.7 Bloque Completo de Tokens `:root` CSS

A continuación se define el bloque maestro canónico de variables CSS para su inclusión en `web/index.html`:

```css
:root {
    /* ==========================================================================
       SUPERFICIES & FONDOS (Navy / Slate Hierarchy)
       ========================================================================== */
    --color-bg-canvas: #0b1120;
    --color-bg-surface: #111827;
    --color-bg-surface-elevated: #1e293b;
    --color-bg-surface-card: #0f172a;
    --color-bg-surface-hover: #1f293d;
    --color-bg-surface-active: #26334a;

    /* Aliases de compatibilidad retroactiva */
    --bg: var(--color-bg-canvas);
    --surface: var(--color-bg-surface);
    --surface-hover: var(--color-bg-surface-hover);
    --surface-card: var(--color-bg-surface-card);

    /* ==========================================================================
       BORDES & SEPARADORES
       ========================================================================== */
    --border-subtle: rgba(255, 255, 255, 0.07);
    --border-default: rgba(255, 255, 255, 0.12);
    --border-hover: rgba(255, 255, 255, 0.22);
    --border-accent: rgba(197, 160, 89, 0.40);
    --border-focus: rgba(197, 160, 89, 0.70);

    /* Alias de compatibilidad retroactiva */
    --border: var(--border-default);

    /* ==========================================================================
       TEXTO & PRIMER PLANO (WCAG 2.1 Compliance)
       ========================================================================== */
    --color-text-primary: #f8fafc;
    --color-text-secondary: #cbd5e1;
    --color-text-muted: #94a3b8;
    --color-text-dim: #64748b;
    --color-text-inverse: #0b1120;

    /* Aliases de compatibilidad retroactiva */
    --text: var(--color-text-primary);
    --text-muted: var(--color-text-muted);
    --text-secondary: var(--color-text-secondary);

    /* ==========================================================================
       ACENTOS CORPORATIVOS (Legal Gold & Champagne Bronze)
       ========================================================================== */
    --color-accent-gold: #c5a059;
    --color-accent-gold-hover: #d4af37;
    --color-accent-gold-active: #a8853b;
    --color-accent-gold-subtle: rgba(197, 160, 89, 0.12);
    --color-accent-gold-border: rgba(197, 160, 89, 0.32);
    --color-accent-champagne: #e2b16a;
    --color-accent-bronze: #927038;

    /* Aliases de vertical y botones primarios */
    --accent-laboral: var(--color-accent-gold);
    --accent-laboral-glow: var(--color-accent-gold-subtle);
    --accent-sucesiones: var(--color-accent-champagne);
    --accent-sucesiones-glow: rgba(226, 177, 106, 0.12);
    --primary: var(--color-accent-gold);
    --primary-hover: var(--color-accent-gold-hover);

    /* ==========================================================================
       ESTADOS SEMÁNTICOS (Trazabilidad Inmediata < 3s)
       ========================================================================== */
    --color-status-pending: #94a3b8;
    --color-status-pending-bg: rgba(148, 163, 184, 0.10);
    --color-status-pending-border: rgba(148, 163, 184, 0.25);

    --color-status-draft: #38bdf8;
    --color-status-draft-bg: rgba(56, 189, 248, 0.12);
    --color-status-draft-border: rgba(56, 189, 248, 0.30);

    --color-status-scheduled: #fbbf24;
    --color-status-scheduled-bg: rgba(251, 191, 36, 0.12);
    --color-status-scheduled-border: rgba(251, 191, 36, 0.30);

    --color-status-published: #34d399;
    --color-status-published-bg: rgba(52, 211, 153, 0.12);
    --color-status-published-border: rgba(52, 211, 153, 0.30);

    --color-status-error: #f87171;
    --color-status-error-bg: rgba(248, 113, 113, 0.14);
    --color-status-error-border: rgba(248, 113, 113, 0.35);

    /* ==========================================================================
       CANALES SOCIALES (R3 Integración Facebook de Primer Orden)
       ========================================================================== */
    --color-channel-fb: #1877f2;
    --color-channel-fb-bg: rgba(24, 119, 242, 0.12);
    --color-channel-fb-border: rgba(24, 119, 242, 0.30);

    --color-channel-ig: #e1306c;
    --color-channel-ig-bg: rgba(225, 48, 108, 0.12);
    --color-channel-ig-border: rgba(225, 48, 108, 0.30);

    --color-channel-tt: #22d3ee;
    --color-channel-tt-bg: rgba(34, 211, 238, 0.12);
    --color-channel-tt-border: rgba(34, 211, 238, 0.30);

    --color-channel-wa: #25d366;
    --color-channel-wa-bg: rgba(37, 211, 102, 0.12);
    --color-channel-wa-border: rgba(37, 211, 102, 0.30);

    /* ==========================================================================
       FAMILIAS & TAMAÑOS TIPOGRÁFICOS
       ========================================================================== */
    --font-serif: 'Playfair Display', 'Cinzel', 'Georgia', 'Cambria', 'Times New Roman', serif;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    --font-mono: 'JetBrains Mono', 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', monospace;

    --font-size-hero: 1.625rem;       /* 26px */
    --font-size-title: 1.25rem;       /* 20px */
    --font-size-subheading: 0.9375rem;/* 15px */
    --font-size-body: 0.875rem;       /* 14px */
    --font-size-caption: 0.75rem;     /* 12px */
    --font-size-micro: 0.6875rem;     /* 11px */

    --line-height-tight: 1.25;
    --line-height-normal: 1.50;
    --line-height-relaxed: 1.65;

    /* ==========================================================================
       ESCALA DE ESPACIADO (Ritmo 4px / 8px)
       ========================================================================== */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;
    --space-10: 40px;
    --space-12: 48px;

    /* ==========================================================================
       ESCALA DE RADIOS DE CURVATURA (Geometría Contenida)
       ========================================================================== */
    --radius-xs: 3px;
    --radius-sm: 4px;
    --radius-md: 6px;
    --radius-lg: 8px;
    --radius-xl: 12px;
    --radius-full: 9999px;

    /* ==========================================================================
       ELEVACIÓN, SOMBRAS & MODALES
       ========================================================================== */
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.35);
    --shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.45), 0 2px 6px -1px rgba(0, 0, 0, 0.30);
    --shadow-lg: 0 10px 24px -4px rgba(0, 0, 0, 0.60);
    --shadow-drawer: -12px 0 36px -4px rgba(0, 0, 0, 0.75);
    --shadow-modal: 0 24px 48px -6px rgba(0, 0, 0, 0.85), 0 12px 24px -4px rgba(0, 0, 0, 0.60);

    --backdrop-modal: rgba(11, 17, 32, 0.82);
    --backdrop-blur: blur(8px);

    /* ==========================================================================
       PUNTOS DE QUIEBRE RESPONSIVOS (Breakpoints)
       ========================================================================== */
    --bp-xs: 640px;
    --bp-sm: 768px;
    --bp-md: 1024px;
    --bp-lg: 1280px;
    --bp-xl: 1440px;
}
```

---

### 2.8 Matriz de Migración de Variables (Código Anterior -> Nuevos Tokens)

| Variable Anterior | Valor Anterior | Nuevo Token Canónico | Nuevo Valor | Justificación Arquitectónica |
|---|---|---|---|---|
| `--bg` | `#0a0a0c` | `--color-bg-canvas` | `#0b1120` | Transición del negro absoluto a un azul pizarra profundo y elegante |
| `--surface` | `#121216` | `--color-bg-surface` | `#111827` | Superficie sólida con alta densidad cromática y contraste controlado |
| `--surface-card` | `#15151b` | `--color-bg-surface-card` | `#0f172a` | Delimitación nítida para tarjetas de resumen y pozos interiores |
| `--surface-hover` | `#18181f` | `--color-bg-surface-hover`| `#1f293d` | Transición de hover fluida sin saltos de luminancia |
| `--border` | `#222228` | `--border-default` | `rgba(255, 255, 255, 0.12)` | Separadores sutiles que no sobrecargan la vista en grillas densas |
| `--accent-laboral` | `#facc15` (amarillo flúor)| `--color-accent-gold` | `#c5a059` | Reemplazo del amarillo estridente por dorado legal corporativo |
| `--primary` | `#ef4444` (rojo peligro) | `--color-accent-gold` | `#c5a059` | Establece el dorado como llamada a la acción; el rojo queda reservado para fallas |
| `--accent-sucesiones` | `#e2b16a` | `--color-accent-champagne`| `#e2b16a` | Estandarizado como dorado champán para sucesiones y herencias |
| *(Inexistente)* | *(Hardcodeado)* | `--color-status-pending` | `#94a3b8` | Token formal para la bandeja de causas pendientes de generar |
| *(Inexistente)* | *(Hardcodeado)* | `--color-status-draft` | `#38bdf8` | Token formal para borradores generados sin fecha de emisión |
| *(Inexistente)* | *(Hardcodeado)* | `--color-status-scheduled`| `#fbbf24` | Token formal para causas con fecha y hora agendadas |
| *(Inexistente)* | *(Hardcodeado)* | `--color-status-published`| `#34d399` | Token formal para posts emitidos exitosamente en redes |
| *(Inexistente)* | *(Hardcodeado)* | `--color-channel-fb` | `#1877f2` | Token de primer orden para Facebook Pages (`R3`) |
| `font-family` | Sistema básico sans | `--font-serif` / `--font-sans` | Playfair / Georgia + Inter | Autoridad editorial en cabeceras y legibilidad técnica en datos |

---

## 3. Tipografía & Escala Editorial

### 3.1 Familias Tipográficas
1. **Titulares, Cabeceras de Autoridad e Identidad de Despacho (`--font-serif`)**:
   - `font-family: 'Playfair Display', 'Cinzel', 'Georgia', 'Cambria', serif;`
   - Aplica a: Logotipo principal, encabezado de la grilla de control, títulos de causas en el drawer de detalle, coronas de modales.
2. **Interfaz de Usuario, Celdas de Grilla y Formularios (`--font-sans`)**:
   - `font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;`
   - Aplica a: Encabezados de columna (`TH`), títulos de causas en tabla, badges, botones, copys generados, textos de formulario.
3. **Importes Monetarios, Números de Expediente y Cédulas (`--font-mono`)**:
   - `font-family: 'JetBrains Mono', 'SFMono-Regular', Menlo, Monaco, Consolas, monospace;`
   - Aplica a: Montos de condena (`$ 34.800.000`), números de causa judicial (`EXPTE N° 45.920/2024`), tokens y datos estructurados.

### 3.2 Estrategia de Carga y Resiliencia Sin Conexión (Zero-Layout-Shift)
En dependencias judiciales o tribunales con conectividad restringida, el sistema nunca debe colapsar ni producir saltos de diseño (*Flash of Unstyled Text* o *FOUT*):

```html
<!-- Preconexión a CDN de alta disponibilidad -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Google Fonts: Inter (400, 500, 600, 700), Playfair Display (600, 700), JetBrains Mono (500) -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
```

Si la red externa se encuentra bloqueada por proxies corporativos, el stack de respaldo (`Georgia, Cambria, serif` y `-apple-system, Segoe UI, Roboto`) comparte las mismas métricas de altura de x (*x-height*) y ancho relativo, manteniendo el 100% de la integridad de la grilla sin desplazamiento estructural.

### 3.3 Escala Jerárquica & Pesos Tipográficos

| Jerarquía | Tamaño | Altura de Línea | Familia | Peso | Tracking | Uso Canónico |
|---|---|---|---|---|---|---|
| **Display / Hero** | `26px / 1.625rem` | `1.25` | `--font-serif` | 700 | `-0.02em` | Cabecera general de Legal Bot, Título en Drawer |
| **Section Title** | `20px / 1.25rem` | `1.35` | `--font-serif` | 600 | `-0.015em`| Título de sección de control, Títulos de modal |
| **Subheading / UI Grande** | `15px / 0.9375rem`| `1.40` | `--font-sans` | 600 | `-0.01em` | Etiquetas de solapas del Drawer, KPI labels |
| **Encabezado Columna TH** | `11px / 0.6875rem`| `1.30` | `--font-sans` | 700 | `+0.06em` | `CONTENIDO`, `FUENTE`, `FECHA`, `ESTADO`, `REDES` |
| **Texto de Cuerpo / Fila** | `14px / 0.875rem` | `1.50` | `--font-sans` | 500 | `0` | Título del caso en tabla, cuerpo de copys |
| **Extracto / Subtítulo** | `12px / 0.75rem` | `1.45` | `--font-sans` | 400 | `+0.01em` | Extracto del caso, resumen fáctico, juzgado |
| **Micro-Insignia / Badge** | `11px / 0.6875rem`| `1.20` | `--font-sans` | 700 | `+0.04em` | `PENDIENTE`, `BORRADOR`, `FB`, `IG`, `TT` |
| **Importe Pecuniario** | `12px / 0.75rem` | `1.40` | `--font-mono` | 700 | `-0.01em` | `$ 18.450.000`, montos indemnizatorios |

---

## 4. Ritmo Espacial, Bordes & Elevación

### 4.1 Escala de Espaciado (Ritmo 4px / 8px)
Todo margen, padding y gap en el sistema es múltiplo estricto de 4px / 8px:
- `--space-1` (`4px`): Micro-espacios, separación entre icono y texto en badges.
- `--space-2` (`8px`): Padding horizontal de badges, separación entre botones secundarios.
- `--space-3` (`12px`): Padding vertical estándar en celdas de tabla y formularios compactos.
- `--space-4` (`16px`): Padding horizontal en celdas de tabla, separación entre columnas principales.
- `--space-5` (`20px`): Padding interno en tarjetas métricas y barras de filtro.
- `--space-6` (`24px`): Padding interior del Drawer de detalle y modales.
- `--space-8` (`32px`): Margen vertical entre secciones maestras del panel.
- `--space-10` (`40px`): Separación perimetral en monitores de alta resolución.
- `--space-12` (`48px`): Respiración final de pie de página.

### 4.2 Radios de Curvatura & Contención (Regla Anti-Pill)
En el derecho corporativo, las formas completamente circulares de tipo píldora deportiva (`border-radius: 9999px`) en tarjetas, tablas y botones estructurales resultan infantiles y restan seriedad procesal. Los radios se limitan con elegancia:
- `--radius-xs` (`3px`): Distintivos numéricos o micro-etiquetas.
- `--radius-sm` (`4px`): Badges de estado (`PENDIENTE`, `BORRADOR`), selectores de canal.
- `--radius-md` (`6px`): Botones de acción (`⚡ Generar`, `📅 Programar`, `📋 Copiar`), campos de texto.
- `--radius-lg` (`8px`): Contenedor de miniaturas, tarjetas interiores, menús contextuales.
- `--radius-xl` (`12px`): Marco perimetral de la grilla de control y paneles de modal.
- `--radius-full` (`9999px`): **Uso exclusivo** para puntos circulares indicadores de estado (status dots) o avatares de usuario.

### 4.3 Sombras & Niveles de Elevación

```css
/* Nivel 1: Sombra tenue para filas y tarjetas interiores */
--shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.35);

/* Nivel 2: Hover sobre filas de la grilla y menús desplegables */
--shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.45), 0 2px 6px -1px rgba(0, 0, 0, 0.30);

/* Nivel 3: Slide-over Detail Drawer lateral */
--shadow-drawer: -12px 0 36px -4px rgba(0, 0, 0, 0.75);

/* Nivel 4: Modales de programación y publicación */
--shadow-modal: 0 24px 48px -6px rgba(0, 0, 0, 0.85), 0 12px 24px -4px rgba(0, 0, 0, 0.60);
```

---

## 5. Componentes Principales & Arquitectura de Interacción

### 5.1 Badges & Chips Semánticos

Todos los badges heredan la clase base `.badge` con tipografía de 11px, mayúsculas, tracking de `+0.04em` y padding de `3px 8px`:

```css
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
    padding: 3px 8px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
}
```

#### A. Badges de Estado Operativo
- **`badge-status-pending`**: Fondo `rgba(148, 163, 184, 0.10)`, texto `#94a3b8`, borde `1px solid rgba(148, 163, 184, 0.25)`. Icono `⏳`.
- **`badge-status-draft`**: Fondo `rgba(56, 189, 248, 0.12)`, texto `#38bdf8`, borde `1px solid rgba(56, 189, 248, 0.30)`. Icono `📝`.
- **`badge-status-scheduled`**: Fondo `rgba(251, 191, 36, 0.12)`, texto `#fbbf24`, borde `1px solid rgba(251, 191, 36, 0.30)`. Icono `⏰`.
- **`badge-status-published`**: Fondo `rgba(52, 211, 153, 0.12)`, texto `#34d399`, borde `1px solid rgba(52, 211, 153, 0.30)`. Icono `✅`.
- **`badge-status-error`**: Fondo `rgba(248, 113, 113, 0.14)`, texto `#f87171`, borde `1px solid rgba(248, 113, 113, 0.35)`. Icono `⚠️`.

#### B. Badges de Fuero y Fuente
- **`badge-source-court`**: Fondo `#0f172a`, texto `#cbd5e1`, borde `1px solid #334155`. (Ej.: `🏛️ CNTrab Sala V`).
- **`badge-source-press`**: Fondo `#131b2e`, texto `#94a3b8`, borde `1px solid #1e293b`. (Ej.: `📰 Infobae`).
- **`badge-source-ai`**: Fondo `rgba(56, 189, 248, 0.12)`, texto `#38bdf8`, borde `1px solid rgba(56, 189, 248, 0.30)`. (Ej.: `🤖 NinoLegal`).

#### C. Badges Pecuniarios de Indemnización / Acervo (`.badge-amount`)
- Fuente monoespaciada (`--font-mono`), 12px, negrita.
- Fondo `rgba(197, 160, 89, 0.12)`, texto `#e5c07b`, borde `1px solid rgba(197, 160, 89, 0.35)`.
- Variante sucesiones: Fondo `rgba(217, 119, 6, 0.12)`, texto `#f59e0b`.

#### D. Insignias de Canales de Redes (`.channel-pill`)
- **Facebook (`channel-fb`)**: Activo con fondo `rgba(24, 119, 242, 0.15)`, texto `#60a5fa`, borde `#1877f2`. Distintivo: `👥 FB`.
- **Instagram (`channel-ig`)**: Activo con fondo `rgba(225, 48, 108, 0.15)`, texto `#f472b6`, borde `#e1306c`. Distintivo: `📸 IG`.
- **TikTok (`channel-tt`)**: Activo con fondo `rgba(34, 211, 238, 0.12)`, texto `#38bdf8`, borde `#22d3ee`. Distintivo: `🎵 TT`.
- **Publicado (`published`)**: Cuando el post ya está en vivo en ese canal, el pill toma tinte esmeralda `rgba(16, 185, 129, 0.20)` con texto `#34d399` y check verde.

---

### 5.2 Botones & Jerarquía Interactiva

```
[ Default ] ──(Hover)──► [ translateY(-1px) + Resplandor Sutil ]
    │
 (Clic)
    ▼
[ Active: Scale 0.98 ] ──(Petición Asíncrona)──► [ Spinner de Carga ] ──► [ Feedback Toast ]
```

1. **Botón Primario de Generación (`.btn-primary-generate`)**:
   - Fondo: Degradé dorado institucional `linear-gradient(135deg, #c5a059 0%, #a88438 100%)`.
   - Texto: `#0b1120` (Obsidiana marino para contraste AAA superior a 11:1).
   - Padding: `7px 14px`, radio `6px`, fuente negrita 700.
   - Hover: Brillo +12%, elevación `translateY(-1px)`, resplandor dorado `box-shadow: 0 4px 12px rgba(197, 160, 89, 0.35)`.
2. **Botón Secundario de Contorno (`.btn-secondary`)**:
   - Fondo: `#101726`, borde `1px solid #1e293b`, texto `#cbd5e1`.
   - Hover: Fondo `#18223a`, borde `#334155`, texto `#ffffff`.
   - Uso: `📅 Programar`, `✏️ Modificar`.
3. **Botón Rápido de Copiado (`.btn-copy-fast`)**:
   - Fondo: `#0f1624`, borde `1px solid #1e293b`, texto `#94a3b8`, padding `5px 9px`.
   - Estado de retroalimentación activa: Al hacer clic, el botón conmuta por **1.500 ms** a fondo esmeralda `rgba(16, 185, 129, 0.15)`, texto `#34d399`, borde `#34d399` y etiqueta `✓ ¡Copiado!`. Emite notificación toast en la esquina inferior.
4. **Botón Fantasma / Menú (`.btn-ghost`)**:
   - Fondo transparente, texto `#94a3b8`, hover con fondo `#1e293b` y texto `#f8fafc`.
   - Uso: Menú contextual de tres puntos (`···`), botón de cierre (`✕`).
5. **Botón de Peligro (`.btn-danger`)**:
   - Fondo `rgba(239, 68, 68, 0.12)`, borde `1px solid rgba(239, 68, 68, 0.25)`, texto `#f87171`.
   - Uso exclusivo: Descartar o eliminar noticias de la bandeja.

---

### 5.3 Grilla Unificada de 6 Columnas (Especificación de Columnas y Layout)

La grilla tabular central sustituye la navegación fragmentada previa (`#sectionScanner`, `#sectionGrilla`, `#sectionBandeja`) por un panel de control único y directo:

| Col # | Nombre de Columna | Ancho (% / mín) | Alineación | Contenido y Jerarquía | Propósito Operativo |
|---|---|---|---|---|---|
| **1** | **Contenido** | `36%` (mín `320px`) | Izquierda | • Ancla visual (44x44px miniatura o icono de expediente)<br>• Título del caso (2 líneas máx)<br>• Badge de vertical + Badge pecuniario<br>• Gancho empático / Extracto jurídico | Identificación inmediata del caso, disparador del Drawer |
| **2** | **Fuente** | `14%` (mín `130px`) | Izquierda | • Nombre del Tribunal / Medio (`CNTrab Sala V`, `Infobae`)<br>• Tipo de procedencia (`🏛️ Oficial`, `🤖 NinoLegal`) | Verificación de autoridad y origen de la resolución |
| **3** | **Fecha** | `10%` (mín `95px`) | Izquierda | • Tiempo relativo (`Hoy`, `Ayer`, `Hace 2d`)<br>• Fecha ISO (`YYYY-MM-DD`) en subtítulo | Evaluación de vigencia procesal |
| **4** | **Estado** | `13%` (mín `120px`) | Centro | • Badge dual con icono y color:<br>`⏳ Pendiente` \| `📝 Borrador` \| `⏰ Programado` \| `✅ Publicado` \| `⚠️ Error` | Trazabilidad del ciclo de vida del contenido |
| **5** | **Redes** | `11%` (mín `100px`) | Centro | • Grupo de insignias de canal:<br>`📸 IG` \| `🎵 TT` \| `👥 FB`<br>• Resaltadas si están asignadas/publicadas | Cobertura de difusión multicanal al instante |
| **6** | **Acciones** | `16%` (mín `160px`) | Derecha | • CTA contextual en 1 clic:<br>- Pendiente: `⚡ Generar`<br>- Generada: `📋 Copiar` + `📅 Programar`<br>• Menú contextual `···` | Ejecución operativa sin salir de la tabla |

---

### 5.4 Arquitectura Sensorial de Trazabilidad en < 3 Segundos

El diseño implementa el principio de **percepción preatencional** para asegurar el cumplimiento del criterio de aceptación: *"El usuario puede identificar en menos de 3 segundos si una noticia fue utilizada o no"*.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARQUITECTURA DE PERCEPCIÓN PREATENCIONAL (<3s)                  │
├────────────────────────────────┬───────────────────────────┬───────────────────────────┤
│ Elemento Sensorial             │ CAUSA PENDIENTE (⚪)       │ PIEZA GENERADA (📝/⏰/✅) │
├────────────────────────────────┼───────────────────────────┼───────────────────────────┤
│ 1. Borde Lateral Izquierdo     │ 3px DISCONTINUO (#475569) │ 3px SÓLIDO Dorado (#c5a059│
│ 2. Tono de Fondo de la Fila    │ Pizarra tenue (#090d16)   │ Azul Marino (#111827)     │
│ 3. Ancla Visual en Columna 1   │ Caja 44px Icono Balanza/Exp│ Miniatura 44px de Portada │
│ 4. Insignia en Columna 4       │ ⏳ PENDIENTE (Gris Muted)  │ Color vivo: 📝 / ⏰ / ✅   │
│ 5. Botón de Acción Principal   │ ⚡ Generar (Dorado Saliency│ 📋 Copiar / 📅 Programar  │
└────────────────────────────────┴───────────────────────────┴───────────────────────────┘
```

#### Reglas de Estilo CSS para Filas:
```css
/* Fila Pendiente */
.control-table tbody tr.row-pending {
    background-color: rgba(9, 13, 22, 0.70);
    border-left: 3px dashed #475569;
}
.control-table tbody tr.row-pending:hover {
    background-color: #101626;
    border-left-color: #94a3b8;
}

/* Fila Generada (Post Activo) */
.control-table tbody tr.row-generated {
    background-color: #111827;
    border-left: 3px solid #c5a059;
}
.control-table tbody tr.row-generated.vertical-sucesiones {
    border-left-color: #e2b16a;
}
.control-table tbody tr.row-generated:hover {
    background-color: #18223a;
}
```

---

### 5.5 Barra de Herramientas KPI / Filtros Rápidos Inmediatos

Directamente sobre la grilla, una barra superior fija despliega contadores instantáneos con filtrado de latencia cero (`0 ms`):
```
[ Todos (45) ]  [ ⏳ 14 Pendientes ]  [ 📝 6 Borradores ]  [ ⏰ 8 Programados ]  [ ✅ 17 Publicados ]
```
Al hacer clic sobre cualquiera de los pills de KPI, la tabla aplica un filtro instantáneo en cliente sin recargar la página.

---

### 5.6 Slide-over Detail Drawer (Panel Lateral de Inspección)

Al pulsar sobre cualquier celda de contenido o miniatura de la fila, se despliega desde el lateral derecho un cajón de detalle profundo:

- **Dimensionamiento**:
  - Escritorio (`>= 1024px`): Ancho fijo `520px` (máximo `90vw`).
  - Tablet (`768px – 1023px`): Ancho `480px`.
  - Móvil (`< 768px`): Ancho completo `100vw` con botón de retroceso fijo.
- **Cinemática**:
  - Apertura con `transform: translateX(0);` y curva de aceleración `transition: transform 300ms cubic-bezier(0.16, 1, 0.3, 1);`.
  - Telón de fondo (*Backdrop*): `rgba(11, 17, 32, 0.75)` con filtro de desenfoque `backdrop-filter: blur(4px)`.
  - Cierre inmediato con tecla `Escape` o clic sobre el backdrop.

#### Estructura de Zonas del Drawer:
1. **Zona 1: Cabecera**:
   - Insignia de Vertical (`⚖️ Laboral` / `📜 Sucesiones`), Insignia de Estado y Monto pecuniario en monoespacio.
   - Título formal de la causa en fuente serif editorial (`Playfair Display`, 18px bold).
   - Tribunal de origen, fecha de publicación y botón de cierre `✕`.
2. **Zona 2: Navegación por Solapas**:
   - `🖼️ Formatos`: Selector de relación de aspecto.
   - `📱 Copys Redes`: Copys listos para publicación.
   - `🎬 Guion 35s`: Guion estructurado para teleprónter.
   - `💬 WhatsApp`: Enlace de conversión y mensaje preconfigurado.
3. **Zona 3: Paneles de Contenido de Solapa**:
   - **Solapa Formatos**: Conmutador segmentado para `📸 Instagram (4:5)`, `🎵 TikTok (9:16)` y `👥 Facebook (1:1)`. Visualizador centrado en caja de alta resolución con botones `🔍 Ver en HD` y `💾 Descargar PNG`.
   - **Solapa Copys Redes**: Cuadros de texto independientes para Instagram (con contador de caracteres y botón `📋 Copiar IG`) y TikTok (con botón `📋 Copiar TT`). Feedback visual inmediato al copiar.
   - **Solapa Guion 35s**: Estructura dividida en 3 bloques temporales de teleprónter:
     - `⚡ Hook Inicial (0–3 seg)`: Línea hablada + indicación de rótulo en pantalla (borde rojo).
     - `📖 Desarrollo del Caso (3–28 seg)`: Explicación de los hechos y la ley aplicable (borde azul cielo).
     - `🎯 Llamada a la Acción (29–35 seg)`: Conducción a WhatsApp (borde verde).
     - Botón `📋 Copiar Guion Completo` listo para aplicaciones de teleprónter.
   - **Solapa WhatsApp**: Caja con enlace `https://wa.me/...`, burbuja simulada de chat con el mensaje de consulta y botón de prueba directa.
4. **Zona 4: Acciones Fijas Inferiores**:
   - `⚡ Regenerar Variante`, `📅 Programar Fecha`, `🚀 Publicar Ahora`.
5. **Modo Especial para Causas Pendientes**:
   - Si la causa seleccionada aún está en estado `⚪ Pendiente`, el Drawer presenta la vista previa del expediente judicial analizado por IA y ofrece el CTA principal: `⚡ Generar Piezas Multi-Asset Ahora (1 Clic)`.

---

### 5.7 Modales de Programación & Publicación Rápida

- **Telón de Fondo (`--backdrop-modal`)**: `rgba(11, 17, 32, 0.82)` con desenfoque de cristal `backdrop-filter: blur(8px)`.
- **Contenedor**: Superficie `#111827`, borde `1px solid rgba(255, 255, 255, 0.12)`, radio `12px`, sombra de alta elevación `--shadow-modal`.
- **Selector de Canales (Facebook como Ciudadano de Primer Orden)**:
  - Tarjetas conmutables para `📸 Instagram`, `🎵 TikTok` y `👥 Facebook Pages`.
  - La tarjeta de Facebook activa su resplandor y contorno en `#1877f2` con la casilla activada por defecto.
- **Selector de Fecha y Hora Dark (`color-scheme: dark`)**:
  - Campo `<input type="datetime-local">` normalizado con fondo `#0b1120`, texto claro e icono de calendario filtrado en tono dorado.
- **Modal de Resultados & Flujo de Contingencia Guiado (Semi-Automático)**:
  - En caso de éxito de publicación por Graph API, presenta el `fb_post_id` y el enlace al post en vivo.
  - En caso de no contar aún con token configurado o token expirado (Error 190), el modal despliega la **Guía Semi-Automática en 5 Pasos**:
    1. Descargar la carátula 1:1 generada mediante el botón directo `💾 Descargar Foto`.
    2. Abrir la Página de Facebook del estudio jurídico.
    3. Crear una nueva publicación y adjuntar la imagen cuadrada.
    4. Copiar el texto de Facebook generado mediante `📋 Copiar Descripción`.
    5. Pegar el texto y pulsar Publicar.

---

### 5.8 Contrato de Datos del Feed Unificado (`UnifiedFeedItem`)

Cada fila de la grilla y el drawer se alimenta del siguiente contrato de interfaz:

```typescript
interface UnifiedFeedItem {
    id: string;                      // Identificador único (MD5 de noticia o UUID de post)
    is_generated: boolean;           // True si ya posee post en 'publicaciones'
    noticia_id?: string;             // Referencia a 'noticias.id'
    post_id?: string;                // Referencia a 'publicaciones.id'
    titulo: string;                  // Título principal de la causa
    extracto?: string;               // Resumen o gancho fáctico
    vertical: "laboral" | "sucesiones";
    monto?: string;                  // Ej: "$ 34.800.000"
    fuente: string;                  // Ej: "CNTrab Sala V", "Infobae"
    fuente_tipo: "tribunal" | "rss" | "ninolegal";
    fecha: string;                   // Formato ISO YYYY-MM-DD
    fecha_relativa: string;          // Ej: "Hoy", "Hace 2d"
    pub_status: "pending" | "draft" | "scheduled" | "published" | "error";
    scheduled_at?: string;           // Timestamp de emisión programada
    redes_target: Array<"instagram" | "tiktok" | "facebook">;
    redes_publicadas?: Array<"instagram" | "tiktok" | "facebook">;
    caratula_url?: string;           // URL a imagen 1:1 o 4:5
    copy_ig?: string;                // Texto optimizado para Instagram
    copy_tiktok?: string;            // Texto optimizado para TikTok
    guion_video?: string;            // Estructura de guion 35s
    wa_link?: string;                // Enlace directo al embudo de WhatsApp
}
```

---

## 6. Pautas Responsivas & Adaptabilidad por Dispositivos

### 6.1 Escala de Breakpoints

| Token | Rango de Viewport | Dispositivos Clave | Adaptación Principal |
|---|---|---|---|
| `--bp-xs` | `< 640px` | Teléfonos móviles | Drawer al 100vw, tabla colapsa a tarjetas compactas, botones de ancho completo |
| `--bp-sm` | `640px – 767px` | Teléfonos grandes / tablets mini | Scroll horizontal con Columna 1 fija (*sticky*), filtros en 2 filas |
| `--bp-md` | `768px – 1023px`| iPads en vertical, laptops compactas | Grilla de 6 columnas visible completa con padding ajustado (10px) |
| `--bp-lg` | `1024px – 1279px`| Pantallas de escritorio estándar | Vista completa con Drawer lateral de 520px conviviendo en paralelo |
| `--bp-xl` | `>= 1280px` | Estaciones de trabajo y monitores amplios | Contenedor centrado hasta 1440px con máxima legibilidad |

### 6.2 Comportamiento Responsivo en Dispositivos Móviles
- En pantallas inferiores a 768px, el Drawer lateral ocupa el 100% del ancho del viewport (`width: 100vw;`) transformándose en una vista de pantalla completa con barra superior fija de cierre.
- Los modales reducen su padding a 16px y sus selectores de redes se apilan verticalmente garantizando áreas de toque mínimas de `44x44px` conforme a las pautas de accesibilidad móvil.

---

## 7. Reglas de Implementación & Checklist de Aceptación

### 7.1 Reglas Obligatorias (Do's & Don'ts)

| Categoría | DO (Obligatorio) | DON'T (Estrictamente Prohibido) |
|---|---|---|
| **Colores** | Utilizar siempre las variables `--color-bg-canvas` (`#0b1120`) y `--color-bg-surface` (`#111827`). | Prohibido utilizar negro puro `#000000` o fondo `#0a0a0c` sin matiz marino. |
| **Acentos** | Emplear dorado corporativo `--color-accent-gold` (`#c5a059`) para acciones primarias. | Prohibido utilizar amarillo flúor (`#facc15`) o rojo como color temático de la app. |
| **Tipografía**| Utilizar `--font-serif` para encabezados solemnes e `--font-sans` para la grilla y controles. | Prohibido usar fuentes de fantasía, cómic o serifs genéricas sin métricas de fallback. |
| **Trazabilidad**| Codificar el estado en 5 capas (borde izquierdo, fondo, icono/thumbnail, badge y botón). | Prohibido confiar el estado únicamente al color del texto sin icono ni etiqueta. |
| **Geometría** | Respetar radios contenidos entre `4px` y `8px` para tarjetas, tablas y botones. | Prohibido usar botones o tarjetas con esquinas tipo píldora (`border-radius: 9999px`). |
| **Facebook** | Asignar a Facebook el mismo tratamiento gráfico, insignias y casillas por defecto que a IG y TT. | Prohibido excluir a Facebook de los selectores o tratarlo como un canal secundario de texto plano. |
| **Drawer** | Implementar apertura lateral fluida con backdrop blur sin provocar recarga de página ni saltos. | Prohibido redirigir a una página nueva o abrir popups intrusivos sin contexto. |

### 7.2 Convención de Nombres de Variables CSS
Todas las variables CSS añadidas a la solución deben cumplir la siguiente taxonomía:
- Colores de fondo y superficie: `--color-bg-*`
- Colores de texto y contenido: `--color-text-*`
- Acentos corporativos: `--color-accent-*`
- Estados operativos: `--color-status-*`
- Canales de redes sociales: `--color-channel-*`
- Familias y escalas tipográficas: `--font-*` y `--font-size-*`
- Escala de espaciado: `--space-*`
- Radios de curvatura: `--radius-*`
- Sombras y elevación: `--shadow-*`

---

### 7.3 Catálogo de Casos Borde y Manejo de Errores

1. **Apertura de Drawer en Causa Pendiente**: Si el usuario pulsa sobre una noticia aún no generada, el Drawer abre en **Modo Admisión Jurídica** con el análisis fáctico, importe estimado y el botón de acción prominente `⚡ Generar Piezas Multi-Asset Ahora (1 Clic)`, evitando pantallas en blanco o tabs vacíos.
2. **Formato de Portada Parcialmente Generado**: Si una causa cuenta con carátula 1:1 pero no 4:5 ni 9:16, el visor visualiza la carátula existente con un distintivo explicativo y el botón `⚡ Generar variante en esta proporción`.
3. **Títulos Judiciales Excesivamente Largos**: Títulos de más de 120 caracteres en la cabecera del Drawer implementan `overflow-wrap: break-word;` y salto de línea elegante manteniendo el botón de cierre fijado arriba a la derecha.
4. **Validación de Selección de Redes en Modal**: Si el usuario desmarca todas las redes en el modal de programación e intenta guardar, el sistema resalta el bloque en rojo suave (`#f87171`), vibra sutilmente y emite la advertencia: *"Seleccioná al menos una red social de destino"*.
5. **Fecha en el Pasado**: El formulario de programación rechaza fechas anteriores al momento actual y advierte: *"La fecha de publicación debe ser a futuro"*.
6. **Falla de Conexión a Fuentes Web**: Si el navegador no puede conectar a Google Fonts, el stack tipográfico de respaldo en `system-ui` y `Georgia` toma el control de inmediato con 0% de desplazamiento de layout.

---

### 7.4 Checklist Exhaustivo de Validación de Criterios de Aceptación (R1 a R4)

Este checklist gobierna la aceptación de las entregas de los Hitos M3 (Frontend Overhaul) y M4 (Verificación E2E):

#### Requisito R1: Vista Unificada Simplificada (Grilla Tabular por Columnas)
- [ ] **AC-R1.1**: La pantalla principal renderiza inmediatamente una tabla de 6 columnas claramente identificadas: `Contenido`, `Fuente`, `Fecha`, `Estado`, `Redes` y `Acciones`.
- [ ] **AC-R1.2**: El usuario puede distinguir si una noticia fue utilizada o no en menos de **3 segundos** mediante la arquitectura preatencional de 5 capas (borde discontinuo gris vs continuo dorado, placeholder vs thumbnail, badge `⏳ Pendiente` vs badges cromáticos).
- [ ] **AC-R1.3**: La acción directa en 1 clic (`⚡ Generar`, `📅 Programar`, `📋 Copiar`) opera de forma contextual desde la fila correspondiente sin pasos confusos.
- [ ] **AC-R1.4**: Se eliminan las cuatro secciones fragmentadas anteriores (`#sectionScanner`, `#sectionGrilla`, `#sectionBandeja`) consolidando el flujo en una única grilla de control central.

#### Requisito R2: Sistema de Diseño Premium (`DESIGN.md`)
- [ ] **AC-R2.1**: Existe el archivo `DESIGN.md` en la raíz del proyecto definiendo la arquitectura completa de tokens, colores, tipografía, componentes y gobernanza.
- [ ] **AC-R2.2**: Los estilos en `web/index.html` implementan las propiedades personalizadas CSS (:root) con estricta adherencia a la taxonomía `--color-*`, `--font-*`, `--space-*`, `--radius-*` y `--shadow-*`.
- [ ] **AC-R2.3**: Se erradica por completo el amarillo flúor estridente (`#facc15`) y el rojo de emergencia como colores de acento primario, consolidando la paleta en azul pizarra (`#0b1120`, `#111827`) y dorado corporativo (`#c5a059`).
- [ ] **AC-R2.4**: Se implementa tipografía editorial con serifa en encabezados solemnes y sin serifa de alta legibilidad en la tabla y controles.
- [ ] **AC-R2.5**: Los ratios de contraste satisfacen las directrices WCAG 2.1 nivel AA y AAA en todos los textos interactivos y badges.

#### Requisito R3: Soporte Completo de Publicación en Facebook
- [ ] **AC-R3.1**: Facebook Pages está integrado permanentemente con su distintivo `👥 FB` en la columna de redes, en el drawer y en los modales de publicación.
- [ ] **AC-R3.2**: La casilla de Facebook está seleccionada por defecto junto a Instagram y TikTok en los modales de publicación rápida y programación.
- [ ] **AC-R3.3**: El motor de publicación y la interfaz contemplan la subida de fotos cuadradas 1:1 vía Graph API y el despliegue de la guía semi-automática de 5 pasos cuando no hay token disponible.
- [ ] **AC-R3.4**: Los archivos `.env` y `.env.example` documentan exhaustivamente las variables `FACEBOOK_PAGE_ACCESS_TOKEN` y `FACEBOOK_PAGE_ID`.

#### Requisito R4: Flujo de Ingesta y Generación Sin Fricción
- [ ] **AC-R4.1**: Las causas escaneadas se exhiben de inmediato en la grilla con su insignia inequívoca `⚪ Pendiente` y datos de tribunal y monto.
- [ ] **AC-R4.2**: La pulsación de `⚡ Generar` desde la fila procesa la causa con IA, redacta los copys, produce las imágenes y transmuta el estado a `📝 Borrador` o `⏰ Programado`.
- [ ] **AC-R4.3**: Al hacer clic en cualquier fila de la grilla se abre el *Slide-over Detail Drawer* con visor de formatos (4:5, 9:16, 1:1), copys con copiado rápido, guion de 35s y embudo a WhatsApp.
