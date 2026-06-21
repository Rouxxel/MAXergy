"""
Gemini LLM service for AI advisor integration.

This service provides a clean interface for interacting with Google's Gemini API
to generate AI-powered advice on energy efficiency upgrades.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from src.utils.custom_logger import log_handler


@dataclass
class AdvisorResponse:
    """Response from the AI advisor."""
    advisor_message: str
    context_used: List[str]
    suggestions: List[str]


class GeminiService:
    """Service for interacting with Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        self._initialized = False
        
        # Security: Validate API key format and don't log the actual key
        if self.api_key and self.api_key != "key_here":
            if not self._validate_api_key(self.api_key):
                log_handler.warning("[gemini_service] Invalid GEMINI_API_KEY format, service will not be initialized")
                self.api_key = None
            else:
                self._initialize()
    
    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate the API key format.
        
        Args:
            api_key: The API key to validate.
        
        Returns:
            True if valid, False otherwise.
        """
        # Gemini API keys typically start with specific prefixes
        # This is a basic validation, actual validation happens during API call
        if not api_key or len(api_key) < 20:
            return False
        return True
    
    def _initialize(self):
        """Initialize the Gemini client."""
        if not GEMINI_AVAILABLE:
            log_handler.warning("[gemini_service] google-generativeai package not installed, using mock responses")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-3.5-flash')
            self._initialized = True
            log_handler.info("[gemini_service] Gemini service initialized successfully")
        except Exception as e:
            log_handler.error("[gemini_service] Failed to initialize Gemini service: %s", str(e))
    
    def is_available(self) -> bool:
        """Check if the Gemini service is available."""
        return self._initialized
    
    def generate_advice(
        self,
        user_message: str,
        forecast_result: Optional[Dict] = None,
        assessment_id: Optional[str] = None,
    ) -> AdvisorResponse:
        """
        Generate AI advice based on user message and forecast context.
        
        Args:
            user_message: User's question or message.
            forecast_result: Optional forecast result data for context.
            assessment_id: Optional assessment ID for logging.
        
        Returns:
            AdvisorResponse with message, context used, and suggestions.
        """
        if not self.is_available():
            log_handler.warning("[gemini_service] Gemini service not available, using mock response")
            return self._generate_mock_response(user_message, forecast_result)
        
        try:
            context_used = ["user_question"]
            if forecast_result:
                context_used.append("forecast_result")
            
            prompt = self._build_prompt(user_message, forecast_result)
            
            response = self.model.generate_content(prompt)
            advisor_message = response.text
            
            suggestions = self._extract_suggestions(advisor_message)
            
            log_handler.info("[gemini_service] Generated advice for assessment %s", assessment_id)
            
            return AdvisorResponse(
                advisor_message=advisor_message,
                context_used=context_used,
                suggestions=suggestions,
            )
        except Exception as e:
            log_handler.error("[gemini_service] Failed to generate advice: %s", str(e))
            return self._generate_mock_response(user_message, forecast_result)
    
    def _build_prompt(self, user_message: str, forecast_result: Optional[Dict]) -> str:
        """
        Build the prompt for the Gemini API.
        
        Args:
            user_message: User's question or message.
            forecast_result: Optional forecast result data for context.
        
        Returns:
            Formatted prompt string.
        """
        base_prompt = """You are MAXergy, an AI advisor specializing in home energy efficiency upgrades. 
You provide helpful, accurate advice about solar PV, battery storage, heat pumps, EV charging and financing options.

Your responses should be:
- Concise and practical, be pragmatic and make yourself clear and easy to understand.
- Focused on market conditions (subsidies, tariffs, regulations), particularly on the german market.
- Based on typical system performance data.
- Include specific, actionable suggestions.

Format your response as a clear message followed by 2-3 bullet point suggestions.
"""
        
        if forecast_result:
            context_prompt = self._build_forecast_context(forecast_result)
            return f"{base_prompt}\n\n{context_prompt}\n\nUser question: {user_message}"
        
        return f"{base_prompt}\n\nUser question: {user_message}"
    
    def _build_forecast_context(self, forecast_result: Dict) -> str:
        """
        Build context string from forecast result.
        
        Args:
            forecast_result: Forecast result data.
        
        Returns:
            Formatted context string.
        """
        context_parts = ["User's household assessment context:"]
        
        if "baseline" in forecast_result:
            baseline = forecast_result["baseline"]
            if "monthly_cost_eur" in baseline:
                costs = baseline["monthly_cost_eur"]
                context_parts.append(
                    f"- Current monthly costs: Electricity €{costs.get('electricity', 0):.2f}, "
                    f"Heating €{costs.get('gas_oil', 0):.2f}, Mobility €{costs.get('fuel', 0):.2f}"
                )
        
        if "scenarios" in forecast_result and forecast_result["scenarios"]:
            top_scenario = forecast_result["scenarios"][0]
            context_parts.append(f"- Recommended scenario: {top_scenario.get('id', 'N/A')}")
            context_parts.append(f"- Monthly savings: €{top_scenario.get('monthly_saving_eur', 0):.2f}")
            
            if "components" in top_scenario:
                components = top_scenario["components"]
                included = [k for k, v in components.items() if v]
                context_parts.append(f"- Includes: {', '.join(included)}")
        
        return "\n".join(context_parts)
    
    def _extract_suggestions(self, advisor_message: str) -> List[str]:
        """
        Extract bullet point suggestions from the advisor message.
        
        Args:
            advisor_message: The advisor's message.
        
        Returns:
            List of suggestions.
        """
        suggestions = []
        lines = advisor_message.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                suggestion = line.lstrip("-•*").strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions
    
    def generate_recommendation_summary(self, forecast_result: Dict) -> AdvisorResponse:
        """
        Generate a summary of the recommended scenario.
        
        Args:
            forecast_result: Forecast result data.
        
        Returns:
            AdvisorResponse with recommendation summary.
        """
        if not self.is_available():
            return self._generate_mock_recommendation_summary(forecast_result)
        
        try:
            prompt = self._build_recommendation_summary_prompt(forecast_result)
            response = self.model.generate_content(prompt)
            advisor_message = response.text
            suggestions = self._extract_suggestions(advisor_message)
            
            return AdvisorResponse(
                advisor_message=advisor_message,
                context_used=["forecast_result", "recommendation"],
                suggestions=suggestions,
            )
        except Exception as e:
            log_handler.error("[gemini_service] Failed to generate recommendation summary: %s", str(e))
            return self._generate_mock_recommendation_summary(forecast_result)
    
    def generate_savings_explanation(self, forecast_result: Dict) -> AdvisorResponse:
        """
        Generate an explanation of the savings calculation.
        
        Args:
            forecast_result: Forecast result data.
        
        Returns:
            AdvisorResponse with savings explanation.
        """
        if not self.is_available():
            return self._generate_mock_savings_explanation(forecast_result)
        
        try:
            prompt = self._build_savings_explanation_prompt(forecast_result)
            response = self.model.generate_content(prompt)
            advisor_message = response.text
            suggestions = self._extract_suggestions(advisor_message)
            
            return AdvisorResponse(
                advisor_message=advisor_message,
                context_used=["forecast_result", "savings"],
                suggestions=suggestions,
            )
        except Exception as e:
            log_handler.error("[gemini_service] Failed to generate savings explanation: %s", str(e))
            return self._generate_mock_savings_explanation(forecast_result)
    
    def detect_upsell_opportunities(self, forecast_result: Dict) -> AdvisorResponse:
        """
        Detect upsell opportunities based on the forecast.
        
        Args:
            forecast_result: Forecast result data.
        
        Returns:
            AdvisorResponse with upsell opportunities.
        """
        if not self.is_available():
            return self._generate_mock_upsell_opportunities(forecast_result)
        
        try:
            prompt = self._build_upsell_opportunities_prompt(forecast_result)
            response = self.model.generate_content(prompt)
            advisor_message = response.text
            suggestions = self._extract_suggestions(advisor_message)
            
            return AdvisorResponse(
                advisor_message=advisor_message,
                context_used=["forecast_result", "upsell"],
                suggestions=suggestions,
            )
        except Exception as e:
            log_handler.error("[gemini_service] Failed to detect upsell opportunities: %s", str(e))
            return self._generate_mock_upsell_opportunities(forecast_result)
    
    def _build_recommendation_summary_prompt(self, forecast_result: Dict) -> str:
        """Build prompt for recommendation summary generation."""
        context = self._build_forecast_context(forecast_result)
        return f"""You are MAXergy, an AI energy advisor. Summarize the recommended energy upgrade scenario for this household.

{context}

Provide a concise summary (2-3 sentences) explaining why this scenario is recommended and what it includes.
Follow with 2-3 bullet point suggestions for next steps."""
    
    def _build_savings_explanation_prompt(self, forecast_result: Dict) -> str:
        """Build prompt for savings explanation generation."""
        context = self._build_forecast_context(forecast_result)
        return f"""You are MAXergy, an AI energy advisor. Explain how the monthly savings are calculated for this household.

{context}

Explain the savings calculation in simple terms (electricity reduction, self-consumption, financing costs, etc.).
Follow with 2-3 bullet point suggestions for maximizing savings."""
    
    def _build_upsell_opportunities_prompt(self, forecast_result: Dict) -> str:
        """Build prompt for upsell opportunity detection."""
        context = self._build_forecast_context(forecast_result)
        return f"""You are MAXergy, an AI energy advisor. Identify upsell opportunities or additional improvements for this household.

{context}

Identify 2-3 additional upgrades or optimizations that could provide further benefits.
Follow with bullet point suggestions for each opportunity."""
    
    def _generate_mock_recommendation_summary(self, forecast_result: Dict) -> AdvisorResponse:
        """Generate mock recommendation summary."""
        advisor_message = (
            "Based on your household profile, the recommended scenario offers the best balance of "
            "monthly savings and upfront investment. This configuration maximizes self-consumption "
            "while minimizing grid dependence."
        )
        suggestions = [
            "Review the detailed cost breakdown in the comparison view",
            "Check available subsidies for your recommended components",
            "Consider phased implementation if budget is a concern",
        ]
        return AdvisorResponse(
            advisor_message=advisor_message,
            context_used=["forecast_result", "recommendation"],
            suggestions=suggestions,
        )
    
    def _generate_mock_savings_explanation(self, forecast_result: Dict) -> AdvisorResponse:
        """Generate mock savings explanation."""
        advisor_message = (
            "Your monthly savings come from reducing grid electricity purchases through solar self-consumption, "
            "lower heating costs with efficient heat pumps, and reduced fuel expenses with EV charging. "
            "Financing costs are factored into the net savings calculation."
        )
        suggestions = [
            "Shift energy-intensive activities to daytime hours for maximum solar usage",
            "Consider time-of-use tariffs to optimize savings",
            "Monitor your actual consumption to validate forecast accuracy",
        ]
        return AdvisorResponse(
            advisor_message=advisor_message,
            context_used=["forecast_result", "savings"],
            suggestions=suggestions,
        )
    
    def _generate_mock_upsell_opportunities(self, forecast_result: Dict) -> AdvisorResponse:
        """Generate mock upsell opportunities."""
        advisor_message = (
            "Based on your current setup, consider adding smart home integration to optimize "
            "energy usage automatically. A home energy management system could further increase "
            "your self-consumption and savings."
        )
        suggestions = [
            "Explore smart home automation for energy optimization",
            "Consider adding EV charging if you plan to buy an electric vehicle",
            "Look into demand response programs for additional revenue",
        ]
        return AdvisorResponse(
            advisor_message=advisor_message,
            context_used=["forecast_result", "upsell"],
            suggestions=suggestions,
        )
    
    def _generate_mock_response(
        self,
        user_message: str,
        forecast_result: Optional[Dict] = None,
    ) -> AdvisorResponse:
        """Generate a mock advisor response for development/testing."""
        user_message_lower = user_message.lower()
        
        if "solar" in user_message_lower:
            advisor_message = (
                "Solar PV is a great starting point for energy independence. "
                "Based on typical German conditions, you can expect around 1000 kWh/kWp annual yield. "
                "Consider adding battery storage to increase self-consumption from 30% to 65%."
            )
            suggestions = [
                "Start with solar PV as the foundation",
                "Add battery storage if you have high daytime consumption",
                "Check your roof orientation and shading for optimal placement",
            ]
        elif "battery" in user_message_lower:
            advisor_message = (
                "Battery storage increases your self-consumption ratio significantly. "
                "A 7.5 kWh battery is typical for a 5-6 kWp solar system. "
                "This can reduce grid dependence and protect against rising electricity prices."
            )
            suggestions = [
                "Size battery to match your evening consumption patterns",
                "Consider smart home integration for optimal charging",
                "Batteries work best with time-of-use tariffs",
            ]
        elif "heat pump" in user_message_lower:
            advisor_message = (
                "Heat pumps are highly efficient with a COP of 3.3 or higher. "
                "They replace fossil fuel heating and can be powered by your solar PV. "
                "Consider your building's insulation level for optimal performance."
            )
            suggestions = [
                "Improve insulation before installing heat pump",
                "Combine with solar PV for maximum savings",
                "Check eligibility for BAFA subsidies",
            ]
        elif "ev" in user_message_lower or "electric vehicle" in user_message_lower:
            advisor_message = (
                "EV charging at home with solar PV can significantly reduce mobility costs. "
                "Typical BEV consumption is 18 kWh/100km. "
                "Consider off-peak charging and smart charging management."
            )
            suggestions = [
                "Install home charger for convenience",
                "Time charging with solar generation peaks",
                "Consider vehicle-to-grid technology in the future",
            ]
        elif "cost" in user_message_lower or "price" in user_message_lower:
            advisor_message = (
                "The total cost depends on the combination of upgrades. "
                "Solar PV typically costs around €1,400/kWp, batteries €700/kWh, "
                "and heat pumps around €12,000 installed. "
                "Subsidies can cover up to 30% of system costs."
            )
            suggestions = [
                "Check KfW and BAFA subsidy programs",
                "Consider green loans for favorable financing",
                "Calculate ROI based on your energy savings",
            ]
        else:
            advisor_message = (
                "I can help you with questions about solar PV, battery storage, heat pumps, "
                "EV charging, costs, and financing options. "
                "Please provide more specific details about what you'd like to know."
            )
            suggestions = [
                "Ask about specific technologies (solar, battery, heat pump, EV)",
                "Inquire about costs and financing options",
                "Request information about subsidies and incentives",
            ]
        
        context_used = ["user_question"]
        if forecast_result:
            context_used.append("forecast_result")
        
        return AdvisorResponse(
            advisor_message=advisor_message,
            context_used=context_used,
            suggestions=suggestions,
        )


# Singleton instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get the singleton Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
