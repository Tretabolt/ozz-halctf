"""
Ozz — LLM Interface
Connects to local vLLM server or llama.cpp server.
"""

import logging
import json
import os
import requests
from typing import Optional

logger = logging.getLogger("ozz.llm")

# Default model - Qwen 2.5 Coder 7B
DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"


class LLM:
    """Local LLM interface using vLLM OpenAI-compatible API."""

    def __init__(self, model_path: str = "/models", port: int = 8000):
        self.model_path = model_path
        self.port = port
        self.api_url = f"http://localhost:{port}/v1"
        self.model_name = os.environ.get("MODEL_NAME", DEFAULT_MODEL)
        self.max_tokens = int(os.environ.get("MAX_TOKENS", "4096"))
        self.temperature = float(os.environ.get("TEMPERATURE", "0.3"))
        self._verify_connection()

    def _verify_connection(self):
        """Verify the LLM server is running."""
        try:
            resp = requests.get(f"{self.api_url}/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    self.model_name = models[0].get("id", self.model_name)
                    logger.info(f"✅ LLM server connected. Model: {self.model_name}")
                else:
                    logger.warning("LLM server running but no models loaded")
            else:
                logger.warning(f"LLM server returned status {resp.status_code}")
        except requests.ConnectionError:
            logger.error(f"❌ Cannot connect to LLM server at {self.api_url}")
            logger.info("Make sure vLLM is running: python -m vllm.entrypoints.openai.api_server")
            raise

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from the LLM."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                f"{self.api_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stop": ["```", "---"],
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return ""

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Optional[dict]:
        """Generate and parse JSON response."""
        response = self.generate(prompt, system)
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}")
            return None
