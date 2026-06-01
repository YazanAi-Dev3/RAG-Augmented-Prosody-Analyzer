from pydantic import BaseModel
from typing import Any, Dict, Optional

class TaskResult(BaseModel):
    result: Any
    confidence: float
    fail: bool
    source: str  # e.g., 'local_model', 'qdrant_qwen', or 'gemini_fallback'

class PoemAnalysisResponse(BaseModel):
    model_version: str = "ArabPoet-v1.0"
    results: Dict[str, TaskResult]
    overall_confidence: float
    overall_fail: bool