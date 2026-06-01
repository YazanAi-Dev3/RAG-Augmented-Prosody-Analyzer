import os
from typing import List, Tuple

API_URL = os.getenv("ARAB_POET_API_URL", "http://localhost:8000/api/v1/analyze")
MODEL_VERSION_FALLBACK = "ArabPoet UI"
DB_PATH = os.getenv("ARAB_POET_UI_DB_PATH", "data/gradio_app.db")
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))

TASK_OPTIONS: List[Tuple[str, str]] = [
    ("البحر", "meter"),
    ("القافية", "rhyme"),
    ("فحص الكسر العروضي", "errors"),
    ("شرح مبسط", "explanation_simple"),
    ("شرح أدبي مفصل", "explanation_detailed"),
    ("الغرض الشعري / الموضوع", "theme"),
    ("التحليل الشامل", "all"),
]
