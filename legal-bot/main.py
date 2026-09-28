import os
import sys

# Garantizar compatibilidad con consola de Windows (evita UnicodeEncodeError)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from scraper import fetch_noticias, get_noticias_pendientes, marcar_procesada
from ai_engine import filtrar_noticia_legal, redactar_post_legal
from designer import generar_caratula, generar_dashboard

def main():
    print("=" * 70)
    print(" ⚖️   LEGAL BOT — SENTENCIAS, DEMANDAS Y CONDENAS LABORALES")
    print("=" * 70)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("\n⚠️  ATENCIÓN: No configuraste tu GEMINI_API_KEY en .env")
        return

    print("\n📡 1. Buscando noticias en fuentes judiciales...")
    nuevas = fetch_noticias()
    print(f"   → {nuevas} noticias ingresadas a la base de datos.")

    pendientes = get_noticias_pendientes(limite=30)
    if not pendientes:
        print("\n✅ No hay noticias pendientes en la base de datos.")
        return

    print(f"   → Analizando {len(pendientes)} noticias (filtrando casos judiciales concretos)...")

    candidatas_legales = []

    for noticia in pendientes:
        res = filtrar_noticia_legal(noticia)
        es_legal = res.get("es_legal_laboral", False)
        puntaje = res.get("puntaje", 0)

        # Filtro estricto: Solo juicios, sentencias o demandas reales
        if es_legal and puntaje >= 6:
            candidatas_legales.append({
                "noticia": noticia,
                "filtro": res
            })
        else:
            # Descartar y marcar como procesada
            marcar_procesada(noticia["id"])

    if not candidatas_legales:
        print("\nℹ️  No se encontraron sentencias o demandas laborales nuevas en este lote.")
        print("   (Se descartaron temas de macroeconomía, inflación y noticias no judiciales).")
        return

    # Menú interactivo con montos y situación del trabajador
    print("\n" + "=" * 70)
    print(" 📋  CASOS JUDICIALES Y SENTENCIAS ENCONTRADAS:")
    print("=" * 70)

    for i, item in enumerate(candidatas_legales, 1):
        noticia = item["noticia"]
        filtro = item["filtro"]
        tipo = filtro.get("tipo", "Sentencia")
        pts = filtro.get("puntaje", 0)
        monto = filtro.get("monto", "")
        situacion = filtro.get("situacion_trabajador", "")

        monto_str = f" • 💰 {monto}" if monto else ""

        print(f"\n [{i}] [{tipo.upper()}{monto_str} • {pts}/10]")
        print(f"     📰 {noticia['titulo']}")
        if situacion:
            print(f"     👤 Situación: {situacion}")
        print(f"     💡 Fallo: {filtro.get('resumen_caso', '')}")
        print(f"     🏛️  Fuente: {noticia.get('fuente', 'Medio')} | Link: {noticia.get('link', '')}")

    print("\n" + "=" * 70)
    print("👉 ¿Cuál querés publicar?")
    print("   - Escribí el número (ej: 1)")
    print("   - O varios separados por coma (ej: 1, 2)")
    print("   - O escribí 'todas'")
    print("   - O '0' para cancelar")
    print("=" * 70)

    try:
        eleccion = input("\nTu elección: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        eleccion = "0"

    if eleccion in ["0", "ninguna", "cancelar", "salir", ""]:
        print("Operación cancelada. No se generaron publicaciones.")
        return

    seleccionadas = []
    if eleccion in ["todas", "all", "*"]:
        seleccionadas = candidatas_legales
    else:
        partes = [p.strip() for p in eleccion.split(",") if p.strip().isdigit()]
        for p in partes:
            idx = int(p) - 1
            if 0 <= idx < len(candidatas_legales):
                seleccionadas.append(candidatas_legales[idx])

    if not seleccionadas:
        print("Opción inválida. No se seleccionó ninguna noticia.")
        return

    print(f"\n✍️  Generando contenido y carátulas minimalistas para {len(seleccionadas)} caso(s)...")

    publicaciones = []

    for item in seleccionadas:
        noticia = item["noticia"]
        filtro = item["filtro"]

        print(f"\n🎨 Procesando: {noticia['titulo'][:60]}...")
        contenido = redactar_post_legal(noticia, filtro)

        if not contenido:
            print("   ⚠️  No se pudo redactar el contenido.")
            continue

        # Generar carátula minimalista con monto
        img_path = generar_caratula(contenido, noticia["id"])
        print(f"   🖼️  Carátula guardada: {img_path}")
        if contenido.get("monto"):
            print(f"   💰 Monto condena: {contenido.get('monto')}")
        print(f"   🎯 Título: {contenido.get('titulo_caratula', '')}")
        print(f"   📢 Gancho: {contenido.get('gancho', '')}")

        publicaciones.append({
            "noticia": noticia,
            "analisis": contenido,
            "imagen_path": img_path
        })

        marcar_procesada(noticia["id"])

    if publicaciones:
        html_path = generar_dashboard(publicaciones)
        abs_html = os.path.abspath(html_path)
        print("\n" + "=" * 70)
        print("🎉 ¡LISTO! Publicaciones generadas exitosamente:")
        print(f"🌐 Visor interactivo generado:")
        print(f"   file:///{abs_html.replace(os.sep, '/')}")
        print("=" * 70)

if __name__ == "__main__":
    main()
