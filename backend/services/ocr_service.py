"""
OCR Service - работа с DeepSeek-OCR через vLLM.
"""

import httpx
import base64
import time
from pathlib import Path
from typing import Optional
from backend.config import get_settings
from backend.prompts import OCR_SYSTEM_PROMPT, OCR_USER_PROMPT

settings = get_settings()


class OCRService:
    """Service for OCR processing using DeepSeek-OCR via vLLM."""

    def __init__(self):
        self.base_url = settings.vllm_ocr_url
        self.timeout = settings.ocr_timeout

    async def check_health(self) -> dict:
        """Check if DeepSeek-OCR model is available."""
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

    def _encode_image(self, file_path: str) -> str:
        """Encode image to base64."""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type from file extension."""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "image/png")

    async def process_image(self, file_path: str) -> dict:
        """
        Process an image with DeepSeek-OCR.

        Args:
            file_path: Path to the image file

        Returns:
            dict with "text" and "processing_time"
        """
        start_time = time.time()

        # Encode image
        image_base64 = self._encode_image(file_path)
        mime_type = self._get_mime_type(file_path)

        # Build request for vLLM OpenAI-compatible API
        payload = {
            "model": "deepseek-ai/DeepSeek-OCR",
            "messages": [
                {
                    "role": "system",
                    "content": OCR_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": OCR_USER_PROMPT
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1  # Low temperature for accuracy
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

        result = response.json()
        text = result["choices"][0]["message"]["content"]
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "text": text,
            "processing_time": processing_time
        }


# Singleton instance
ocr_service = OCRService()
