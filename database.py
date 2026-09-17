"""
database.py
===========
Gestión del esquema SQLite del pipeline.
Crea las tablas si no existen y registra cada ejecución del pipeline.
"""

import sqlite3
from contextlib import contextmanager
from config import DB_PATH
from logger import get_logger

log = get_logger("database")


@contextmanager
def get_connection():
    """Context manager que abre y cierra la conexión SQLite automáticamente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea todas las tablas del esquema si no existen."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # ── Calidad del Aire ─────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS air_quality (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                location    TEXT NOT NULL,       -- Nombre ciudad
                country     TEXT NOT NULL,
                lat         REAL NOT NULL,
                lon         REAL NOT NULL,
                parameter   TEXT NOT NULL,       -- pm25, no2, o3, co, pm10
                value       REAL NOT NULL,
                unit        TEXT NOT NULL,
                datetime_utc TEXT NOT NULL,
                extracted_at TEXT NOT NULL,
                UNIQUE(location, parameter, datetime_utc)
            )
        """)

        # ── Variables Climáticas ─────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                location         TEXT NOT NULL,
                country          TEXT NOT NULL,
                lat              REAL NOT NULL,
                lon              REAL NOT NULL,
                date             TEXT NOT NULL,
                temperature_2m   REAL,           -- °C
                precipitation    REAL,           -- mm
                windspeed_10m    REAL,           -- km/h
                humidity         REAL,           -- %
                weathercode      INTEGER,        -- WMO code
                extracted_at     TEXT NOT NULL,
                UNIQUE(location, date)
            )
        """)

        # ── Ocurrencias de Biodiversidad (GBIF) ─────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biodiversity (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                gbif_key        INTEGER UNIQUE,
                species         TEXT,
                kingdom         TEXT,
                phylum          TEXT,
                class           TEXT,
                order_name      TEXT,
                family          TEXT,
                lat             REAL,
                lon             REAL,
                country         TEXT,
                event_date      TEXT,
                basis_of_record TEXT,           -- HUMAN_OBSERVATION, MACHINE_OBSERVATION, etc.
                location_ref    TEXT,           -- Ciudad de monitoreo más cercana
                extracted_at    TEXT NOT NULL
            )
        """)

        # ── Incendios Activos (NASA FIRMS) ───────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fire_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lat         REAL NOT NULL,
                lon         REAL NOT NULL,
                brightness  REAL,               -- K (temperatura de brillo)
                scan        REAL,               -- km (tamaño del píxel escaneado)
                track       REAL,               -- km
                acq_date    TEXT NOT NULL,       -- YYYY-MM-DD
                acq_time    TEXT NOT NULL,       -- HHMM
                confidence  INTEGER,            -- 0-100%
                daynight    TEXT,               -- D / N
                extracted_at TEXT NOT NULL,
                UNIQUE(lat, lon, acq_date, acq_time)
            )
        """)

        # ── Registro de Ejecuciones ──────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                extractor      TEXT NOT NULL,   -- openaq | openmeteo | gbif | nasafirms
                start_time     TEXT NOT NULL,
                end_time       TEXT,
                status         TEXT NOT NULL,   -- running | success | error
                records_loaded INTEGER DEFAULT 0,
                error_message  TEXT
            )
        """)

    log.info("Base de datos inicializada correctamente en %s", DB_PATH)


def log_run_start(extractor: str) -> int:
    """Registra el inicio de una ETL y devuelve el ID de la ejecución."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO pipeline_runs (extractor, start_time, status) VALUES (?, ?, 'running')",
            (extractor, now)
        )
        return cur.lastrowid


def log_run_end(run_id: int, records: int = 0, error: str = None):
    """Actualiza el registro de ejecución con el resultado."""
    from datetime import datetime, timezone
    now    = datetime.now(timezone.utc).isoformat()
    status = "error" if error else "success"
    with get_connection() as conn:
        conn.execute(
            """UPDATE pipeline_runs
               SET end_time=?, status=?, records_loaded=?, error_message=?
               WHERE id=?""",
            (now, status, records, error, run_id)
        )
