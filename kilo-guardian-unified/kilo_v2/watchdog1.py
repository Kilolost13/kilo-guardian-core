import logging
import subprocess
import sys
import time
from threading import Thread

# --- WATCHDOG SETUP ---

# Configure logging for the watchdog itself
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG - %(levelname)s] %(message)s",
    handlers=[logging.FileHandler("watchdog.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Watchdog")

# Command to launch your FastAPI server (Kilo Core)
# IMPORTANT: Use 'uvicorn server_core:app' or the specific command you use to start the server
KILO_CORE_COMMAND = [
    "uvicorn",
    "server_core:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
]

# --- STREAM CAPTURE FUNCTIONS ---


def stream_reader(stream, log_func, prefix):
    """Reads output from a process stream line by line and logs it."""
    for line in stream:
        log_func(f"[{prefix}] {line.strip()}")


def launch_kilo_core():
    """Launches Kilo Core and captures its stdout/stderr."""
    logger.info("🚀 Launching Kilo Core process...")

    # Set up the subprocess to capture stdout and stderr
    try:
        process = subprocess.Popen(
            KILO_CORE_COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Read output as text (decoded)
        )

        logger.info(f"Kilo Core PID: {process.pid}")

        # Start two separate threads to read stdout and stderr simultaneously
        stdout_thread = Thread(
            target=stream_reader,
            args=(process.stdout, logger.info, "CORE-OUT"),
            daemon=True,
        )
        stderr_thread = Thread(
            target=stream_reader,
            args=(process.stderr, logger.error, "CORE-ERR"),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        # Wait for the process to terminate
        process.wait()

        # When we reach here, Kilo Core has exited.
        status = process.returncode

        # Ensure the threads finish reading any remaining output
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        if status == 0:
            logger.error(
                f"🔴 CRITICAL: Kilo Core crashed with **GRACEFUL EXIT CODE 0**."
            )
            logger.error(
                "  -> This usually means an unhandled exception (e.g., ImportError, uninitialized variable) occurred during the Uvicorn worker startup."
            )
        else:
            logger.error(f"🔴 CRITICAL: Kilo Core crashed with Exit Code {status}.")

        logger.info(
            "Review the logged [CORE-ERR] messages above for the Python traceback!"
        )
        return status

    except FileNotFoundError:
        logger.error(
            f"❌ ERROR: Command not found. Is '{KILO_CORE_COMMAND[0]}' installed and in your PATH? (e.g., 'uvicorn')"
        )
        return 1
    except Exception as e:
        logger.critical(f"❌ WATCHDOG FAILURE: Could not launch process: {e}")
        return 1


if __name__ == "__main__":
    exit_code = 0
    while True:
        logger.info("-" * 50)
        exit_code = launch_kilo_core()

        # --- RESTART POLICY ---
        if exit_code == 0:
            logger.error(
                "Kilo Core exited cleanly (Exit 0). This suggests a severe startup bug. Retying in 5 seconds..."
            )
            time.sleep(5)
        elif exit_code != 0:
            logger.error(
                f"Kilo Core exited with error code {exit_code}. Retying in 10 seconds..."
            )
            time.sleep(10)

        # You can add logic here to stop after N retries.
