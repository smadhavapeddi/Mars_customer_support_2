"""
DigitalOcean Serverless Inference Endpoint Wrapper
Handles API calls to the Serverless Inference service with caching and error handling
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
import requests
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

class ServerlessInferenceClient:
    """
    Wrapper for DigitalOcean Serverless Inference Endpoint
    Supports Claude and other models through the DO Inference API
    """

    def __init__(self):
        """Initialize the Serverless Inference client."""
        self.base_url = os.getenv(
            "SERVERLESS_INFERENCE_URL",
            "https://inference.do-ai.run"
        )
        self.api_key = os.getenv("MODEL_ACCESS_KEY")
        self.model = os.getenv("INFERENCE_MODEL", "claude-3-5-sonnet-20241022")
        self.timeout = int(os.getenv("INFERENCE_TIMEOUT", "30"))
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour

        if not self.api_key:
            logger.warning("MODEL_ACCESS_KEY not set. Serverless Inference will not work.")

    def _get_cache_key(self, prompt: str) -> str:
        """Generate a cache key from the prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _is_cached(self, cache_key: str) -> bool:
        """Check if a cached response is still valid."""
        if cache_key not in self.cache:
            return False

        cached = self.cache[cache_key]
        if datetime.now() > cached['expires']:
            del self.cache[cache_key]
            return False

        return True

    def classify_message(self, message: str) -> Dict[str, Any]:
        """
        Classify a customer message for ticket triage.
        Returns: category, priority, sentiment, requires_escalation
        """
        prompt = f"""Analyze this customer support message and provide classification in JSON format.

Message: {message}

Respond ONLY with valid JSON in this exact format, no other text:
{{
    "category": "billing|technical|account|feature_request|other",
    "priority": "low|medium|high|critical",
    "sentiment": "positive|neutral|negative",
    "requires_escalation": true|false,
    "keywords": ["keyword1", "keyword2"]
}}"""

        try:
            # Check cache first
            cache_key = self._get_cache_key(prompt)
            if self._is_cached(cache_key):
                logger.debug("Returning cached classification")
                return self.cache[cache_key]['data']

            response = self.call_inference(prompt)

            # Parse JSON response
            try:
                classification = json.loads(response)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse classification response: {response}")
                classification = {
                    "category": "other",
                    "priority": "medium",
                    "sentiment": "neutral",
                    "requires_escalation": False,
                    "keywords": []
                }

            # Cache the result
            self.cache[cache_key] = {
                'data': classification,
                'expires': datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            return classification

        except Exception as e:
            logger.error(f"Error classifying message: {str(e)}")
            return {
                "category": "other",
                "priority": "medium",
                "sentiment": "neutral",
                "requires_escalation": False,
                "keywords": []
            }

    def generate_response(self, message: str, context: List[Dict],
                         faq_results: List[Dict]) -> str:
        """
        Generate an agent response using context and FAQ data.
        """
        faq_context = ""
        if faq_results:
            faq_context = "Relevant FAQ entries:\n"
            for faq in faq_results[:3]:  # Use top 3 results
                faq_context += f"- Q: {faq.get('question', '')}\n"
                faq_context += f"  A: {faq.get('answer', '')}\n\n"

        # Build conversation context
        context_str = ""
        for msg in context[-5:]:  # Use last 5 messages for context
            role = "Customer" if msg.get('role') == 'customer' else "Support Agent"
            context_str += f"{role}: {msg.get('message', '')}\n"

        prompt = f"""You are a helpful customer support agent for DigitalOcean.

{faq_context}

Previous conversation:
{context_str}

Current customer message: {message}

Provide a helpful, concise response (2-3 sentences). Be professional and empathetic.
If the issue needs a ticket, suggest creating one."""

        try:
            response = self.call_inference(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Let me escalate this to our team."

    def generate_faq_answer(self, question: str, faq_text: str) -> str:
        """
        Generate a contextual FAQ response for a customer question.
        """
        prompt = f"""Based on this FAQ information, provide a helpful answer to the customer's question.

FAQ Information:
{faq_text}

Customer Question: {question}

Provide a clear, helpful response that directly answers their question."""

        try:
            return self.call_inference(prompt)
        except Exception as e:
            logger.error(f"Error generating FAQ answer: {str(e)}")
            return "I can help with that. Let me connect you with our specialist."

    def summarize_conversation(self, messages: List[Dict]) -> str:
        """
        Generate a summary of a conversation for human handoff.
        """
        conversation = "\n".join([
            f"{msg.get('role', 'Unknown').title()}: {msg.get('message', '')}"
            for msg in messages
        ])

        prompt = f"""Please provide a brief summary (2-3 sentences) of this customer support conversation:

{conversation}

Summary:"""

        try:
            return self.call_inference(prompt)
        except Exception as e:
            logger.error(f"Error summarizing conversation: {str(e)}")
            return "Unable to generate summary."

    def call_inference(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Make a call to the DigitalOcean Serverless Inference Endpoint.
        """
        if not self.api_key:
            raise ValueError("MODEL_ACCESS_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            logger.debug(f"Calling Serverless Inference: {self.base_url}/v1/chat/completions")

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Inference API error {response.status_code}: {response.text}")
                raise Exception(f"API returned status {response.status_code}")

            data = response.json()

            # Extract the response text
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            else:
                raise ValueError("Unexpected response format from inference API")

        except requests.Timeout:
            logger.error("Serverless Inference request timed out")
            raise Exception("Request timed out")
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling Serverless Inference: {str(e)}")
            raise

    def health_check(self) -> bool:
        """
        Check if the Serverless Inference service is available.
        """
        try:
            # Try a simple classification to verify connectivity
            result = self.classify_message("Hello")
            return bool(result)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def clear_cache(self):
        """Clear the response cache."""
        self.cache.clear()
        logger.info("Cache cleared")


# Singleton instance
_client = None

def get_inference_client() -> ServerlessInferenceClient:
    """Get or create the singleton inference client."""
    global _client
    if _client is None:
        _client = ServerlessInferenceClient()
    return _client
