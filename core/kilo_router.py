#!/usr/bin/env python3
"""
Kilo Command Router - Intelligent intent classification and routing
"""

from typing import Dict, Any, Tuple
import re


class KiloRouter:
    """Routes user commands to appropriate handlers based on intent"""

    # Command patterns with regex
    PATTERNS = {
        # Memory/Learning commands
        "teach": [
            r"teach\s+(?:fact|me|that)?\s*:?\s*(.+)",
            r"remember\s+(?:that)?\s*(.+)",
            r"learn\s+(?:that)?\s*(.+)",
            r"store\s+(?:fact|that)?\s*:?\s*(.+)",
        ],

        "recall": [
            r"what\s+(?:did\s+i\s+tell\s+you|do\s+you\s+know)\s+about\s+(.+)",
            r"recall\s+(.+)",
            r"what\s+is\s+my\s+(.+)",
            r"do\s+you\s+remember\s+(.+)",
        ],

        # Cluster status queries
        "status": [
            r"(?:what'?s|what\s+is)\s+(?:the\s+)?(?:cluster\s+)?status",
            r"(?:show|check)\s+(?:cluster\s+)?status",
            r"what'?s\s+running",
            r"are\s+(?:any\s+)?services\s+running",
            r"is\s+(?:the\s+)?cluster\s+(?:up|online|healthy)",
            r"how\s+(?:is\s+)?(?:the\s+)?cluster",
            r"analyze\s+(?:the\s+)?cluster",
        ],

        # Cluster control commands
        "control": [
            r"start\s+(?:all\s+)?services?",
            r"stop\s+(?:all\s+)?services?",
            r"restart\s+(?:all\s+)?services?",
            r"start\s+(\w+)",
            r"stop\s+(\w+)",
            r"scale\s+(\w+)",
        ],

        # Advice/Recommendation requests (Expanded for Finance)
        "advice": [
            r"what\s+should\s+i\s+(?:add|install|do)",
            r"(?:any\s+)?suggestions?",
            r"how\s+(?:can\s+i|do\s+i)\s+improve",
            r"what'?s\s+missing",
            r"recommend(?:ations)?",
            r"analyze\s+(?:my\s+)?(?:finance|spending|financials|data)",
            r"financial\s+(?:insight|advice|analysis)",
            r"check\s+(?:my\s+)?(?:spending|budget)",
        ],

        # Troubleshooting
        "troubleshoot": [
            r"why\s+(?:is|isn'?t|aren'?t)\s+(.+)",
            r"what'?s\s+wrong\s+(?:with)?",
            r"(?:help|fix)\s+(.+)",
            r"error\s+(?:with|in)\s+(.+)",
            r"(.+)\s+(?:not\s+working|broken|failed)",
        ],

        # Memory/Resource queries
        "resources": [
            r"(?:how\s+much|what'?s\s+the)\s+(?:memory|ram|cpu)",
            r"resource\s+usage",
            r"memory\s+(?:usage|status)",
            r"can\s+i\s+(?:run|start)\s+(.+)",
        ],
        
        # Follow-up actions
        "follow_up": [
            r"^ok\s+do\s+that",
            r"^do\s+it",
            r"^go\s+ahead",
            r"^proceed",
            r"^yes",
            r"^run\s+the\s+analysis",
        ],
    }

    def __init__(self):
        """Initialize the router"""
        pass

    def classify_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Classify the user's message intent
        """
        message_lower = message.lower().strip()

        # Check each pattern category
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    # Extract any captured groups
                    extracted = {}
                    if match.groups():
                        extracted["captured"] = match.group(1) if len(match.groups()) == 1 else match.groups()

                    return intent, extracted

        # Default to general chat
        return "chat", {}

    def parse_teach_command(self, message: str) -> Tuple[str, str, str]:
        """
        Parse a teach command to extract fact_key and fact_value
        """
        message_lower = message.lower().strip()

        # Remove trigger words
        for trigger in ["teach", "remember", "learn", "store", "fact", "that", ":"]:
            message_lower = message_lower.replace(trigger, "", 1)

        message_lower = message_lower.strip()

        # Try to parse "key: value" or "key is value" or "key = value"
        if ":" in message_lower:
            parts = message_lower.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip()
        elif " is " in message_lower:
            parts = message_lower.split(" is ", 1)
            key = parts[0].strip()
            value = parts[1].strip()
        elif " = " in message_lower:
            parts = message_lower.split(" = ", 1)
            key = parts[0].strip()
            value = parts[1].strip()
        else:
            # Try to split on first space
            words = message_lower.split(None, 1)
            if len(words) >= 2:
                key = words[0]
                value = words[1]
            else:
                # Can't parse
                return "", "", "general"

        # Clean up "my" prefix
        key = key.replace("my ", "")

        # Determine category based on keywords
        category = "general"
        if any(word in key for word in ["model", "ai", "llm"]):
            category = "preferences"
        elif any(word in key for word in ["service", "cluster", "deployment"]):
            category = "cluster"
        elif any(word in key for word in ["memory", "cpu", "ram"]):
            category = "resources"

        return key, value, category

    def parse_recall_command(self, message: str) -> str:
        """
        Parse a recall command to extract the fact_key
        """
        message_lower = message.lower().strip()

        # Remove trigger phrases
        for trigger in ["what did i tell you about", "what do you know about",
                       "recall", "what is my", "do you remember", "my"]:
            message_lower = message_lower.replace(trigger, "", 1)

        # Remove question marks
        message_lower = message_lower.replace("?", "")

        return message_lower.strip()

    def should_query_cluster(self, intent: str) -> bool:
        """
        Determine if we need to query the cluster for this intent
        """
        # These intents require fresh cluster data
        cluster_intents = ["status", "control", "troubleshoot", "resources", "advice", "follow_up"]
        return intent in cluster_intents


# Singleton instance
_router_instance = None

def get_kilo_router() -> KiloRouter:
    """Get the global router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = KiloRouter()
    return _router_instance