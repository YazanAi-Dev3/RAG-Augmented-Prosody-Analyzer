import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Arab Poet Microservice"
    APP_VERSION: str = "1.0.0"
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Local Services
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "qwen:8b")
    
    # System Thresholds
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.75))
    
    # Paths
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "models/bge-m3")
    QDRANT_STORAGE_PATH: str = os.getenv("QDRANT_STORAGE_PATH", "local_qdrant_db")

    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()