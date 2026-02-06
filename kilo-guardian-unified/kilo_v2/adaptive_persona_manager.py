# kilo_v2/adaptive_persona_manager.py
import json
import os
from typing import Any, Dict, Literal

from kilo_v2.pattern_recognizer import DeviationReport, PatternRecognizer
from kilo_v2.persona_logger import PersonaLogger


class AdaptivePersonaManager:
    """
    Manages a dynamic, adaptive persona that adjusts to real-time situations
    based on learned patterns and detected deviations.
    """

    def __init__(
        self, tier: Literal["home", "pro"], personas_dir: str = "kilo_v2/personas"
    ):
        """
        Initializes the manager, loads the persona, and sets up sub-modules.
        """
        self.tier = tier
        self.personas_dir = personas_dir

        # Load and validate persona structure
        self._config = self._load_config()
        self.core_traits = self._config.get("values", {}).get("core_traits", {})
        self.dynamic_traits = self._config.get("values", {}).get("dynamic_traits", {})

        if not self.core_traits or not self.dynamic_traits:
            raise ValueError(
                "Persona config must contain 'core_traits' and 'dynamic_traits'."
            )

        # Initialize sub-modules
        self.pattern_recognizer = PatternRecognizer()
        self.persona_logger = PersonaLogger()

        print(f"AdaptivePersonaManager initialized for tier: '{self.tier}'")
        print(f"Core Traits: {self.core_traits}")

    def _load_config(self) -> Dict[str, Any]:
        """Loads and validates the persona configuration file."""
        file_path = os.path.join(self.personas_dir, f"{self.tier}_persona.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Persona configuration file not found at: {file_path}"
            )

        with open(file_path, "r") as f:
            config = json.load(f)

        # Basic validation
        if (
            "values" not in config
            or "core_traits" not in config["values"]
            or "dynamic_traits" not in config["values"]
        ):
            raise ValueError(
                "Invalid persona structure. Missing 'values', 'core_traits', or 'dynamic_traits'."
            )
        return config

    def get_current_traits(self) -> Dict[str, float]:
        """Returns the current, real-time dynamic persona traits."""
        return self.dynamic_traits.copy()

    def adapt_persona(self, report: DeviationReport):
        """
        Adjusts the dynamic_traits based on the severity of a deviation.

        Args:
            report (DeviationReport): The report of the detected deviation.
        """
        if not report.is_deviation:
            # Optionally, add a decay mechanism to slowly revert to core traits over time
            return

        print(f"Adapting persona due to deviation (severity: {report.severity:.2f})")
        magnitude = report.severity

        # Example adaptation logic:
        # For high-severity deviations, rapidly shift to a focused state.
        if magnitude > 0.8:
            self.dynamic_traits["SecurityFocus"] = min(
                self.core_traits["SecurityFocus"] + magnitude, 1.0
            )
            self.dynamic_traits["Formality"] = min(
                self.core_traits["Formality"] + magnitude, 1.0
            )
            self.dynamic_traits["Proactiveness"] = min(
                self.core_traits["Proactiveness"] + magnitude, 1.0
            )

        # For medium-severity, make a less drastic shift
        elif magnitude > 0.4:
            self.dynamic_traits["Proactiveness"] = min(
                self.core_traits["Proactiveness"] + (magnitude / 2), 1.0
            )

    def handle_interaction(self, context: Dict[str, Any], outcome: Dict[str, Any]):
        """
        The main handler for processing an interaction. It detects deviations,
        adapts the persona, and logs the entire event.

        Args:
            context (Dict[str, Any]): The situational context of the interaction.
            outcome (Dict[str, Any]): The result of the interaction.
        """
        # 1. Learn from the context to update the baseline
        self.pattern_recognizer.learn_pattern(context)

        # 2. Detect deviations from the norm
        deviation_report = self.pattern_recognizer.detect_deviation(context)

        # 3. If deviation is found, adapt the persona
        pre_adjustment_traits = self.get_current_traits()
        if deviation_report.is_deviation:
            self.adapt_persona(deviation_report)
        post_adjustment_traits = self.get_current_traits()

        # 4. Log the entire event for future analysis and learning
        self.persona_logger.log_adaptation(
            deviation_report=deviation_report,
            pre_adjustment_traits=pre_adjustment_traits,
            post_adjustment_traits=post_adjustment_traits,
            context=context,
            outcome=outcome,
        )
        print("Interaction handled and logged.")


# Example Usage
if __name__ == "__main__":
    # Initialize for the 'pro' tier
    manager = AdaptivePersonaManager(tier="pro")

    print("\n--- Simulating a Normal Interaction ---")
    normal_context = {"request_type": "file_search", "user_sentiment": "neutral"}
    normal_outcome = {"task_completed": True, "user_satisfaction": 0.9}
    manager.handle_interaction(normal_context, normal_outcome)
    print(f"Dynamic traits after normal interaction: {manager.get_current_traits()}")

    print("\n--- Simulating a HIGH-SEVERITY Deviation ---")
    security_context = {"request_type": "security_alert", "source_ip": "203.0.113.78"}
    security_outcome = {"task_completed": True, "alert_acknowledged": True}
    manager.handle_interaction(security_context, security_outcome)
    print(f"Dynamic traits after security alert: {manager.get_current_traits()}")

    # Clean up logs
    log_file = manager.persona_logger.log_file
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"\nCleaned up sample log file: {log_file}")
