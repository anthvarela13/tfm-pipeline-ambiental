"""
scheduler.py
============
Configura la ejecución periódica del pipeline usando APScheduler.
Soporta dos modos:
  - Scheduled: ejecución automática según cron (por defecto 02:00 AM UTC diario)
  - Immediate:  ejecución manual inmediata (modo --now)

Uso:
    python scheduler.py           # Inicia el scheduler en modo daemon
    python scheduler.py --now     # Ejecuta el pipeline una vez ahora mismo
"""

import argparse
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from config import SCHEDULE_CRON
from logger import get_logger
from main import run_pipeline

log = get_logger("scheduler")


def start_scheduler():
    """Inicia el scheduler en modo daemon con trigger cron."""
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_pipeline,
        trigger=CronTrigger(**SCHEDULE_CRON),
        id="pipeline_daily",
        name="Pipeline Monitorización Ambiental",
        replace_existing=True,
        misfire_grace_time=3600,   # 1h de margen si el scheduler se reinicia tarde
    )

    log.info(
        "Scheduler iniciado. Próxima ejecución: %s (cron: hora=%s, minuto=%s)",
        scheduler.get_job("pipeline_daily").next_run_time,
        SCHEDULE_CRON.get("hour"),
        SCHEDULE_CRON.get("minute"),
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler detenido por el usuario.")
        scheduler.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de Monitorización Ambiental")
    parser.add_argument("--now", action="store_true",
                        help="Ejecutar el pipeline inmediatamente (sin scheduler)")
    args = parser.parse_args()

    if args.now:
        log.info("Modo inmediato: ejecutando pipeline ahora...")
        run_pipeline()
    else:
        start_scheduler()
