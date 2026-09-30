"""
DigitalOcean Serverless Inference Client
Wrapper for OpenAI-compatible API with model routing, fallback, and usage tracking
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import requests
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class InferenceUsage:
    """Track inference API usage and costs."""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: str
    request_id: Optional[str] = None

class DigitalOceanInferenceClient:
    """
    DigitalOcean Serverless Inference Client
    OpenAI-compatible API wrapper with advanced features
    """

    # DigitalOcean Serverless Inference endpoint
    BASE_URL = "https://inference.do-ai.run/v1"

    # Model pricing (in USD per 1M tokens)
    # Update these based on current DO pricing
    MODEL_PRICING = {
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "llama-3-70b": {"input": 0.50, "output": 0.50},
        "llama-3-8b": {"input": 0.10, "output": 0.10},
    }

    def __init__(self, api_key: Optional[str] = None, primary_model: str = "claude-3-5-sonnet"):
        """Initialize the DO Inference client."""
        self.api_key = api_key or os.getenv("DO_INFERENCE_KEY")
        if not self.api_key:
            raise ValueError("DO_INFERENCE_KEY environment variable not set")

        self.primary_model = primary_model
        self.fallback_models = self._get_fallback_models(primary_model)
        self.usage_history: List[InferenceUsage] = []
        self.session_id = None

    def _get_fallback_models(self, model: str) -> List[str]:
        """Get fallback models if primary fails."""
        fallback_map = {
            "claude-3-5-sonnet": ["claude-3-5-haiku", "gpt-4o-mini"],
            "claude-3-5-haiku": ["gpt-4o-mini"],
            "gpt-4o": ["gpt-4o-mini", "claude-3-5-sonnet"],
            "gpt-4o-mini": ["llama-3-8b"],
            "llama-3-70b": ["llama-3-8b", "gpt-4o-mini"],
        }
        return fallback_map.get(model, [])

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False,
        retry_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to DO Serverless Inference.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to primary_model)
            max_tokens: Max tokens in response
            temperature: Sampling temperature
            stream: Enable response streaming
            retry_fallback: Try fallback models on failure

        Returns:
            Response dict with content, usage, model used
        """
        model = model or self.primary_model

        try:
            return self._make_request(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
        except Exception as e:
            logger.error(f"Request failed with {model}: {str(e)}")

            if retry_fallback and self.fallback_models:
                logger.info(f"Attempting fallback models: {self.fallback_models}")
                for fallback_model in self.fallback_models:
                    try:
                        return self._make_request(
                            model=fallback_model,
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            stream=stream
                        )
                    except Exception as fallback_error:
                        logger.warning(f"Fallback {fallback_model} failed: {str(fallback_error)}")
                        continue

            raise Exception(f"All models failed. Last error: {str(e)}")

    def _make_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make actual API request to DO Serverless Inference."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        response = requests.post(
            f"{self.BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        data = response.json()

        # Track usage
        if "usage" in data:
            usage = InferenceUsage(
                model=model,
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
                cost_usd=self._calculate_cost(model, data["usage"]),
                timestamp=datetime.now().isoformat(),
                request_id=data.get("id")
            )
            self.usage_history.append(usage)

        return {
            "content": data["choices"][0]["message"]["content"],
            "model": model,
            "usage": data.get("usage"),
            "cost": self._calculate_cost(model, data.get("usage", {})),
            "request_id": data.get("id")
        }

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate cost of API call."""
        if model not in self.MODEL_PRICING:
            return 0.0

        pricing = self.MODEL_PRICING[model]
        input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * pricing["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of API usage."""
        if not self.usage_history:
            return {"total_requests": 0, "total_cost": 0, "models_used": []}

        total_cost = sum(u.cost_usd for u in self.usage_history)
        total_tokens = sum(u.total_tokens for u in self.usage_history)
        models_used = list(set(u.model for u in self.usage_history))

        return {
            "total_requests": len(self.usage_history),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "models_used": models_used,
            "average_cost_per_request": round(total_cost / len(self.usage_history), 6) if self.usage_history else 0,
            "usage_by_model": self._get_usage_by_model()
        }

    def _get_usage_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Break down usage by model."""
        by_model = {}

        for usage in self.usage_history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }

            by_model[usage.model]["requests"] += 1
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["cost"] += usage.cost_usd

        return by_model

    def export_usage_logs(self, filepath: str):
        """Export detailed usage logs to JSON."""
        logs = [asdict(u) for u in self.usage_history]

        with open(filepath, 'w') as f:
            json.dump({
                "summary": self.get_usage_summary(),
                "detailed_logs": logs,
                "exported_at": datetime.now().isoformat()
            }, f, indent=2)

        logger.info(f"Usage logs exported to {filepath}")

    def set_session_id(self, session_id: str):
        """Set session ID for tracking."""
        self.session_id = session_id

    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """
        Stream chat completion responses.

        Yields chunks of the response as they arrive.
        """
        model = model or self.primary_model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        with requests.post(
            f"{self.BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=60
        ) as response:

            if response.status_code != 200:
                raise Exception(f"API Error {response.status_code}: {response.text}")

            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data != "[DONE]":
                            try:
                                chunk = json.loads(data)
                                yield chunk["choices"][0]["delta"].get("content", "")
                            except json.JSONDecodeError:
                                pass


class InferenceModelRegistry:
    """Registry of available models on DigitalOcean Serverless Inference."""

    MODELS = {
        "claude-3-5-sonnet": {
            "provider": "Anthropic",
            "type": "text",
            "context_window": 200000,
            "description": "Latest Claude model - excellent for reasoning and complex tasks"
        },
        "claude-3-5-haiku": {
            "provider": "Anthropic",
            "type": "text",
            "context_window": 200000,
            "description": "Fast Claude model - good for speed-critical applications"
        },
        "gpt-4o": {
            "provider": "OpenAI",
            "type": "text",
            "context_window": 128000,
            "description": "Latest GPT-4 model - strong across all tasks"
        },
        "gpt-4o-mini": {
            "provider": "OpenAI",
            "type": "text",
            "context_window": 128000,
            "description": "Lightweight GPT-4 - fast and cost-effective"
        },
        "llama-3-70b": {
            "provider": "Meta",
            "type": "text",
            "context_window": 8192,
            "description": "Large open-source model - good for general tasks"
        },
        "llama-3-8b": {
            "provider": "Meta",
            "type": "text",
            "context_window": 8192,
            "description": "Small open-source model - lightweight and fast"
        },
    }

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a model."""
        return cls.MODELS.get(model_name)

    @classmethod
    def list_models(cls) -> List[str]:
        """List all available models."""
        return list(cls.MODELS.keys())

    @classmethod
    def get_recommended_model(cls, use_case: str) -> str:
        """Get recommended model for use case."""
        recommendations = {
            "customer_support": "claude-3-5-sonnet",
            "fast_responses": "claude-3-5-haiku",
            "high_accuracy": "gpt-4o",
            "cost_effective": "gpt-4o-mini",
            "open_source": "llama-3-70b",
            "lightweight": "llama-3-8b",
        }
        return recommendations.get(use_case, "claude-3-5-sonnet")
