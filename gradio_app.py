import json
import os
from typing import Any, Dict, List, Tuple

import gradio as gr
import requests


API_URL = os.getenv("ARAB_POET_API_URL", "http://localhost:8000/api/v1/analyze")
MODEL_VERSION_FALLBACK = "ArabPoet UI"

TASK_OPTIONS: List[Tuple[str, str]] = [
    ("البحر", "meter"),
    ("القافية", "rhyme"),
    ("فحص الكسر العروضي", "errors"),
    ("شرح مبسط", "explanation_simple"),
    ("شرح أدبي مفصل", "explanation_detailed"),
    ("الغرض الشعري / الموضوع", "theme"),
    ("التحليل الشامل", "all"),
]


def _status_badge(text: str, kind: str) -> str:
    colors = {
        "success": "#0f766e",
        "warning": "#b45309",
        "danger": "#b91c1c",
        "info": "#1d4ed8",
        "muted": "#475569",
    }
    color = colors.get(kind, colors["muted"])
    return (
        f'<span style="display:inline-block;padding:0.35rem 0.7rem;border-radius:999px;'
        f'background:{color};color:white;font-size:0.8rem;font-weight:700;">{text}</span>'
    )


def _render_result_card(title: str, payload: Dict[str, Any]) -> str:
    result = payload.get("result", "")
    source = payload.get("source", "unknown")
    fail = bool(payload.get("fail", False))

    source_kind = "info"
    if source == "gemini_fallback":
        source_kind = "warning"
    elif source == "local_qwen_rag":
        source_kind = "success"

    fail_badge = _status_badge("فشل" if fail else "نجاح", "danger" if fail else "success")
    source_badge = _status_badge(f"<span class='ltr-inline'>{source}</span>", source_kind)

    return f"""
    <div class="result-card">
        <div class="result-card__head">
            <h3>{title}</h3>
            <div class="badge-row">{source_badge} {fail_badge}</div>
        </div>
        <div class="result-card__body">{result if result else 'لا توجد نتيجة متاحة'}</div>
    </div>
    """


def _normalize_payload(poem_text: str, task: str, is_full_poem: bool) -> Dict[str, Any]:
    return {
        "poem_text": (poem_text or "").strip(),
        "task": task,
        "is_full_poem": bool(is_full_poem),
    }


def analyze_poem(poem_text: str, task: str, is_full_poem: bool) -> Tuple[str, str]:
    if len((poem_text or "").strip()) < 10:
        return (
            "<div class='summary-box'>يرجى إدخال نص عربي أطول قليلًا قبل الإرسال.</div>",
            _status_badge("غير صالح للإرسال", "danger"),
        )

    payload = _normalize_payload(poem_text, task, is_full_poem)

    try:
        response = requests.post(API_URL, json=payload, timeout=900)
    except requests.RequestException:
        return (
            "<div class='summary-box'>تعذر الوصول إلى السيرفر المحلي. تأكد من تشغيل FastAPI على المنفذ الصحيح.</div>",
            _status_badge("انقطاع الاتصال", "danger"),
        )

    if response.status_code == 422:
        return (
            "<div class='summary-box'>المدخلات غير مكتملة أو غير صحيحة وفق schema الخدمة.</div>",
            _status_badge("422 Unprocessable Entity", "danger"),
        )

    if response.status_code >= 500:
        return (
            "<div class='summary-box'>عذراً، حدث خطأ في محركات التحليل. يرجى المحاولة مرة أخرى.</div>",
            _status_badge(f"{response.status_code} Server Error", "danger"),
        )

    response.raise_for_status()
    data = response.json()

    results = data.get("results", {}) or {}
    model_version = data.get("model_version", MODEL_VERSION_FALLBACK)
    overall_fail = bool(data.get("overall_fail", False))

    cards = []
    order = ["meter", "rhyme", "errors", "explanation_simple", "explanation_detailed", "theme"]
    labels = {
        "meter": "البحر",
        "rhyme": "القافية",
        "errors": "فحص الكسر العروضي",
        "explanation_simple": "شرح مبسط",
        "explanation_detailed": "شرح أدبي مفصل",
        "theme": "الغرض الشعري / الموضوع",
    }

    for key in order:
        if key in results:
            cards.append(_render_result_card(labels.get(key, key), results[key]))

    for key, value in results.items():
        if key not in order:
            cards.append(_render_result_card(key, value))

    source_notes = []
    if any((value.get("source") == "gemini_fallback" for value in results.values() if isinstance(value, dict))):
        source_notes.append(_status_badge("Gemini fallback تم استخدامه تلقائيًا", "warning"))
    if overall_fail:
        source_notes.append(_status_badge("هناك فشل جزئي في أحد المسارات", "danger"))
    if not source_notes:
        source_notes.append(_status_badge("النتيجة مكتملة", "success"))

    summary_html = f"""
    <div class="summary-box">
        <div class="summary-top">
            <h2>ملخص التحليل</h2>
            <div class="badge-row">{''.join(source_notes)}</div>
        </div>
        <div class="summary-grid">
            <div><span>إصدار النموذج</span><strong>{model_version}</strong></div>
            <div><span>عدد النتائج</span><strong>{len(results)}</strong></div>
        </div>
    </div>
    <div class="results-grid">
        {''.join(cards)}
    </div>
    """

    status = _status_badge("اكتمل التحليل", "success")
    return summary_html, status


def clear_inputs() -> Tuple[str, str, bool, str, str]:
    return "", "all", False, _status_badge("تم المسح", "info"), ""


CUSTOM_CSS = """
:root {
    --bg: #f4efe7;
    --panel: rgba(255, 255, 255, 0.78);
    --panel-solid: #fffdf8;
    --text: #1f2937;
    --muted: #6b7280;
    --line: rgba(31, 41, 55, 0.12);
    --accent: #7c3aed;
    --accent-2: #0f766e;
    --shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
}

body, .gradio-container {
    background:
        radial-gradient(circle at top right, rgba(124, 58, 237, 0.10), transparent 32%),
        radial-gradient(circle at left bottom, rgba(15, 118, 110, 0.10), transparent 28%),
        linear-gradient(180deg, #f8f4ed 0%, #f4efe7 100%);
    color: var(--text);
    direction: rtl;
    unicode-bidi: plaintext;
    font-family: 'Noto Naskh Arabic', 'Tahoma', serif;
}

.gradio-container * {
    text-align: right;
}

.ltr-inline {
    direction: ltr;
    unicode-bidi: isolate;
    display: inline-block;
    text-align: left;
}

.hero {
    background: linear-gradient(135deg, rgba(28, 25, 23, 0.92), rgba(55, 48, 163, 0.92));
    color: white;
    border-radius: 24px;
    padding: 28px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.hero::after {
    content: '';
    position: absolute;
    inset: auto -60px -70px auto;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 65%);
}

.hero h1 {
    margin: 0;
    font-size: 2rem;
}

.hero p {
    margin: 0;
    max-width: 820px;
    line-height: 1.8;
    color: rgba(255, 255, 255, 0.86);
}

.panel {
    background: var(--panel);
    border: 1px solid var(--line);
    backdrop-filter: blur(14px);
    border-radius: 22px;
    box-shadow: var(--shadow);
}

.result-card, .summary-box {
    background: var(--panel-solid);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
}

.summary-top, .result-card__head, .badge-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-top: 16px;
}

.summary-grid div {
    padding: 12px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid rgba(148, 163, 184, 0.25);
}

.summary-grid span {
    display: block;
    color: var(--muted);
    font-size: 0.85rem;
    margin-bottom: 6px;
}

.summary-grid strong {
    font-size: 1.05rem;
}

.result-card__head h3 {
    margin: 0;
    font-size: 1.1rem;
}

.result-card__body {
    margin-top: 14px;
    line-height: 1.9;
    white-space: pre-wrap;
    unicode-bidi: plaintext;
}

.result-card__meta {
    margin-top: 14px;
    color: var(--muted);
    font-size: 0.9rem;
}

.gr-button-primary, button.primary {
    background: linear-gradient(135deg, var(--accent), #4f46e5) !important;
    border: none !important;
    color: white !important;
}

.tiny-note {
    color: var(--muted);
    font-size: 0.95rem;
    line-height: 1.8;
}
"""


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Arab Poet Gradio") as demo:
        gr.Markdown(
            """
            <div class="hero">
                <h1>Arab Poet Interface</h1>
            </div>
            """
        )

        with gr.Row():
            with gr.Column(scale=5, elem_classes=["panel"]):
                poem_text = gr.Textbox(
                    label="نص القصيدة",
                    placeholder="اكتب البيت أو القصيدة هنا...",
                    lines=10,
                    text_align="right",
                )
                task = gr.Radio(
                    choices=TASK_OPTIONS,
                    value="all",
                    label="نوع التحليل",
                    info="",
                )
                is_full_poem = gr.Checkbox(
                    value=False,
                    label="النص قصيدة كاملة متعددة الأبيات",
                )
                with gr.Row():
                    analyze_btn = gr.Button("ابدأ التحليل", variant="primary")
                    clear_btn = gr.Button("مسح الحقول", variant="secondary")

            with gr.Column(scale=7, elem_classes=["panel"]):
                status_box = gr.HTML(_status_badge("بانتظار الإدخال", "muted"))
                summary_box = gr.HTML()

        analyze_btn.click(
            fn=analyze_poem,
            inputs=[poem_text, task, is_full_poem],
            outputs=[summary_box, status_box],
        )

        clear_btn.click(
            fn=clear_inputs,
            inputs=None,
            outputs=[poem_text, task, is_full_poem, status_box, summary_box],
        )

    return demo


if __name__ == "__main__":
    demo = build_demo()
    demo.queue(max_size=16)
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
        css=CUSTOM_CSS,
    )