from pydantic import BaseModel, Field
from typing import Optional

class PoemAnalysisRequest(BaseModel):
    poem_text: str = Field(..., min_length=10, description="The Arabic poem text to analyze")
    task: str = Field(
        default="all",
        description="Type of analysis: meter, rhyme, errors, explanation_simple, explanation_detailed, theme, question, or all"
    )
    question: Optional[str] = Field(None, description="User question if task is 'question'")
    is_full_poem: bool = Field(False, description="Flag indicating if the input is a full poem (multiple verses) or a single verse")