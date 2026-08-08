import argparse
import os
import subprocess
import sys
import time

from config.settings import settings
from database.connection import init_db
from services.orchestrator import PipelineOrchestrator
from services.scheduler import AgentScheduler
from utils.logger import logger


def run_single_sync():
    """Executes a single processing cycle over inbox."""
    logger.info("Executing single email automation sync pass...")
    orchestrator = PipelineOrchestrator()
    metrics = orchestrator.run_pipeline()
    print("\n==========================================")
    print("      SYNC CYCLE METRICS SUMMARY          ")
    print("==========================================")
    for k, v in metrics.items():
        print(f"  {k:<25}: {v}")
    print("==========================================\n")


def run_daemon_scheduler():
    """Starts continuous background scheduler."""
    logger.info("Starting Placement Email AI Agent in Daemon Mode...")
    init_db()
    # Run immediate sync on start
    run_single_sync()

    scheduler = AgentScheduler(interval_seconds=settings.CHECK_INTERVAL)
    scheduler.start()

    print(f"\n🚀 AI Agent is continuously monitoring inbox every {settings.CHECK_INTERVAL} seconds.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping daemon...")
        scheduler.stop()


def launch_dashboard():
    """Launches the Streamlit UI dashboard."""
    dashboard_path = settings.BASE_DIR / "app" / "dashboard.py"
    logger.info(f"Launching Streamlit dashboard from {dashboard_path}...")
    cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_path)]
    subprocess.run(cmd)


def launch_api():
    """Launches the FastAPI application server."""
    logger.info("Launching FastAPI server on port 8000...")
    cmd = [sys.executable, "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="AI Email Task Automation Agent - Autonomous Placement & Interview Tracker"
    )
    parser.add_argument("--sync", action="store_true", help="Run a single email fetch & task extraction sync pass.")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit monitoring dashboard.")
    parser.add_argument("--api", action="store_true", help="Launch FastAPI web server.")
    parser.add_argument("--init-db", action="store_true", help="Initialize SQLite database schema.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode using sample placement emails.")

    args = parser.parse_args()

    # Initialize DB first
    init_db()

    if args.dry_run:
        settings.ENABLE_DRY_RUN = True
        logger.info("Dry-run mode activated.")
        run_single_sync()
        return

    if args.init_db:
        logger.info("Database initialized successfully.")
        return

    if args.dashboard:
        launch_dashboard()
        return

    if args.api:
        launch_api()
        return

    if args.sync:
        run_single_sync()
        return

    # Default execution when run with `python main.py`: Run single pass & start continuous scheduler daemon
    run_daemon_scheduler()


if __name__ == "__main__":
    main()
