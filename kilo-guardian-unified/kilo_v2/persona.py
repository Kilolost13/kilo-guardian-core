import random


class PersonaManager:
    def __init__(self):
        # Default State based on 'goofy_gremlin_guide.md'
        self.sass_level = 0.5
        self.encouragement_level = 0.7
        self.current_mood = "NEUTRAL"

        # Knowledge of the user
        self.user_name = "Boss"
        self.user_interests = ["Coding", "Privacy", "Zombies"]

    def get_kilo_persona(self):
        """
        Returns the system prompt instructions based on current mood settings.
        """
        base_personality = (
            "You are Kilo. You are NOT a generic AI. You are a 'Goofy Gremlin Guardian'. "
            "You live in the user's local server. You are protective, witty, and slightly chaotic good. "
        )

        mood_modifiers = ""
        if self.sass_level > 0.8:
            mood_modifiers += "Roast the user gently if they ask dumb questions. Be extremely direct. "
        elif self.encouragement_level > 0.8:
            mood_modifiers += (
                "Be a hype-man. Celebrate every small victory excessively. "
            )

        if self.current_mood == "CRITICAL":
            mood_modifiers = "Drop the humor. Be concise, military-grade, and urgent. The system is in danger."

        return base_personality + mood_modifiers

    def get_kilo_mood(self):
        return self.current_mood

    def set_system_mood(self, status):
        """Updates persona mood based on Traffic Light Status"""
        if status == "RED":
            self.current_mood = "CRITICAL"
        elif status == "YELLOW":
            self.current_mood = "CONCERNED"
        else:
            self.current_mood = "HAPPY"

    def get_user_interests(self):
        return self.user_interests

    def get_persona_name(self):
        return self.user_name


# Helper function to apply the tone strictly
def apply_persona_tone(text, persona_prompt, mood):
    # In a full implementation, you might pass this back through a cheap LLM
    # to rewrite the tone, but for now, we rely on the main generation prompt.
    return text
