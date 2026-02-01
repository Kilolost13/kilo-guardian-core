import time
import logging
import os

logger = logging.getLogger(__name__)

class CircuitBreakerException(Exception):
    """Exception raised when the circuit breaker trips."""
    pass

class CircuitBreaker:
    """
    A safety mechanism to prevent hardware crashes (Beelink power failure) 
    by rejecting heavy loads and enforcing cool-down periods.
    """
    
    def __init__(self):
        # Safety Thresholds
        self.MAX_PROMPT_CHARS = 4000  # Increased for tool-augmented prompts (RAG with tools needs more space)
        self.COOLDOWN_SECONDS = 5.0   # Time to let VRMs/CPU cool down between requests
        
        self.last_request_time = 0
        self.enabled = os.environ.get("ENABLE_CIRCUIT_BREAKER", "true").lower() == "true"

    def check_and_reset(self, prompt_text: str):
        """
        Checks if the request is safe to proceed.
        If safe, updates the last_request_time and allows execution.
        If unsafe, raises CircuitBreakerException.
        """
        if not self.enabled:
            return

        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 1. Check Cooldown (Thermal Recovery)
        if time_since_last < self.COOLDOWN_SECONDS:
            wait_time = self.COOLDOWN_SECONDS - time_since_last
            msg = f"❄️ Circuit Breaker: System cooling down. Please wait {wait_time:.1f}s."
            logger.warning(msg)
            raise CircuitBreakerException(msg)

        # 2. Check Prompt Complexity (Input Length)
        # Long prompts cause sustained CPU load -> Voltage droop -> Crash
        if len(prompt_text) > self.MAX_PROMPT_CHARS:
            msg = (f"⚡ Circuit Breaker: Prompt too long ({len(prompt_text)} chars). "
                   f"Limit is {self.MAX_PROMPT_CHARS} to prevent system crash.")
            logger.warning(msg)
            raise CircuitBreakerException(msg)
            
        # 3. Double-Step / "Chain" Detection (Simple Heuristic)
        # If the prompt looks like a complex multi-part instruction which might run long
        # This is a heuristic based on the user's report of "two step" prompts crashing it.
        # We look for indicators of complex reasoning that might cause the model to generate 
        # for a long time (output token generation is also power intensive).
        complex_markers = ["step by step", "explain in detail", "comprehensive", "break down"]
        if any(marker in prompt_text.lower() for marker in complex_markers):
            # We enforce a stricter length limit for complex prompts
            STRICT_LIMIT = 800
            if len(prompt_text) > STRICT_LIMIT:
                 msg = (f"⚡ Circuit Breaker: Complex prompt detected and exceeds strict safety limit "
                        f"({len(prompt_text)} > {STRICT_LIMIT}). Simplify request.")
                 logger.warning(msg)
                 raise CircuitBreakerException(msg)

        # If we passed all checks, update the timestamp and allow
        self.last_request_time = current_time
        logger.info("Circuit Breaker: Request allowed.")

# Global instance
breaker = CircuitBreaker()
