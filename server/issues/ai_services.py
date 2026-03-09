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

        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not configured. AI features will be disabled.")

    def is_available(self) -> bool:
        """Check if the AI service is available."""
        return bool(self.api_key)

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

            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            # Parse the JSON response
            result_text = response.text.strip()
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
            logger.error(f"Error analyzing sentiment: {e}")
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

            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            result_text = response.text.strip()

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
            logger.error(f"Error generating chatbot response: {e}")
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

            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating admin response draft: {e}")
            return "AI draft unavailable - please write your response manually."

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

            prompt = f"""You are a facilities management analyst. Write a concise monthly performance report for a university campus maintenance system based on these statistics:

{stats_json}

Include:
- Overall summary
- Key wins
- Areas of concern
- 2-3 actionable recommendations

Use clear headings and be professional."""

            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            return "AI report generation failed."


# Global instance
ai_service = GeminiAIService()