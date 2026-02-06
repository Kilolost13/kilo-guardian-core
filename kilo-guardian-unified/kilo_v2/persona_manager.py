# kilo_v2/persona_manager.py
import json
import logging
import os
from typing import Any, Dict, Literal

logger = logging.getLogger("PersonaManager")


class PersonaManager:
    """
    Manages the AI's persona by loading, validating, and providing access
    to tier-specific persona attributes.
    """

    def __init__(
        self,
        tier: Literal["home", "pro", "business"] = "home",
        personas_dir: str = "kilo_v2/personas",
    ):
        """
        Initializes the PersonaManager for a specific tier.

        Args:
            tier (Literal['home', 'pro']): The operational tier ('home' or 'pro').
            personas_dir (str): The directory where persona JSON files are stored.

        Raises:
            FileNotFoundError: If the persona configuration file for the tier does not exist.
            ValueError: If the loaded persona configuration is invalid.
        """
        self.tier = tier
        self.personas_dir = personas_dir
        self.persona_config = self.load_persona()

        # Extract both core and dynamic traits
        values = self.persona_config.get("values", {})
        self.traits = values.get("core_traits", values)

        logger.info(f"✅ PersonaManager initialized for tier: '{self.tier}'")
        logger.debug(f"Loaded traits: {self.traits}")

    def load_persona(self) -> Dict[str, Any]:
        """
        Loads the persona configuration file for the specified tier.

        Returns:
            Dict[str, Any]: The loaded persona configuration.
        """
        file_path = os.path.join(self.personas_dir, f"{self.tier}_persona.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Persona configuration file not found at: {file_path}"
            )

        with open(file_path, "r") as f:
            config = json.load(f)

        self.validate_persona(config)
        return config

    def validate_persona(self, config: Dict[str, Any]):
        """
        Validates the structure and values of the loaded persona configuration.

        Args:
            config (Dict[str, Any]): The persona configuration to validate.

        Raises:
            ValueError: If the configuration is missing required sections or values are invalid.
        """
        required_keys = ["tier", "schema", "values", "validation_rules"]
        for key in required_keys:
            if key not in config:
                raise ValueError(
                    f"Persona config for tier '{self.tier}' is missing required key: '{key}'"
                )

        schema_attributes = config["schema"].get("attributes", {})
        persona_values = config.get("values", {})

        # Check that all defined attributes are present
        if schema_attributes.keys() != persona_values.keys():
            raise ValueError(
                "Mismatch between attributes defined in schema and provided values."
            )

        # Handle nested values structure (core_traits/dynamic_traits)
        if "core_traits" in persona_values:
            traits_to_check = persona_values["core_traits"]
        else:
            traits_to_check = persona_values

        # Check that all values are within the 0.0-1.0 range
        for trait, value in traits_to_check.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"Invalid value for trait '{trait}': {value}. Must be between 0.0 and 1.0."
                )

        logger.info(f"✅ Persona for tier '{self.tier}' passed validation.")

    def get_traits(self) -> Dict[str, float]:
        """
        Returns the current persona trait values.

        Returns:
            Dict[str, float]: A dictionary of trait names and their values.
        """
        return self.traits.copy()

    def get_tier_definition(self) -> Dict[str, Any]:
        """
        Returns the full definition block for the current tier.
        """
        return {
            "tier_definition": self.persona_config.get("tier"),
            "attribute_schema": self.persona_config.get("schema"),
            "logic_implementation": "Logic is implemented in PersonaManager and ReasoningEngine based on loaded trait values.",
            "validation_rules": self.persona_config.get("validation_rules"),
            "adherence_metrics": self.persona_config.get("adherence_metrics"),
        }

    def get_system_prompt(self) -> str:
        """
        Generate a system prompt for the LLM based on the tier's persona traits.
        This shapes how the AI responds to users.
        """
        traits = self.get_traits()
        tier_name = self.persona_config.get("tier", self.tier)

        # Base prompt structure
        prompt_parts = [
            f"You are Kilo Guardian, an AI assistant operating in {tier_name} mode.\n"
        ]

        # Adjust tone based on Formality
        formality = traits.get("Formality", 0.5)
        if formality < 0.5:
            prompt_parts.append(
                "Communication Style: Friendly and conversational. Use simple language and relatable examples."
            )
        elif formality < 0.8:
            prompt_parts.append(
                "Communication Style: Professional but approachable. Balance technical accuracy with clarity."
            )
        else:
            prompt_parts.append(
                "Communication Style: Formal and business-professional. Use precise terminology and structured formatting."
            )

        # Adjust detail based on TechnicalDepth
        tech_depth = traits.get("TechnicalDepth", 0.5)
        if tech_depth < 0.5:
            prompt_parts.append(
                "\nDetail Level: Simplified explanations. Avoid jargon. Focus on practical outcomes."
            )
        elif tech_depth < 0.8:
            prompt_parts.append(
                "\nDetail Level: Technical detail with context. Include metrics and specific data points."
            )
        else:
            prompt_parts.append(
                "\nDetail Level: Comprehensive technical analysis. Include all relevant metrics, thresholds, and technical context."
            )

        # Adjust helpfulness
        helpfulness = traits.get("Helpfulness", 0.7)
        if helpfulness > 0.8:
            prompt_parts.append(
                "\nGuidance: Proactively offer suggestions and next steps. Anticipate user needs."
            )

        # Security focus
        security = traits.get("SecurityFocus", 0.7)
        if security > 0.8:
            prompt_parts.append(
                "\nSecurity: Prioritize security concerns. Always mention risks and safety implications."
            )

        # Business tier specific additions
        if self.tier == "business":
            prompt_parts.append("\n\nBusiness Mode Requirements:")
            prompt_parts.append(
                "- Begin responses with Executive Summary when providing analysis"
            )
            prompt_parts.append(
                "- Include Risk Assessment section for operational decisions"
            )
            prompt_parts.append(
                "- Note compliance and regulatory considerations where relevant"
            )
            prompt_parts.append(
                "- Provide formal recommendations with clear action items"
            )
            prompt_parts.append("- Use professional business language throughout")

        # Pro tier specific
        elif self.tier == "pro":
            prompt_parts.append(
                "\n\nPro Mode: Assume technical expertise. Provide detailed metrics, thresholds, and advanced options. Skip basic explanations."
            )

        # Home tier specific
        elif self.tier == "home":
            prompt_parts.append(
                "\n\nHome Mode: Be encouraging and supportive. Explain concepts clearly. Focus on what matters most to home users."
            )

        return "\n".join(prompt_parts)

    def format_response_prefix(self) -> str:
        """
        Get a response prefix/format hint based on tier.
        Used to structure responses appropriately.
        """
        if self.tier == "business":
            return "EXECUTIVE SUMMARY:\n"
        elif self.tier == "pro":
            return "ANALYSIS:\n"
        else:
            return ""  # Home users get casual responses


# Example of how this could be integrated into the application
if __name__ == "__main__":
    # This block demonstrates usage and would typically be in server_core.py

    # The application tier would be set via a config file or environment variable
    APP_TIER = "home"  # or 'pro'

    try:
        persona_manager = PersonaManager(tier=APP_TIER)

        # In the reasoning engine, you would get the current traits
        current_traits = persona_manager.get_traits()

        print("\n--- Simulating Reasoning Engine ---")
        if current_traits.get("TechnicalDepth", 0.5) > 0.7:
            print("Behavior: Providing a detailed, technical response.")
        else:
            print("Behavior: Providing a simplified, user-friendly response.")

        # You can also get the full definition string as requested
        tier_definition_string = persona_manager.get_tier_definition()
        print("\n--- Tier Definition String ---")
        import pprint

        pprint.pprint(tier_definition_string)

    except (FileNotFoundError, ValueError) as e:
        print(f"Error initializing PersonaManager: {e}")
