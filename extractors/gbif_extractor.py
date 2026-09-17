"""
gbif_extractor.py
=================
Extrae ocurrencias de especies de flora y fauna desde la API de GBIF.
Fuente: https://www.gbif.org/developer/occurrence

GBIF (Global Biodiversity Information Facility) es la mayor infraestructura
de datos de biodiversidad del mundo, con más de 2.600 millones de registros.
No requiere API key para consultas de lectura.
"""

import time
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (GBIF_BASE_URL, GBIF_LIMIT, GBIF_RADIUS_DEG, GBIF_CLASSES,
                    LOCATIONS, REQUEST_TIMEOUT, REQUEST_RETRIES, REQUEST_BACKOFF)
from logger import get_logger

log = get_logger("extractor.gbif")


def extract_biodiversity() -> List[Dict[str, Any]]:
    """
    Para cada ubicación y clase taxonómica configurada, recupera ocurrencias
    de especies observadas en los últimos 12 meses.

    Retorna:
        Lista de registros de ocurrencias con taxonomía y coordenadas.
    """
    now_utc      = datetime.now(timezone.utc)
    extracted_at = now_utc.isoformat()
    year_ago     = (now_utc - timedelta(days=365)).strftime("%Y-%m-%d")
    today        = now_utc.strftime("%Y-%m-%d")

    all_records: List[Dict[str, Any]] = []

    for loc in LOCATIONS:
        for taxon_class in GBIF_CLASSES:
            log.info("GBIF → %s / clase: %s", loc["name"], taxon_class)

            params = {
                "decimalLatitude":  f"{loc['lat'] - GBIF_RADIUS_DEG},{loc['lat'] + GBIF_RADIUS_DEG}",
                "decimalLongitude": f"{loc['lon'] - GBIF_RADIUS_DEG},{loc['lon'] + GBIF_RADIUS_DEG}",
                "class":            taxon_class,
                "year":             f"{year_ago[:4]},{today[:4]}",
                "hasCoordinate":    "true",
                "occurrenceStatus": "PRESENT",
                "limit":            GBIF_LIMIT,
                "offset":           0,
            }

            for attempt in range(1, REQUEST_RETRIES + 1):
                try:
                    resp = requests.get(GBIF_BASE_URL, params=params,
                                        timeout=REQUEST_TIMEOUT)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except requests.RequestException as e:
                    log.warning("Intento %d/%d GBIF %s/%s: %s",
                                attempt, REQUEST_RETRIES, loc["name"], taxon_class, e)
                    if attempt < REQUEST_RETRIES:
                        time.sleep(REQUEST_BACKOFF ** attempt)
                    else:
                        data = None

            if not data:
                continue

            results = data.get("results", [])
            log.debug("  → %d ocurrencias encontradas (total: %d)",
                      len(results), data.get("count", 0))

            for occ in results:
                lat = occ.get("decimalLatitude")
                lon = occ.get("decimalLongitude")
                if lat is None or lon is None:
                    continue

                record = {
                    "gbif_key":       occ.get("key"),
                    "species":        occ.get("species") or occ.get("scientificName"),
                    "kingdom":        occ.get("kingdom"),
                    "phylum":         occ.get("phylum"),
                    "class":          occ.get("class"),
                    "order_name":     occ.get("order"),
                    "family":         occ.get("family"),
                    "lat":            lat,
                    "lon":            lon,
                    "country":        occ.get("countryCode"),
                    "event_date":     occ.get("eventDate", "")[:10] if occ.get("eventDate") else None,
                    "basis_of_record": occ.get("basisOfRecord"),
                    "location_ref":   loc["name"],
                    "extracted_at":   extracted_at,
                }
                all_records.append(record)

            # Pausa para respetar límite de tasa de GBIF
            time.sleep(0.5)

    log.info("GBIF → %d registros extraídos en total", len(all_records))
    return all_records
