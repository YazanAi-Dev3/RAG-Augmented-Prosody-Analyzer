from typing import Any, Dict, Optional, Tuple

import requests

from .config import API_URL
from .rendering import build_summary_html, status_badge


def normalize_payload(poem_text: str, task: str, is_full_poem: bool) -> Dict[str, Any]:
    return {
        "poem_text": (poem_text or "").strip(),
        "task": task,
        "is_full_poem": bool(is_full_poem),
    }


def request_analysis(poem_text: str, task: str, is_full_poem: bool) -> Tuple[Optional[Dict[str, Any]], str, str]:
    if len((poem_text or "").strip()) < 10:
        return None, "<div class='summary-box'>يرجى إدخال نص عربي أطول قليلًا قبل الإرسال.</div>", status_badge("غير صالح للإرسال", "danger")

    payload = normalize_payload(poem_text, task, is_full_poem)

    try:
        response = requests.post(API_URL, json=payload, timeout=900)
    except requests.RequestException:
        return None, "<div class='summary-box'>تعذر الوصول إلى السيرفر المحلي. تأكد من تشغيل FastAPI على المنفذ الصحيح.</div>", status_badge("انقطاع الاتصال", "danger")

    if response.status_code == 422:
        return None, "<div class='summary-box'>المدخلات غير مكتملة أو غير صحيحة وفق schema الخدمة.</div>", status_badge("422 Unprocessable Entity", "danger")

    if response.status_code >= 500:
        return None, "<div class='summary-box'>عذراً، حدث خطأ في محركات التحليل. يرجى المحاولة مرة أخرى.</div>", status_badge(f"{response.status_code} Server Error", "danger")

    response.raise_for_status()
    data = response.json()
    return data, build_summary_html(data), status_badge("اكتمل التحليل", "success")
