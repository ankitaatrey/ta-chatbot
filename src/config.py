"""Configuration management for the TA chatbot."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration with environment variable support."""
    
    # LLM Backend
    # Default to OpenAI (LOCAL=0) for better reliability
    local: bool = Field(default=False)
    openai_api_key: Optional[str] = Field(default=None)
    local_model: str = Field(default="llama3.1:8b")
    openai_model: str = Field(default="gpt-4o-mini")
    
    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    
    # Embeddings
    use_local_embeddings: bool = Field(default=True)
    
    # Paths
    chroma_path: Path = Field(default=Path("./chroma_db"))
    collection_name: str = Field(default="ta_documents")
    data_dir: Path = Field(default=Path("./data"))
    
    # Retrieval
    top_k: int = Field(default=3, ge=1, le=20)  # Reduced from 4 for faster retrieval
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    use_mmr: bool = Field(default=False)  # Disabled by default for speed
    mmr_diversity: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # Chunking
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=500)
    
    # Generation
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=800, ge=100, le=4000)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Default to "0" (OpenAI) for better reliability
        local_val = os.getenv("LOCAL", "0")
        
        return cls(
            local=local_val == "1",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            local_model=os.getenv("LOCAL_MODEL", "llama3.1:8b"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            use_local_embeddings=os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true",
            chroma_path=Path(os.getenv("CHROMA_PATH", "./chroma_db")),
            collection_name=os.getenv("COLLECTION_NAME", "ta_documents"),
            top_k=int(os.getenv("TOP_K", "3")),
            score_threshold=float(os.getenv("SCORE_THRESHOLD", "0.3")),
            use_mmr=os.getenv("USE_MMR", "false").lower() == "true",
            mmr_diversity=float(os.getenv("MMR_DIVERSITY", "0.3")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
            temperature=float(os.getenv("TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("MAX_TOKENS", "800")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def get_backend(self) -> str:
        """Return the active LLM backend name."""
        if not self.local and self.openai_api_key:
            return f"OpenAI ({self.openai_model})"
        return f"Local ({self.local_model})"


# Global config instance
config = Config.from_env()

# Log configuration at module load for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded: LOCAL={config.local}, Backend={config.get_backend()}")

