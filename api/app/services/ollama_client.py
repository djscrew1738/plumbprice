"""
Ollama API client for Hermes agent integration.

Provides wrappers around Ollama endpoints for:
- LLM-based classification (task code routing)
- Semantic embeddings (RAG support)
- Memory/context management
"""

import asyncio
import httpx
import structlog
from typing import Optional, Any
from enum import Enum

logger = structlog.get_logger()


class OllamaModel(str, Enum):
    """Available Ollama models for Hermes."""
    
    # Classification models (task routing)
    WHITERABBIT_V2 = "ALIENTELLIGENCE/whiterabbitv2:latest"
    GEMMA_4 = "igorls/gemma-4-E4B-it-heretic-GGUF:latest"
    ORCHESTRATOR_XAL = "orchestrator-xal:latest"
    
    # Embedding models (RAG/semantic search)
    MXBAI_EMBED_LARGE = "mxbai-embed-large:latest"
    BGE_LARGE = "bge-large:latest"
    
    # Vision models
    LLAMA_VISION = "llama3.2-vision:latest"


class OllamaClient:
    """
    Client for Ollama API.
    
    Tested configuration:
    - Server: 100.83.120.32:11434
    - Version: 0.20.4
    - 45 models available
    """
    
    def __init__(
        self,
        api_url: str = "http://100.83.120.32:11434",
        timeout: float = 120.0,
        classification_model: str = OllamaModel.WHITERABBIT_V2,
        embedding_model: str = OllamaModel.MXBAI_EMBED_LARGE,
    ):
        """Initialize Ollama client."""
        self.api_url = api_url
        self.timeout = httpx.Timeout(timeout)
        self.classification_model = classification_model
        self.embedding_model = embedding_model
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def is_healthy(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.api_url}/api/version",
                timeout=5.0
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("ollama.health_check_failed", error=str(e))
            return False
    
    async def get_models(self) -> list[dict]:
        """List available models on Ollama server."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.api_url}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception as e:
            logger.error("ollama.list_models_failed", error=str(e))
            return []
    
    async def classify(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Classify a message using LLM (classification model).
        
        Args:
            message: User message to classify
            system_prompt: Optional system prompt for classification task
            temperature: Model temperature (lower = more deterministic)
        
        Returns:
            Classification result (e.g., task code)
        """
        try:
            client = await self._get_client()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})
            
            payload = {
                "model": self.classification_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            }
            
            logger.info(
                "ollama.classify_request",
                model=self.classification_model,
                message_length=len(message)
            )
            
            resp = await client.post(
                f"{self.api_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            
            result = resp.json()
            content = result.get("message", {}).get("content", "").strip()
            
            logger.info(
                "ollama.classify_success",
                response_length=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error("ollama.classify_failed", error=str(e))
            raise
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[list[float]]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Optional model override (defaults to embedding_model)
        
        Returns:
            Embedding vector (1024 dimensions) or None on error
        """
        try:
            client = await self._get_client()
            model = model or self.embedding_model
            
            payload = {
                "model": model,
                "input": text,
            }
            
            logger.info("ollama.embed_request", text_length=len(text))
            
            resp = await client.post(
                f"{self.api_url}/api/embed",
                json=payload,
            )
            resp.raise_for_status()
            
            result = resp.json()
            embeddings = result.get("embeddings", [])
            
            if embeddings:
                logger.info(
                    "ollama.embed_success",
                    embedding_dimension=len(embeddings[0])
                )
                return embeddings[0]
            
            return None
            
        except Exception as e:
            logger.error("ollama.embed_failed", error=str(e))
            return None
    
    async def chat_stream(
        self,
        message: str,
        model: Optional[str] = None,
    ):
        """
        Stream chat response (generator).
        
        Yields chunks of response text as they arrive.
        """
        try:
            client = await self._get_client()
            model = model or self.classification_model
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "stream": True,
            }
            
            async with client.stream(
                "POST",
                f"{self.api_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            import json
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except Exception:
                            pass
                            
        except Exception as e:
            logger.error("ollama.chat_stream_failed", error=str(e))


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


async def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def close_ollama_client():
    """Close global Ollama client."""
    global _ollama_client
    if _ollama_client is not None:
        await _ollama_client.close()
        _ollama_client = None
