import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAIService:
    """Service for interacting with Google's Gemini AI API."""

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.model = getattr(settings, 'GEMINI_MODEL_ISSUES', 'models/gemini-1.5-flash')
        # list of fallback models to try when quota is exceeded
        # these are known to work and have free tier quotas
        self.fallback_models = [
            getattr(settings, 'GEMINI_FREE_MODEL', 'models/gemini-1.5-flash'),
            'models/gemini-2.0-flash',
            'models/gemini-pro',
        ]

        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not configured. AI features will be disabled.")

    def is_available(self) -> bool:
        """Check if the AI service is available."""
        return bool(self.api_key)

    def _generate_with_fallback(self, prompt: str) -> str:
        """Attempt to generate content using the configured model.

        If a quota/rate-limit error is detected, retry with models from
        fallback_models list in order. Returns with a note when fallback is used.
        """
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            msg = str(e)
            # look for common quota-related indicators
            if 'quota' in msg.lower() or 'rate limit' in msg.lower() or '429' in msg:
                logger.warning(
                    "Primary AI model '%s' failed due to quota/rate limit. "
                    "Trying fallback models: %s",
                    self.model,
                    self.fallback_models,
                )
                # try each fallback model in order
                for fallback_model in self.fallback_models:
                    if fallback_model == self.model:
                        continue  # skip if it's the same as primary
                    try:
                        logger.info("Attempting fallback model: %s", fallback_model)
                        alt_model = genai.GenerativeModel(fallback_model)
                        response = alt_model.generate_content(prompt)
                        text = response.text.strip()
                        # annotate so callers know we switched models
                        return text + (
                            "\n\n(Note: AI quota exceeded on the primary model, "
                            "so '%s' was used instead.)" % fallback_model
                        )
                    except Exception as e2:
                        msg2 = str(e2).lower()
                        logger.warning(
                            "Fallback model '%s' failed: %s",
                            fallback_model,
                            msg2,
                        )
                        # if this is also a quota issue, try the next fallback
                        if 'quota' in msg2 or 'rate limit' in msg2 or '429' in msg2:
                            continue
                        # if it's a model not found or unsupported, try next
                        if 'not found' in msg2 or 'unsupported' in msg2 or '404' in msg2:
                            continue
                        # any other error, stop and raise
                        break
                # all fallbacks tried and failed
                logger.exception("All fallback models failed")
                raise
            # not a quota issue; re-raise
            raise

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment and frustration in text.

        Returns:
            {
                'sentiment': 'positive'|'neutral'|'frustrated'|'angry',
                'frustration_score': int (0-10),
                'needs_escalation': bool,
                'reason': str
            }
        """
        if not self.is_available():
            return {
                'sentiment': 'neutral',
                'frustration_score': 0,
                'needs_escalation': False,
                'reason': 'AI service unavailable'
            }

        try:
            prompt = f"""Analyze this text from a student reporting a campus issue. Return JSON only:

{text}

Return format:
{{
    "sentiment": "positive"|"neutral"|"frustrated"|"angry",
    "frustrationScore": number (0-10),
    "needsEscalation": boolean,
    "reason": "brief explanation"
}}

Flag for escalation if frustrationScore >= 7."""

            # try primary model and fall back to a free-tier model if quota is hit
            response_text = self._generate_with_fallback(prompt)
            result_text = response_text.strip()
            # Remove markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)

            # Validate and normalize the response
            sentiment = result.get('sentiment', 'neutral')
            if sentiment not in ['positive', 'neutral', 'frustrated', 'angry']:
                sentiment = 'neutral'

            frustration_score = min(max(int(result.get('frustrationScore', 0)), 0), 10)
            needs_escalation = result.get('needsEscalation', False) or frustration_score >= 7
            reason = result.get('reason', '')

            return {
                'sentiment': sentiment,
                'frustration_score': frustration_score,
                'needs_escalation': needs_escalation,
                'reason': reason
            }

        except Exception as e:
            logger.exception(f"Error analyzing sentiment for text: {text[:100]}...")
            return {
                'sentiment': 'neutral',
                'frustration_score': 0,
                'needs_escalation': False,
                'reason': f'Analysis failed: {str(e)}'
            }

    def generate_chatbot_response(self, conversation_history: list, user_message: str) -> str:
        """
        Generate a response for the complaint assistant chatbot.

        Args:
            conversation_history: List of previous messages (last 10)
            user_message: Current user message

        Returns:
            AI response or empty string if unavailable
        """
        if not self.is_available():
            return "I'm sorry, the AI assistant is currently unavailable. Please fill out the form manually."

        try:
            # Build conversation context
            context = "\n".join([
                f"{'User' if i % 2 == 0 else 'Assistant'}: {msg}"
                for i, msg in enumerate(conversation_history[-10:])  # Last 10 messages
            ])

            prompt = f"""You are CampusFix Assistant, a friendly helper for university students reporting campus maintenance issues.

Previous conversation:
{context}

Current user message: {user_message}

Instructions:
- Ask clear, simple questions one at a time
- Extract: location, issue type, description, and urgency
- Once you have all info, output a JSON summary for form filling
- Be friendly and helpful

If you have enough information, respond with JSON in this format:
{{"complete": true, "location": "...", "category": "...", "description": "...", "urgency": "low|medium|high|critical"}}

Otherwise, ask one question at a time."""

            result_text = self._generate_with_fallback(prompt)

            # Check if it's a JSON completion response
            try:
                if result_text.startswith('{') and result_text.endswith('}'):
                    json_data = json.loads(result_text)
                    if json_data.get('complete'):
                        return json.dumps(json_data)  # Return JSON for form filling
            except json.JSONDecodeError:
                pass

            # Return as regular chat response
            return result_text

        except Exception as e:
            logger.exception(f"Error generating chatbot response for user message: {user_message}")
            return "I apologize, but I'm having trouble responding right now. Please continue filling out the form manually."

    def generate_admin_response_draft(self, issue_data: Dict[str, Any]) -> str:
        """
        Generate a draft response for admin to use when replying to issues.

        Args:
            issue_data: Dict with issue details

        Returns:
            Draft response text
        """
        if not self.is_available():
            return "AI draft unavailable - please write your response manually."

        try:
            prompt = f"""You are a university facilities admin. Draft a professional, empathetic response to a student's campus issue report.

Issue Details:
- Title: {issue_data.get('title', '')}
- Category: {issue_data.get('category', '')}
- Status: {issue_data.get('status', '')}
- Description: {issue_data.get('description', '')}

Write 2-3 sentences. Be clear about next steps."""

            # generate text with fallback in case of quota errors
            return self._generate_with_fallback(prompt)

        except Exception as e:
            logger.exception(f"Error generating admin response draft for issue: {issue_data.get('title')}")
            return f"AI draft unavailable due to an error: {str(e)}. Please write your response manually."

    def generate_monthly_report(self, stats: Dict[str, Any]) -> str:
        """
        Generate a monthly performance report based on statistics.

        Args:
            stats: Dictionary of statistics

        Returns:
            Formatted report text
        """
        if not self.is_available():
            return "AI report generation unavailable."

        try:
            stats_json = json.dumps(stats, indent=2)
            current_month_year = timezone.now().strftime("%B %Y")

            prompt = f"""You are a facilities management analyst. Write a concise monthly performance report for a university campus maintenance system based on these statistics:

{stats_json}

The report is for the period: {current_month_year}.
Please ensure the title of your report explicitly includes this period instead of "[Insert Month/Year]".

Include:
- Overall summary
- Key wins
- Areas of concern
- 2-3 actionable recommendations

Use clear headings and be professional."""

            # if quota exceeded on primary model, retry with free-tier fallback
            return self._generate_with_fallback(prompt)

        except Exception as e:
            logger.exception("Error generating monthly report")
            return f"AI report generation failed: {str(e)}. Please try again later or contact support."


# Global instance
ai_service = GeminiAIService()