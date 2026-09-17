"""
main.py
=======
Punto de entrada principal del pipeline ETL de Monitorización Ambiental.

Orquesta la ejecución secuencial de las 4 ETLs:
  1. OpenAQ        → Calidad del Aire
  2. Open-Meteo    → Variables Climáticas
  3. GBIF          → Biodiversidad (flora y fauna)
  4. NASA FIRMS    → Incendios Activos

Uso:
    python main.py                  # Ejecuta todas las ETLs
    python main.py --etl openaq     # Ejecuta solo una ETL específica

ETLs disponibles: openaq, openmeteo, gbif, nasafirms
"""

import argparse
import sys
import os
from datetime import datetime, timezone

# Agregar el directorio del pipeline al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from logger import get_logger

from extractors.openaq_extractor    import extract_air_quality
from extractors.openmeteo_extractor import extract_weather
from extractors.gbif_extractor      import extract_biodiversity
from extractors.nasafirms_extractor import extract_fires

from loaders.sqlite_loader import (
    load_air_quality, load_weather, load_biodiversity, load_fires
)

log = get_logger("main")

# Mapa de ETLs disponibles: nombre → (función extractor, función loader)
ETL_MAP = {
    "openaq":    (extract_air_quality,  load_air_quality),
    "openmeteo": (extract_weather,      load_weather),
    "gbif":      (extract_biodiversity, load_biodiversity),
    "nasafirms": (extract_fires,        load_fires),
}


def run_pipeline(etls: list = None):
    """
    Ejecuta el pipeline completo o un subconjunto de ETLs.

    Args:
        etls: Lista de nombres de ETLs a ejecutar. None = todas.
    """
    start = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("INICIO DEL PIPELINE — %s UTC", start.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    # Asegurar que el esquema de DB existe
    init_db()

    etls_to_run = etls or list(ETL_MAP.keys())
    summary     = {}

    for etl_name in etls_to_run:
        if etl_name not in ETL_MAP:
            log.error("ETL desconocida: '%s'. Opciones: %s", etl_name, list(ETL_MAP))
            continue

        extractor_fn, loader_fn = ETL_MAP[etl_name]
        log.info("─── Iniciando ETL: %s", etl_name.upper())

        try:
            records  = extractor_fn()
            inserted = loader_fn(records)
            summary[etl_name] = {"status": "OK", "extraídos": len(records), "insertados": inserted}
        except Exception as e:
            log.error("ETL %s FALLÓ: %s", etl_name, e)
            summary[etl_name] = {"status": "ERROR", "error": str(e)}

    # ── Resumen final ─────────────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log.info("=" * 60)
    log.info("PIPELINE COMPLETADO en %.1f segundos", elapsed)
    log.info("Resumen:")
    for etl, result in summary.items():
        if result["status"] == "OK":
            log.info("  ✓ %-12s → %d extraídos, %d insertados",
                     etl, result["extraídos"], result["insertados"])
        else:
            log.error("  ✗ %-12s → ERROR: %s", etl, result.get("error"))
    log.info("=" * 60)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline ETL — Monitorización Ambiental y Biodiversidad"
    )
    parser.add_argument(
        "--etl",
        choices=list(ETL_MAP.keys()),
        nargs="+",
        help="ETL(s) a ejecutar (por defecto: todas)",
    )
    args = parser.parse_args()
    run_pipeline(etls=args.etl)
