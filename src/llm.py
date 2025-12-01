"""LLM backend with support for OpenAI, Ollama, and transformers."""

from typing import Optional, Iterator, List, Dict, Any
import logging
import requests
import json

from src.config import config
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class LLM:
    """LLM wrapper supporting multiple backends."""
    
    def __init__(
        self,
        backend: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 800
    ):
        """
        Initialize the LLM.
        
        Args:
            backend: 'openai', 'ollama', or 'transformers' (auto-detect if None)
            model_name: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None  # For OpenAI client
        
        # Determine backend based on configuration
        if backend is None:
            if not config.local and config.openai_api_key:
                # LOCAL=0 and API key present: Use OpenAI ONLY
                backend = "openai"
                logger.info("Auto-detected backend: OpenAI (LOCAL=0)")
            elif config.local:
                # LOCAL=1: Try local models (Ollama first, then transformers)
                backend = "ollama"
                logger.info("Auto-detected backend: Local models (LOCAL=1)")
            else:
                # LOCAL=0 but no API key
                logger.error("LOCAL=0 but OPENAI_API_KEY not set!")
                raise ValueError(
                    "OpenAI selected (LOCAL=0) but OPENAI_API_KEY not configured. "
                    "Set OPENAI_API_KEY in .env or set LOCAL=1 for local models."
                )
        
        self.backend = backend
        self.model_name = model_name
        
        # Initialize backend
        if self.backend == "openai":
            self._init_openai()
        elif self.backend == "ollama":
            self._init_ollama()
        elif self.backend == "transformers":
            self._init_transformers()
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def _init_openai(self):
        """Initialize OpenAI backend."""
        try:
            from openai import OpenAI
            
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            
            self.client = OpenAI(api_key=config.openai_api_key)
            self.model_name = self.model_name or config.openai_model
            
            # Log successful initialization (without exposing API key)
            logger.info(f"✓ LLM backend initialized: backend=openai, model={self.model_name}, local=False")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI backend: {e}")
            
            # When LOCAL=0, do NOT fall back to local models
            if not config.local:
                logger.error("LOCAL=0 requires OpenAI. Not falling back to local models.")
                raise RuntimeError(
                    f"OpenAI initialization failed: {e}\n"
                    "Fix: Ensure OPENAI_API_KEY is correctly set in .env, or set LOCAL=1 to use local models."
                )
            
            # Only fall back if LOCAL=1
            logger.warning("OpenAI failed but LOCAL=1, attempting local fallback...")
            self.backend = "ollama"
            self._init_ollama()
    
    def _init_ollama(self):
        """Initialize Ollama backend (only when LOCAL=1)."""
        if not config.local:
            raise RuntimeError("Ollama backend should only be used when LOCAL=1")
        
        self.model_name = self.model_name or config.local_model
        self.ollama_url = f"{config.ollama_base_url}/api/generate"
        
        # Test connection
        try:
            response = requests.get(f"{config.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ LLM backend initialized: backend=ollama, model={self.model_name}, local=True")
                return
        except Exception as e:
            logger.warning(f"Ollama not available at {config.ollama_base_url}: {e}")
        
        # Fallback to transformers (only when LOCAL=1)
        logger.info("Ollama unavailable, falling back to transformers...")
        self.backend = "transformers"
        self._init_transformers()
    
    def _init_transformers(self):
        """Initialize transformers backend (only when LOCAL=1)."""
        if not config.local:
            raise RuntimeError("Transformers backend should only be used when LOCAL=1")
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            import torch
            
            # CRITICAL FIX: Don't use Ollama model names (llama3.1:8b) with transformers
            # If model_name is an Ollama-format name, reset to a valid HF repo ID
            if self.model_name and ":" in self.model_name:
                logger.warning(
                    f"Model name '{self.model_name}' looks like Ollama format (has ':'), "
                    "not a valid Hugging Face repo ID. Resetting to default HF model."
                )
                self.model_name = None
            
            # Use a valid Hugging Face model name
            self.model_name = self.model_name or "google/gemma-2b-it"
            logger.info(f"Loading transformers model: {self.model_name}")
            
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Use CPU by default for compatibility
            device = "cpu"
            logger.info(f"Using device: {device}")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )
            self.model.to(device)
            
            # Create pipeline
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=device,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
            )
            
            logger.info(f"✓ LLM backend initialized: backend=transformers, model={self.model_name}, local=True")
            
        except Exception as e:
            logger.error(f"Failed to initialize transformers: {e}")
            logger.error("No LLM backend available. Queries will fail.")
            self.backend = "none"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> str:
        """
        Generate a response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream the response
            
        Returns:
            Generated text
        """
        if self.backend == "openai":
            return self._generate_openai(messages, stream)
        elif self.backend == "ollama":
            return self._generate_ollama(messages, stream)
        elif self.backend == "transformers":
            return self._generate_transformers(messages)
        else:
            return "LLM backend not available. Showing retrieval results only."
    
    def _generate_openai(self, messages: List[Dict[str, str]], stream: bool) -> str:
        """Generate using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=stream
            )
            
            if stream:
                # Return iterator for streaming
                return response
            else:
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return f"Error: {e}"
    
    def _generate_ollama(self, messages: List[Dict[str, str]], stream: bool) -> str:
        """Generate using Ollama API."""
        try:
            # Convert messages to prompt
            prompt = self._messages_to_prompt(messages)
            
            # Make request
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                },
                stream=stream,
                timeout=60
            )
            
            if stream:
                return self._stream_ollama_response(response)
            else:
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            # Only try transformers fallback if LOCAL=1
            if self.backend == "ollama" and config.local:
                logger.info("Attempting transformers fallback (LOCAL=1)...")
                self.backend = "transformers"
                self._init_transformers()
                if self.backend == "transformers":
                    return self._generate_transformers(messages)
            return f"Error: {e}"
    
    def _generate_transformers(self, messages: List[Dict[str, str]]) -> str:
        """Generate using transformers pipeline."""
        try:
            # Convert messages to prompt
            prompt = self._messages_to_prompt(messages)
            
            # Generate
            outputs = self.pipe(
                prompt,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
            # Extract generated text
            generated_text = outputs[0]["generated_text"]
            
            # Remove the prompt from the output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()
            
            return generated_text
        except Exception as e:
            logger.error(f"Transformers generation failed: {e}")
            return f"Error: {e}"
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single prompt string."""
        prompt_parts = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        
        prompt_parts.append("Assistant: ")
        return "\n".join(prompt_parts)
    
    def _stream_ollama_response(self, response) -> str:
        """Stream Ollama response (for now, collect and return)."""
        # For simplicity, collect all chunks
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        full_response += data["response"]
                except:
                    pass
        return full_response
    
    def get_backend_info(self) -> Dict[str, str]:
        """Get information about the current backend."""
        return {
            "backend": self.backend,
            "model": self.model_name or "unknown",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


def get_llm(
    backend: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> LLM:
    """
    Get an LLM instance with configuration.
    
    Args:
        backend: Optional backend override
        model_name: Optional model name override
        temperature: Optional temperature override
        max_tokens: Optional max_tokens override
        
    Returns:
        LLM instance
    """
    return LLM(
        backend=backend,
        model_name=model_name,
        temperature=temperature or config.temperature,
        max_tokens=max_tokens or config.max_tokens
    )

