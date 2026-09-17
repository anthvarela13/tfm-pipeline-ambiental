"""
nasafirms_extractor.py
======================
Extrae datos de incendios activos desde NASA FIRMS (Fire Information for
Resource Management System).
Fuente: https://firms.modaps.eosdis.nasa.gov

Los datos MODIS C6.1 son archivos CSV públicos que NASA actualiza cada pocas
horas con detecciones satelitales de los últimos 7 días. No requieren API key.
"""

import io
import time
import requests
import csv
from datetime import datetime, timezone
from typing import List, Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FIRMS_URL, REQUEST_TIMEOUT, REQUEST_RETRIES, REQUEST_BACKOFF
from logger import get_logger

log = get_logger("extractor.nasafirms")

# Columnas esperadas en el CSV de FIRMS MODIS
EXPECTED_COLS = {
    "latitude", "longitude", "brightness", "scan", "track",
    "acq_date", "acq_time", "confidence", "daynight"
}


def extract_fires() -> List[Dict[str, Any]]:
    """
    Descarga y parsea el CSV global de incendios activos de NASA FIRMS
    (últimos 7 días, sensor MODIS C6.1).

    Retorna:
        Lista de registros de incendios con coordenadas, brillo y confianza.
    """
    now_utc      = datetime.now(timezone.utc)
    extracted_at = now_utc.isoformat()

    log.info("NASA FIRMS → descargando CSV global de incendios activos")

    raw_content = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.get(FIRMS_URL, timeout=REQUEST_TIMEOUT,
                                stream=True)
            resp.raise_for_status()
            raw_content = resp.content.decode("utf-8")
            break
        except requests.RequestException as e:
            log.warning("Intento %d/%d FIRMS: %s", attempt, REQUEST_RETRIES, e)
            if attempt < REQUEST_RETRIES:
                time.sleep(REQUEST_BACKOFF ** attempt)

    if raw_content is None:
        log.error("No se pudo descargar datos de NASA FIRMS")
        return []

    records: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(raw_content))

    # Verificar que el CSV tiene las columnas esperadas
    if reader.fieldnames:
        missing = EXPECTED_COLS - set(reader.fieldnames)
        if missing:
            log.warning("Columnas faltantes en CSV FIRMS: %s", missing)

    for row in reader:
        try:
            lat  = float(row["latitude"])
            lon  = float(row["longitude"])
            conf = row.get("confidence", "").strip()

            # Filtrar solo detecciones con confianza nominal o alta
            if conf.lower() in ("l", "low"):
                continue

            record = {
                "lat":          lat,
                "lon":          lon,
                "brightness":   _to_float(row.get("brightness")),
                "scan":         _to_float(row.get("scan")),
                "track":        _to_float(row.get("track")),
                "acq_date":     row.get("acq_date", "").strip(),
                "acq_time":     str(row.get("acq_time", "")).zfill(4),
                "confidence":   _to_int(conf) if conf.lstrip("-").isdigit() else None,
                "daynight":     row.get("daynight", "").strip().upper(),
                "extracted_at": extracted_at,
            }
            records.append(record)

        except (ValueError, KeyError) as e:
            log.debug("Fila FIRMS omitida: %s", e)
            continue

    log.info("NASA FIRMS → %d incendios extraídos (confianza nominal/alta)", len(records))
    return records


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
