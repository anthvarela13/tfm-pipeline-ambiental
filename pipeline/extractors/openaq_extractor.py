"""
openaq_extractor.py
===================
Extrae mediciones de calidad del aire desde la API pública de OpenAQ v3.
Fuente: https://api.openaq.org/v3

Para cada ubicación configurada busca estaciones dentro de un radio definido
y recupera las últimas mediciones de los parámetros de interés.
"""

import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (OPENAQ_BASE_URL, OPENAQ_PARAMETERS, OPENAQ_RADIUS_M,
                    OPENAQ_LIMIT, OPENAQ_API_KEY, LOCATIONS, REQUEST_TIMEOUT,
                    REQUEST_RETRIES, REQUEST_BACKOFF)
from logger import get_logger

log = get_logger("extractor.openaq")

# Encabezados HTTP — la API key va en X-API-Key (requerida desde v3)
def _headers() -> dict:
    h = {"Accept": "application/json"}
    if OPENAQ_API_KEY:
        h["X-API-Key"] = OPENAQ_API_KEY
    else:
        log.warning("OPENAQ_API_KEY no configurada. Regístrate en https://explore.openaq.org/register")
    return h


def _get_with_retry(url: str, params: dict) -> dict:
    """Realiza una petición GET con reintentos y backoff exponencial."""
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT,
                                headers=_headers())
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            log.warning("Intento %d/%d fallido para %s: %s", attempt, REQUEST_RETRIES, url, e)
            if attempt < REQUEST_RETRIES:
                time.sleep(REQUEST_BACKOFF ** attempt)
    raise RuntimeError(f"No se pudo conectar a {url} tras {REQUEST_RETRIES} intentos")


def extract_air_quality() -> List[Dict[str, Any]]:
    """
    Extrae mediciones de calidad del aire para todas las ubicaciones configuradas.

    Retorna:
        Lista de diccionarios con campos:
        location, country, lat, lon, parameter, value, unit, datetime_utc, extracted_at
    """
    now_utc    = datetime.now(timezone.utc).isoformat()
    all_records: List[Dict[str, Any]] = []

    for loc in LOCATIONS:
        log.info("OpenAQ → extrayendo datos para %s (%s)", loc["name"], loc["country"])

        try:
            # Buscar estaciones cercanas a la ubicación
            stations_data = _get_with_retry(
                f"{OPENAQ_BASE_URL}/locations",
                params={
                    "coordinates": f"{loc['lat']},{loc['lon']}",
                    "radius": OPENAQ_RADIUS_M,
                    "limit": 10,
                }
            )

            stations = stations_data.get("results", [])
            if not stations:
                log.warning("Sin estaciones para %s en radio %dm", loc["name"], OPENAQ_RADIUS_M)
                continue

            log.debug("  → %d estaciones encontradas", len(stations))

            # Obtener mediciones de cada estación
            for station in stations[:5]:   # Máximo 5 estaciones por ciudad
                station_id = station.get("id")
                if not station_id:
                    continue

                # En v3, el campo 'parameter' NO viene en /latest — está en station['sensors']
                # Construimos un mapa: sensorsId → {name, units}
                sensor_map = {
                    s["id"]: {
                        "name":  s["parameter"]["name"],
                        "units": s["parameter"]["units"],
                    }
                    for s in station.get("sensors", [])
                    if s.get("parameter")
                }

                measures_data = _get_with_retry(
                    f"{OPENAQ_BASE_URL}/locations/{station_id}/latest",
                    params={"limit": OPENAQ_LIMIT}
                )

                for measure in measures_data.get("results", []):
                    sensor_info = sensor_map.get(measure.get("sensorsId"), {})
                    param = sensor_info.get("name", "").lower()
                    unit  = sensor_info.get("units", "µg/m³")
                    dt_raw = measure.get("datetime", {}) or {}
                    dt_utc = dt_raw.get("utc", now_utc) if isinstance(dt_raw, dict) else now_utc

                    if param not in OPENAQ_PARAMETERS or measure.get("value") is None:
                        continue

                    all_records.append({
                        "location":     loc["name"],
                        "country":      loc["country"],
                        "lat":          measure.get("coordinates", {}).get("latitude",  loc["lat"]),
                        "lon":          measure.get("coordinates", {}).get("longitude", loc["lon"]),
                        "parameter":    param,
                        "value":        measure["value"],
                        "unit":         unit,
                        "datetime_utc": dt_utc,
                        "extracted_at": now_utc,
                    })

            # Pausa cortés para no sobrecargar la API
            time.sleep(0.5)

        except Exception as e:
            log.error("Error extrayendo OpenAQ para %s: %s", loc["name"], e)
            continue

    log.info("OpenAQ → %d registros extraídos en total", len(all_records))
    return all_records
