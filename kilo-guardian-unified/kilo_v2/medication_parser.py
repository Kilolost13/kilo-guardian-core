"""
Medication Parser - Extract structured data from OCR text.

Parses medication labels to extract:
- Drug name
- Dosage (mg, mcg, IU, ml, etc.)
- Frequency (daily, twice daily, every X hours)
- Instructions (with food, before bed, as needed)
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MedicationParser")


class MedicationParser:
    """
    Parser for extracting structured medication data from OCR text.

    Technical decisions:
    1. Regex-based parsing (fast, deterministic, no ML training needed)
    2. Common medication dictionary for name matching
    3. Pattern priority: specific over generic (e.g., "twice daily" before "daily")
    4. Flexible matching: case-insensitive, handles OCR errors
    """

    # Common medication names (expandable list)
    COMMON_MEDICATIONS = {
        # Pain/Inflammation
        "aspirin",
        "ibuprofen",
        "acetaminophen",
        "tylenol",
        "advil",
        "aleve",
        "naproxen",
        "tramadol",
        "oxycodone",
        "hydrocodone",
        "codeine",
        "morphine",
        # Blood pressure/Heart
        "lisinopril",
        "amlodipine",
        "metoprolol",
        "losartan",
        "atenolol",
        "carvedilol",
        "atorvastatin",
        "simvastatin",
        "rosuvastatin",
        "lipitor",
        "crestor",
        # Diabetes
        "metformin",
        "insulin",
        "glipizide",
        "glyburide",
        "januvia",
        "ozempic",
        # Antibiotics
        "amoxicillin",
        "azithromycin",
        "ciprofloxacin",
        "doxycycline",
        "penicillin",
        # Mental health
        "sertraline",
        "zoloft",
        "prozac",
        "fluoxetine",
        "lexapro",
        "escitalopram",
        "alprazolam",
        "xanax",
        "lorazepam",
        "ativan",
        "diazepam",
        "valium",
        # Thyroid
        "levothyroxine",
        "synthroid",
        "armour thyroid",
        # Asthma/Respiratory
        "albuterol",
        "montelukast",
        "singulair",
        "fluticasone",
        "budesonide",
        # Stomach/GI
        "omeprazole",
        "prilosec",
        "pantoprazole",
        "ranitidine",
        "famotidine",
        # Vitamins/Supplements
        "vitamin d",
        "vitamin d3",
        "vitamin b12",
        "vitamin c",
        "multivitamin",
        "calcium",
        "magnesium",
        "iron",
        "folic acid",
        "fish oil",
        "omega-3",
    }

    # Dosage units
    DOSAGE_UNITS = [
        "mg",
        "mcg",
        "g",
        "ml",
        "iu",
        "units",
        "meq",
        "milligram",
        "microgram",
        "milliliter",
        "gram",
    ]

    # Frequency keywords (ordered by specificity - most specific first)
    FREQUENCY_PATTERNS = [
        (r"\bevery\s+(\d+)\s+hours?\b", "every {} hours"),
        (r"\bevery\s+(\d+)\s+hour?\b", "every {} hours"),
        (r"\b(\d+)\s+times?\s+(?:per|a)\s+day\b", "{} times daily"),
        (r"\b(\d+)\s+times?\s+daily\b", "{} times daily"),
        (r"\bthree\s+times?\s+(?:per|a)\s+day\b", "three times daily"),
        (r"\bthree\s+times?\s+daily\b", "three times daily"),
        (r"\btwice\s+(?:per|a)\s+day\b", "twice daily"),
        (r"\btwice\s+daily\b", "twice daily"),
        (r"\bonce\s+(?:per|a)\s+day\b", "once daily"),
        (r"\bonce\s+daily\b", "once daily"),
        (r"\bdaily\b", "once daily"),
        (r"\bas\s+needed\b", "as needed"),
        (r"\bprn\b", "as needed"),
        (r"\bevery\s+other\s+day\b", "every other day"),
        (r"\bweekly\b", "once weekly"),
        (r"\bmonthly\b", "once monthly"),
    ]

    # Time-of-day patterns (ordered by specificity)
    TIME_PATTERNS = [
        (r"\b(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\b", "time_with_minutes"),
        (
            r"(?<!:)(?<!\d)\b(\d{1,2})\s*([ap]\.?m\.?)\b",
            "time_hour_only",
        ),  # Not preceded by colon or digit
        (r"\bmorning\b", "morning"),
        (r"\bevening\b", "evening"),
        (r"\bnight\b", "night"),
        (r"\bbedtime\b", "bedtime"),
        (r"\bbefore\s+bed\b", "bedtime"),
    ]

    # Instruction keywords
    INSTRUCTION_PATTERNS = [
        (r"\bwith\s+food\b", "with food"),
        (r"\bwith\s+meals?\b", "with food"),
        (r"\bafter\s+meals?\b", "after meals"),
        (r"\bbefore\s+meals?\b", "before meals"),
        (r"\bon\s+empty\s+stomach\b", "on empty stomach"),
        (r"\bbefore\s+bed\b", "before bed"),
        (r"\bat\s+bedtime\b", "at bedtime"),
        (r"\bdo\s+not\s+crush\b", "do not crush"),
        (r"\btake\s+with\s+water\b", "take with water"),
        (r"\bswallow\s+whole\b", "swallow whole"),
    ]

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse OCR text to extract structured medication data.

        Args:
            text: Raw OCR text from medication label

        Returns:
            Dictionary with:
                - name: Extracted drug name
                - dosage: Extracted dosage with units
                - frequency: Parsed frequency
                - times: Suggested times (if found)
                - instructions: Special instructions
                - raw_text: Original text
                - confidence: Parser confidence (0-100)
        """
        text_lower = text.lower()

        result = {
            "name": self._extract_medication_name(text_lower),
            "dosage": self._extract_dosage(text_lower),
            "frequency": self._extract_frequency(text_lower),
            "times": self._extract_times(text_lower),
            "instructions": self._extract_instructions(text_lower),
            "raw_text": text,
            "confidence": 0,
        }

        # Calculate confidence based on fields extracted
        confidence_score = 0
        if result["name"]:
            confidence_score += 40
        if result["dosage"]:
            confidence_score += 30
        if result["frequency"]:
            confidence_score += 20
        if result["instructions"]:
            confidence_score += 10

        result["confidence"] = confidence_score

        logger.info(
            f"Parsed medication: {result['name']} {result['dosage']} ({confidence_score}% confidence)"
        )

        return result

    def _extract_medication_name(self, text: str) -> Optional[str]:
        """
        Extract medication name from text.

        Strategy:
        1. Check against known medication dictionary
        2. Look for drug name patterns (capitalized words at start)
        3. Return first match with highest confidence
        """
        # Check known medications
        for med_name in self.COMMON_MEDICATIONS:
            if med_name in text:
                # Return with proper capitalization
                return med_name.title()

        # Fallback: Look for capitalized words in first few lines
        lines = text.split("\n")
        for line in lines[:3]:  # Check first 3 lines
            words = line.strip().split()
            if words:
                # First word might be drug name
                first_word = words[0].strip(".,;:")
                if len(first_word) > 2:  # At least 3 chars
                    return first_word.title()

        return None

    def _extract_dosage(self, text: str) -> Optional[str]:
        """
        Extract dosage from text.

        Pattern: Number + Unit (e.g., "81mg", "1000 IU", "10 ml")
        """
        # Pattern: optional decimal number + optional space + unit
        for unit in self.DOSAGE_UNITS:
            # Try with space
            pattern = r"\b(\d+(?:\.\d+)?)\s*" + re.escape(unit) + r"\b"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)
                return f"{amount}{unit.lower()}"

        return None

    def _extract_frequency(self, text: str) -> Optional[str]:
        """
        Extract frequency from text.

        Uses priority-ordered patterns (most specific first).
        """
        for pattern, frequency_template in self.FREQUENCY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if "{}" in frequency_template:
                    # Pattern has capture group (e.g., "every 6 hours")
                    return frequency_template.format(match.group(1))
                else:
                    return frequency_template

        return None

    def _extract_times(self, text: str) -> List[str]:
        """
        Extract specific times from text.

        Returns list of times like ["08:00 AM", "20:00 PM"] or ["morning", "evening"]
        """
        times = []
        seen_times = set()  # Avoid duplicates

        for pattern, time_type in self.TIME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if time_type == "time_with_minutes":
                    # Format like "8:00 AM"
                    hour, minute, meridiem = match.groups()
                    time_str = f"{hour}:{minute} {meridiem.upper()}"
                    if time_str not in seen_times:
                        times.append(time_str)
                        seen_times.add(time_str)
                elif time_type == "time_hour_only":
                    # Format like "8 AM" (no minutes)
                    hour, meridiem = match.groups()
                    time_str = f"{hour}:00 {meridiem.upper()}"
                    if time_str not in seen_times:
                        times.append(time_str)
                        seen_times.add(time_str)
                else:
                    # Time of day like "morning", "bedtime"
                    if time_type not in seen_times:
                        times.append(time_type)
                        seen_times.add(time_type)

        return times

    def _extract_instructions(self, text: str) -> List[str]:
        """
        Extract special instructions from text.

        Returns list of instructions like ["with food", "do not crush"]
        """
        instructions = []

        for pattern, instruction in self.INSTRUCTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                instructions.append(instruction)

        return instructions

    def to_medication_form_data(self, parsed: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert parsed data to medication form format.

        Args:
            parsed: Output from parse() method

        Returns:
            Dictionary suitable for medication form pre-fill:
                - name: Drug name
                - dosage: Dosage string
                - frequency: Frequency description
                - times: Comma-separated times
                - notes: Instructions and raw text
        """
        # Convert times list to comma-separated string
        times_str = ", ".join(parsed.get("times", []))

        # If no specific times but have frequency, suggest times
        if not times_str and parsed.get("frequency"):
            times_str = self._suggest_times_from_frequency(parsed["frequency"])

        # Combine instructions into notes
        instructions = parsed.get("instructions", [])
        notes_parts = []
        if instructions:
            notes_parts.append("Instructions: " + "; ".join(instructions))
        notes_parts.append(f"Scanned from label")

        return {
            "name": parsed.get("name", ""),
            "dosage": parsed.get("dosage", ""),
            "frequency": parsed.get("frequency", ""),
            "times": times_str,
            "notes": " | ".join(notes_parts),
        }

    def _suggest_times_from_frequency(self, frequency: str) -> str:
        """
        Suggest default times based on frequency.

        Examples:
        - "once daily" -> "08:00"
        - "twice daily" -> "08:00, 20:00"
        - "three times daily" -> "08:00, 14:00, 20:00"
        """
        frequency_lower = frequency.lower()

        if "once" in frequency_lower or frequency_lower == "daily":
            return "08:00"
        elif "twice" in frequency_lower or "2 times" in frequency_lower:
            return "08:00, 20:00"
        elif "three" in frequency_lower or "3 times" in frequency_lower:
            return "08:00, 14:00, 20:00"
        elif "4 times" in frequency_lower:
            return "08:00, 12:00, 16:00, 20:00"
        elif "every 6 hours" in frequency_lower:
            return "06:00, 12:00, 18:00, 24:00"
        elif "every 8 hours" in frequency_lower:
            return "08:00, 16:00, 24:00"
        elif "every 12 hours" in frequency_lower:
            return "08:00, 20:00"

        return ""


# Singleton instance
_parser: Optional[MedicationParser] = None


def get_medication_parser() -> MedicationParser:
    """Get the global medication parser instance."""
    global _parser
    if _parser is None:
        _parser = MedicationParser()
    return _parser
