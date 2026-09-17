"""
sqlite_loader.py
================
Carga los datos transformados en la base de datos SQLite del pipeline.
Usa INSERT OR IGNORE para evitar duplicados gracias a las constraints UNIQUE
definidas en el esquema (database.py).
"""

from typing import List, Dict, Any
from database import get_connection, log_run_start, log_run_end
from logger import get_logger

log = get_logger("loader.sqlite")


def load_air_quality(records: List[Dict[str, Any]]) -> int:
    """Carga registros de calidad del aire. Retorna número de filas insertadas."""
    run_id = log_run_start("openaq")
    inserted = 0
    try:
        with get_connection() as conn:
            for r in records:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO air_quality
                        (location, country, lat, lon, parameter, value, unit,
                         datetime_utc, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["location"], r["country"], r["lat"], r["lon"],
                      r["parameter"], r["value"], r["unit"],
                      r["datetime_utc"], r["extracted_at"]))
                inserted += cur.rowcount
        log.info("Calidad del aire → %d/%d filas insertadas", inserted, len(records))
        log_run_end(run_id, records=inserted)
    except Exception as e:
        log.error("Error cargando calidad del aire: %s", e)
        log_run_end(run_id, error=str(e))
        raise
    return inserted


def load_weather(records: List[Dict[str, Any]]) -> int:
    """Carga registros meteorológicos. Retorna número de filas insertadas."""
    run_id = log_run_start("openmeteo")
    inserted = 0
    try:
        with get_connection() as conn:
            for r in records:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO weather
                        (location, country, lat, lon, date, temperature_2m,
                         precipitation, windspeed_10m, humidity, weathercode,
                         extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["location"], r["country"], r["lat"], r["lon"],
                      r["date"], r["temperature_2m"], r["precipitation"],
                      r["windspeed_10m"], r["humidity"], r["weathercode"],
                      r["extracted_at"]))
                inserted += cur.rowcount
        log.info("Clima → %d/%d filas insertadas", inserted, len(records))
        log_run_end(run_id, records=inserted)
    except Exception as e:
        log.error("Error cargando clima: %s", e)
        log_run_end(run_id, error=str(e))
        raise
    return inserted


def load_biodiversity(records: List[Dict[str, Any]]) -> int:
    """Carga ocurrencias de biodiversidad. Retorna número de filas insertadas."""
    run_id = log_run_start("gbif")
    inserted = 0
    try:
        with get_connection() as conn:
            for r in records:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO biodiversity
                        (gbif_key, species, kingdom, phylum, class, order_name,
                         family, lat, lon, country, event_date, basis_of_record,
                         location_ref, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["gbif_key"], r["species"], r["kingdom"], r["phylum"],
                      r["class"], r["order_name"], r["family"],
                      r["lat"], r["lon"], r["country"], r["event_date"],
                      r["basis_of_record"], r["location_ref"], r["extracted_at"]))
                inserted += cur.rowcount
        log.info("Biodiversidad → %d/%d filas insertadas", inserted, len(records))
        log_run_end(run_id, records=inserted)
    except Exception as e:
        log.error("Error cargando biodiversidad: %s", e)
        log_run_end(run_id, error=str(e))
        raise
    return inserted


def load_fires(records: List[Dict[str, Any]]) -> int:
    """Carga registros de incendios. Retorna número de filas insertadas."""
    run_id = log_run_start("nasafirms")
    inserted = 0
    try:
        with get_connection() as conn:
            for r in records:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO fire_events
                        (lat, lon, brightness, scan, track, acq_date, acq_time,
                         confidence, daynight, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["lat"], r["lon"], r["brightness"], r["scan"],
                      r["track"], r["acq_date"], r["acq_time"],
                      r["confidence"], r["daynight"], r["extracted_at"]))
                inserted += cur.rowcount
        log.info("Incendios → %d/%d filas insertadas", inserted, len(records))
        log_run_end(run_id, records=inserted)
    except Exception as e:
        log.error("Error cargando incendios: %s", e)
        log_run_end(run_id, error=str(e))
        raise
    return inserted
