"""
config.py
=========
Configuración centralizada del pipeline de monitorización ambiental.
Modifica este archivo para ajustar ubicaciones, parámetros y rutas.
"""

import os

# Carga variables de entorno desde pipeline/.env si existe (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # dotenv opcional — también funciona con export OPENAQ_API_KEY="..."

# ─── Base del proyecto ───────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH y LOG_DIR son sobreescribibles via variable de entorno
# (útil en Docker para montar un volumen compartido entre servicios)
DB_PATH  = os.environ.get("DB_PATH",  os.path.join(BASE_DIR, "biodiversity_monitor.db"))
LOG_DIR  = os.environ.get("LOG_DIR",  os.path.join(BASE_DIR, "logs"))
# ─── Ubicaciones de monitoreo (globales) ────────────────────────────────────
# Cada entrada: nombre, latitud, longitud, país ISO-2
LOCATIONS = [
    {"name": "São Paulo",    "lat": -23.5505, "lon": -46.6333, "country": "BR"},
    {"name": "Nairobi",      "lat":  -1.2921, "lon":  36.8219, "country": "KE"},
    {"name": "Delhi",        "lat":  28.6139, "lon":  77.2090, "country": "IN"},
    {"name": "Beijing",      "lat":  39.9042, "lon": 116.4074, "country": "CN"},
    {"name": "Los Angeles",  "lat":  34.0522, "lon": -118.2437,"country": "US"},
    {"name": "London",       "lat":  51.5074, "lon":  -0.1278, "country": "GB"},
    {"name": "Sydney",       "lat": -33.8688, "lon": 151.2093, "country": "AU"},
]

# ─── OpenAQ ─────────────────────────────────────────────────────────────────
# API key gratuita en: https://explore.openaq.org/register
# Pégala entre las comillas de abajo (después de revocar la anterior)
OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY", "a074928ff81091ee283e2c6faf83af67291d654c00e0f8b80490bb5e5eed3561")
OPENAQ_BASE_URL   = "https://api.openaq.org/v3"
OPENAQ_PARAMETERS = ["pm25", "pm10", "no2", "o3", "co"]   # Contaminantes a extraer
OPENAQ_RADIUS_M   = 25_000                                  # Radio de búsqueda (metros)
OPENAQ_LIMIT      = 100                                     # Resultados por ubicación

# ─── Open-Meteo ─────────────────────────────────────────────────────────────
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_VARIABLES = [
    "temperature_2m_max", "precipitation_sum",
    "wind_speed_10m_max", "weather_code"
]
OPENMETEO_DAYS = 7   # Días de histórico a extraer (past_days)

# ─── GBIF (Biodiversidad) ───────────────────────────────────────────────────
GBIF_BASE_URL    = "https://api.gbif.org/v1/occurrence/search"
GBIF_LIMIT       = 100    # Ocurrencias por ubicación
GBIF_RADIUS_DEG  = 0.5    # Radio de búsqueda en grados (~55 km)
GBIF_CLASSES     = ["Mammalia", "Aves", "Reptilia", "Amphibia", "Insecta"]

# ─── NASA FIRMS (Incendios) ──────────────────────────────────────────────────
# Datos públicos CSV sin necesidad de API key
FIRMS_URL = (
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
    "modis-c6.1/csv/MODIS_C6_1_Global_7d.csv"
)

# ─── Scheduler ───────────────────────────────────────────────────────────────
# Expresión cron para ejecución diaria a las 02:00 AM
SCHEDULE_CRON = {"hour": 2, "minute": 0}

# ─── HTTP ────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30      # Segundos por llamada HTTP
REQUEST_RETRIES = 3       # Reintentos en caso de error
REQUEST_BACKOFF = 2       # Factor de espera exponencial entre reintentos
