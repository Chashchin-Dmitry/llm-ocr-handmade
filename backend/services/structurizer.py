"""
Structurizer Service - работа с Qwen для структуризации данных.
"""

import httpx
import json
import time
import re
from typing import Optional
from backend.config import get_settings
from backend.prompts import STRUCTURING_SYSTEM_PROMPT, build_structuring_prompt

settings = get_settings()


class StructurizerService:
    """Service for data structuring using Qwen via vLLM."""

    def __init__(self):
        self.base_url = settings.vllm_qwen_url
        self.timeout = settings.structurizer_timeout

    async def check_health(self) -> dict:
        """Check if Qwen model is available."""
        try:
            start = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=10
                )
                response_time = int((time.time() - start) * 1000)

                if response.status_code == 200:
                    return {
                        "status": "online",
                        "response_time": response_time
                    }
                return {"status": "error", "response_time": response_time}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from model response."""
        # Try to find JSON in response
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try to parse entire response as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Return error if no valid JSON found
        return {"_error": "Failed to parse JSON", "_raw": text}

    async def structure_data(self, ocr_text: str, columns: list[dict]) -> dict:
        """
        Structure OCR text into JSON based on column definitions.

        Args:
            ocr_text: Raw text from OCR
            columns: List of {"name": "...", "description": "..."} dicts

        Returns:
            dict with "data", "confidence", and "processing_time"
        """
        start_time = time.time()

        # Build prompt with column descriptions
        user_prompt = build_structuring_prompt(columns, ocr_text)

        # Build request for vLLM OpenAI-compatible API
        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": STRUCTURING_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.1  # Low temperature for consistency
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

        result = response.json()
        raw_content = result["choices"][0]["message"]["content"]

        # Extract JSON from response
        data = self._extract_json(raw_content)

        processing_time = int((time.time() - start_time) * 1000)

        # Calculate simple confidence based on filled fields
        filled_fields = sum(1 for v in data.values() if v is not None and v != "" and not str(v).startswith("_"))
        total_fields = len(columns)
        confidence = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0

        return {
            "data": data,
            "confidence": confidence,
            "processing_time": processing_time
        }


# Singleton instance
structurizer_service = StructurizerService()
