from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import settings
from services.orchestrator import PipelineOrchestrator
from utils.logger import logger


class AgentScheduler:
    """Configurable periodic scheduler running background email monitoring cycles."""

    def __init__(self, interval_seconds: int = None):
        self.interval_seconds = interval_seconds or settings.CHECK_INTERVAL
        self.orchestrator = PipelineOrchestrator()
        self.scheduler = BackgroundScheduler()

    def start(self):
        """Starts background interval job."""
        self.scheduler.add_job(
            func=self.orchestrator.run_pipeline,
            trigger="interval",
            seconds=self.interval_seconds,
            id="placement_email_agent_job",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"AgentScheduler started. Checking Gmail inbox every {self.interval_seconds} seconds.")

    def stop(self):
        """Stops background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("AgentScheduler background service stopped.")
