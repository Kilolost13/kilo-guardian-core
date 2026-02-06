import logging
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler

# --- Professional Logging Setup ---
# Rotates logs so they don't fill up the disk [cite: 121]
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] (WATCHDOG) %(message)s")
log_handler = RotatingFileHandler(
    "kilo_watchdog.log", maxBytes=5 * 1024 * 1024, backupCount=5
)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger("KiloWatchdog")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler(sys.stdout))


def start_kilo_core():
    logger.info("🟢 Initiating Kilo Core Sequence...")
    # This runs the actual server as a subprocess
    process = subprocess.Popen([sys.executable, "server_core.py"])
    return process


def main():
    process = start_kilo_core()

    while True:
        try:
            # Check if process is still running
            status = process.poll()

            if status is not None:
                # Process has died
                logger.error(f"🔴 CRITICAL: Kilo Core crashed with exit code {status}.")
                logger.warning("⚠️ Attempting emergency restart in 5 seconds...")

                # TODO: Insert code here to send Push Notification/SMS [cite: 120]

                time.sleep(5)
                process = start_kilo_core()

            time.sleep(2)  # Check every 2 seconds

        except KeyboardInterrupt:
            logger.info("🛑 User shutdown requested. Killing Core...")
            process.terminate()
            break
        except Exception as e:
            logger.error(f"🔴 Watchdog Error: {e}")


if __name__ == "__main__":
    main()
