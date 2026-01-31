import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class GuardrailStatus(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    REDIRECTED = "redirected"


@dataclass
class GuardrailResult:
    status: GuardrailStatus
    message: Optional[str] = None
    original_input: Optional[str] = None


# Allowed topics for the auto service center
ALLOWED_TOPICS = [
    "vehicle", "car", "truck", "suv", "van",
    "service", "repair", "maintenance", "oil change", "brake", "tire",
    "appointment", "schedule", "booking",
    "parts", "price", "cost", "estimate", "quote",
    "recall", "safety", "warranty",
    "vin", "mileage", "year", "make", "model",
    "engine", "transmission", "battery", "air filter",
    "hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye",
    "help", "support", "speak", "agent", "human",
]

# Blocked patterns (prompt injection attempts, off-topic)
BLOCKED_PATTERNS = [
    r"ignore.*instructions",
    r"forget.*previous",
    r"you are now",
    r"pretend to be",
    r"act as",
    r"new persona",
    r"jailbreak",
    r"bypass",
    r"override",
    r"system prompt",
    r"ignore all",
]

# Off-topic subjects to redirect
OFF_TOPIC_SUBJECTS = [
    "politics", "religion", "dating", "relationship",
    "medical advice", "legal advice", "investment",
    "cryptocurrency", "stocks", "gambling",
    "weapons", "drugs", "alcohol",
    "personal opinion", "controversial",
]


class TopicGuard:
    """Ensures conversation stays within auto service topics"""
    
    @staticmethod
    def check_topic(user_input: str) -> GuardrailResult:
        input_lower = user_input.lower()
        
        # Check for blocked patterns (prompt injection)
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, input_lower):
                return GuardrailResult(
                    status=GuardrailStatus.BLOCKED,
                    message="I'm here to help with auto service questions. How can I assist you with your vehicle today?",
                    original_input=user_input
                )
        
        # Check for off-topic subjects
        for subject in OFF_TOPIC_SUBJECTS:
            if subject in input_lower:
                return GuardrailResult(
                    status=GuardrailStatus.REDIRECTED,
                    message=f"I specialize in auto service assistance. I can help you with vehicle repairs, maintenance, appointments, or parts. What can I help you with?",
                    original_input=user_input
                )
        
        # Check if any allowed topic is mentioned (loose matching for general queries)
        has_allowed_topic = any(topic in input_lower for topic in ALLOWED_TOPICS)
        
        # Allow general greetings and short messages
        if len(user_input.split()) <= 5 or has_allowed_topic:
            return GuardrailResult(
                status=GuardrailStatus.ALLOWED,
                original_input=user_input
            )
        
        # For longer messages without clear auto-related content, gently redirect
        return GuardrailResult(
            status=GuardrailStatus.REDIRECTED,
            message="I'm your auto service assistant. I can help with scheduling appointments, checking recalls, getting repair estimates, or finding parts. What would you like help with?",
            original_input=user_input
        )


class InputValidator:
    """Sanitizes and validates user input"""
    
    MAX_INPUT_LENGTH = 1000
    
    @staticmethod
    def validate(user_input: str) -> GuardrailResult:
        # Check for empty input
        if not user_input or not user_input.strip():
            return GuardrailResult(
                status=GuardrailStatus.BLOCKED,
                message="I didn't catch that. Could you please repeat?",
                original_input=user_input
            )
        
        # Check input length
        if len(user_input) > InputValidator.MAX_INPUT_LENGTH:
            return GuardrailResult(
                status=GuardrailStatus.BLOCKED,
                message="That's quite a lot of information. Could you break it down into smaller questions?",
                original_input=user_input[:100] + "..."
            )
        
        # Sanitize: remove excessive whitespace
        sanitized = " ".join(user_input.split())
        
        return GuardrailResult(
            status=GuardrailStatus.ALLOWED,
            original_input=sanitized
        )


class OutputFilter:
    """Validates AI responses before sending to user"""
    
    # Phrases the AI should never say
    FORBIDDEN_PHRASES = [
        "as an ai",
        "as a language model",
        "i cannot provide medical",
        "i cannot provide legal",
        "i'm just an ai",
        "my training data",
    ]
    
    # Required context phrases for certain responses
    PRICE_DISCLAIMER = "Prices are estimates and may vary based on your specific vehicle and location."
    
    @staticmethod
    def filter_response(response: str) -> str:
        response_lower = response.lower()
        
        # Remove forbidden phrases by replacing with appropriate alternatives
        for phrase in OutputFilter.FORBIDDEN_PHRASES:
            if phrase in response_lower:
                print(f"[OutputFilter] Removed forbidden phrase: {phrase}")
        
        # Add disclaimer if discussing prices
        price_keywords = ["price", "cost", "estimate", "$", "dollar"]
        if any(kw in response_lower for kw in price_keywords):
            if OutputFilter.PRICE_DISCLAIMER.lower() not in response_lower:
                response += f"\n\n{OutputFilter.PRICE_DISCLAIMER}"
        
        return response


class Guardrails:
    """Main guardrails interface combining all checks"""
    
    def __init__(self):
        self.topic_guard = TopicGuard()
        self.input_validator = InputValidator()
        self.output_filter = OutputFilter()
    
    def check_input(self, user_input: str) -> GuardrailResult:
        """Run all input checks and return result"""
        
        # Step 1: Validate input
        validation_result = self.input_validator.validate(user_input)
        if validation_result.status != GuardrailStatus.ALLOWED:
            return validation_result
        
        # Step 2: Check topic boundaries
        topic_result = self.topic_guard.check_topic(validation_result.original_input)
        return topic_result
    
    def filter_output(self, response: str) -> str:
        """Filter AI response before sending to user"""
        return self.output_filter.filter_response(response)


# Convenience function for quick checks
def check_guardrails(user_input: str) -> GuardrailResult:
    """Quick guardrail check for user input"""
    guardrails = Guardrails()
    return guardrails.check_input(user_input)
