# Pipeline ETL de Monitorización Ambiental y su Impacto en la Biodiversidad Global

**Trabajo Fin de Máster · Perfil Data Engineer**  
Máster en Big Data, Data Science e Inteligencia Artificial  
Universidad Complutense de Madrid · 2026

---

## Descripción

Pipeline ETL automatizado que integra **cuatro fuentes de datos públicas** en una base de datos SQLite unificada, actualizada periódicamente y lista para análisis. Incluye un dashboard interactivo Streamlit y un modelo de clustering K-Means para segmentación de ciudades por perfil ambiental.

## Fuentes de Datos

| Fuente | Datos | API Key |
|--------|-------|---------|
| [OpenAQ v3](https://openaq.org) | Calidad del aire (PM2.5, NO₂, O₃, CO) | Sí (gratuita) |
| [Open-Meteo](https://open-meteo.com) | Temperatura, precipitación, viento | No |
| [GBIF](https://gbif.org) | Ocurrencias de flora y fauna | No |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | Incendios activos (MODIS satelital) | No |

**7 ciudades monitoreadas:** São Paulo · Nairobi · Delhi · Beijing · Los Ángeles · Londres · Sydney

## Arquitectura

```
pipeline/
├── config.py              # Parámetros centralizados
├── database.py            # Esquema SQLite y registro de ejecuciones
├── main.py                # Orquestador de las 4 ETLs
├── scheduler.py           # Scheduler APScheduler (cron diario 02:00 UTC)
├── app.py                 # Dashboard interactivo Streamlit
├── extractors/            # Un módulo por fuente de datos
│   ├── openaq_extractor.py
│   ├── openmeteo_extractor.py
│   ├── gbif_extractor.py
│   └── nasafirms_extractor.py
├── loaders/
│   └── sqlite_loader.py   # Carga idempotente con INSERT OR IGNORE
└── requirements.txt
Dockerfile.pipeline        # Imagen Docker del sistema
docker-compose.yml         # Orquestación pipeline + dashboard
```

## Instalación y Uso

### Opción 1 — Docker Compose (recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/anthvarela/tfm-pipeline-ambiental.git
cd tfm-pipeline-ambiental

# 2. Construir y arrancar pipeline + dashboard
docker-compose up --build

# 3. Abrir el dashboard en el navegador
open http://localhost:8501
```

### Opción 2 — Ejecución local

```bash
# Crear entorno virtual e instalar dependencias
cd pipeline/
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurar API key de OpenAQ (registro gratuito en https://explore.openaq.org)
echo "OPENAQ_API_KEY=tu_key_aqui" > .env

# Ejecutar el pipeline una vez
python scheduler.py --now

# Iniciar el scheduler (modo daemon, cron diario)
python scheduler.py

# Iniciar el dashboard
streamlit run app.py
```

## Dashboard

El dashboard Streamlit incluye 7 secciones navegables:

- **📊 Resumen** — KPIs globales y últimas ejecuciones del pipeline
- **💨 Calidad del Aire** — PM2.5 por ciudad vs. límite OMS (15 µg/m³)
- **🌡️ Clima** — Temperatura y precipitación (14 días)
- **🦁 Biodiversidad** — Distribución taxonómica y correlación PM2.5 vs. especies
- **🔥 Incendios** — Mapa global de focos activos (NASA FIRMS / MODIS)
- **🤖 Machine Learning** — Clustering K-Means con PCA y predicción de ciudades nuevas
- **🗂️ Explorador de Datos** — Tabla filtrable con descarga CSV

## Resultados Principales

| ETL | Registros extraídos | Registros cargados |
|-----|--------------------|--------------------|
| OpenAQ | 115 | 81 (idempotencia) |
| Open-Meteo | 98 | 98 |
| GBIF | 3.500 | 700 |
| NASA FIRMS | 96.198 | 96.198 |

**Clustering K-Means (K=2, silhouette=0.321):**
- 🔴 Cluster 1 — Alta contaminación: Delhi (267 µg/m³), Beijing — PM2.5 promedio 144.9 µg/m³
- 🔵 Cluster 0 — Perfil limpio: Londres, Los Ángeles, Nairobi, Sydney, São Paulo — PM2.5 promedio 11.6 µg/m³

**Correlación PM2.5 ↔ Riqueza de especies: r = −0.305** (tendencia negativa)

## Tecnologías

Python 3.11 · SQLite · requests · APScheduler · python-dotenv · pandas · numpy · matplotlib · scikit-learn · Streamlit · Docker · Docker Compose

## Notebook

El análisis completo (ETLs, consultas SQL, 5 gráficos y modelo ML) está documentado en  
`TFM_Pipeline_Monitorizacion_Ambiental.ipynb` — ejecutable directamente en Jupyter o Google Colab.

## Licencia

Código bajo licencia MIT. Los datos son propiedad de sus fuentes originales (OpenAQ, Open-Meteo, GBIF, NASA) con licencias abiertas para uso académico e investigación.
