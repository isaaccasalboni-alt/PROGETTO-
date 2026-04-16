import logging
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DailyScheduler:
    def __init__(self, run_time: str | None = None):
        self.run_time = run_time or os.getenv("DAILY_RUN_TIME", "09:00")
        self.scheduler = BlockingScheduler(timezone="Europe/Rome")

    def start(self, job_func) -> None:
        """Avvia lo scheduler con esecuzione giornaliera all'orario configurato."""
        try:
            hour, minute = map(int, self.run_time.split(":"))
        except ValueError:
            raise ValueError(
                f"Formato orario non valido: '{self.run_time}'. Usa HH:MM (es. 09:00)"
            )

        self.scheduler.add_job(
            func=job_func,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="instagram_daily_post",
            name="Instagram Daily Post Generator",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        logger.info(f"Scheduler avviato — esecuzione giornaliera alle {self.run_time}")
        logger.info("Premi Ctrl+C per fermare")

        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler fermato dall'utente")
            self.scheduler.shutdown()
