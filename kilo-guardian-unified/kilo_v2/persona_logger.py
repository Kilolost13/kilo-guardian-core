# kilo_v2/persona_logger.py
import json
import os
import time
from typing import Any, Dict


class PersonaLogger:
    """
    Handles structured logging of persona adaptations for continuous learning
    and optimization.
    """

    def __init__(self, log_dir: str = "kilo_data/persona_logs"):
        """
        Initializes the logger and ensures the log directory exists.

        Args:
            log_dir (str): The directory to store persona log files.
        """
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.log_file = os.path.join(self.log_dir, "adaptations.jsonl")
        print(f"PersonaLogger initialized. Logging to: {self.log_file}")

    def log_adaptation(
        self,
        deviation_report: Any,
        pre_adjustment_traits: Dict[str, float],
        post_adjustment_traits: Dict[str, float],
        context: Dict[str, Any],
        outcome: Dict[str, Any],
    ):
        """
        Logs a complete persona adaptation event to a structured log file.

        Args:
            deviation_report (Any): The DeviationReport that triggered the adaptation.
            pre_adjustment_traits (Dict[str, float]): The dynamic persona state before the shift.
            post_adjustment_traits (Dict[str, float]): The dynamic persona state after the shift.
            context (Dict[str, Any]): The situational context of the interaction.
            outcome (Dict[str, Any]): Metrics on the outcome of the interaction,
                                     e.g., {'user_satisfaction': 0.9, 'task_completed': True}.
        """
        log_entry = {
            "timestamp": time.time(),
            "deviation_severity": deviation_report.severity,
            "deviation_summary": deviation_report.summary,
            "context": context,
            "persona_state_before": pre_adjustment_traits,
            "persona_state_after": post_adjustment_traits,
            "outcome": outcome,
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except IOError as e:
            print(f"Error: Could not write to persona log file: {e}")


# Example Usage
if __name__ == "__main__":
    from pattern_recognizer import DeviationReport

    logger = PersonaLogger()

    # Create dummy data for a sample log entry
    mock_report = DeviationReport(
        is_deviation=True, severity=0.9, summary="Test security alert"
    )
    mock_context = {"request_type": "security_alert", "source_ip": "192.168.1.101"}
    mock_pre_traits = {"SecurityFocus": 0.8, "Formality": 0.7}
    mock_post_traits = {"SecurityFocus": 1.0, "Formality": 1.0}
    mock_outcome = {
        "user_satisfaction": None,
        "task_completed": True,
        "alert_acknowledged": True,
    }

    print("\nLogging a sample adaptation event...")
    logger.log_adaptation(
        deviation_report=mock_report,
        pre_adjustment_traits=mock_pre_traits,
        post_adjustment_traits=mock_post_traits,
        context=mock_context,
        outcome=mock_outcome,
    )
    print("Log entry written.")

    # Verify content
    with open(logger.log_file, "r") as f:
        print("\n--- Log File Content ---")
        for line in f:
            print(line.strip())

    # Clean up the created log file for idempotency
    os.remove(logger.log_file)
    print("\nCleaned up sample log file.")
