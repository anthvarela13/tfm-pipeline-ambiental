"""
openmeteo_extractor.py
======================
Extrae datos meteorológicos históricos desde la API gratuita de Open-Meteo.
Fuente: https://api.open-meteo.com

No requiere API key. Proporciona datos horarios y diarios de variables climáticas
para cualquier coordenada geográfica.
"""

import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (OPENMETEO_BASE_URL, OPENMETEO_VARIABLES, OPENMETEO_DAYS,
                    LOCATIONS, REQUEST_TIMEOUT, REQUEST_RETRIES, REQUEST_BACKOFF)
from logger import get_logger
import time

log = get_logger("extractor.openmeteo")


def extract_weather() -> List[Dict[str, Any]]:
    """
    Extrae datos meteorológicos diarios para los últimos N días
    para cada ubicación configurada.

    Retorna:
        Lista de diccionarios con variables climáticas por ubicación y fecha.
    """
    now_utc      = datetime.now(timezone.utc)
    extracted_at = now_utc.isoformat()

    all_records: List[Dict[str, Any]] = []

    for loc in LOCATIONS:
        log.info("Open-Meteo → extrayendo clima para %s", loc["name"])

        # past_days evita el error 400 que ocurre con start_date/end_date en /forecast
        params = {
            "latitude":  loc["lat"],
            "longitude": loc["lon"],
            "daily":     ",".join(OPENMETEO_VARIABLES),
            "past_days": OPENMETEO_DAYS,
            "timezone":  "UTC",
        }

        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                resp = requests.get(OPENMETEO_BASE_URL, params=params,
                                    timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.RequestException as e:
                log.warning("Intento %d/%d fallido para %s: %s", attempt, REQUEST_RETRIES, loc["name"], e)
                if attempt < REQUEST_RETRIES:
                    time.sleep(REQUEST_BACKOFF ** attempt)
                else:
                    log.error("No se pudo extraer Open-Meteo para %s", loc["name"])
                    data = None

        if not data:
            continue

        daily = data.get("daily", {})
        dates = daily.get("time", [])

        for i, date in enumerate(dates):
            record = {
                "location":       loc["name"],
                "country":        loc["country"],
                "lat":            loc["lat"],
                "lon":            loc["lon"],
                "date":           date,
                "temperature_2m": _safe_get(daily, "temperature_2m_max", i),
                "precipitation":  _safe_get(daily, "precipitation_sum", i),
                "windspeed_10m":  _safe_get(daily, "wind_speed_10m_max", i),
                "humidity":       None,   # no disponible como agregado diario en Open-Meteo
                "weathercode":    _safe_get(daily, "weather_code", i),
                "extracted_at":   extracted_at,
            }
            all_records.append(record)

        time.sleep(0.3)

    log.info("Open-Meteo → %d registros extraídos", len(all_records))
    return all_records


def _safe_get(daily: dict, key: str, index: int):
    """Devuelve el valor en la posición index o None si no existe."""
    values = daily.get(key, [])
    return values[index] if index < len(values) else None
