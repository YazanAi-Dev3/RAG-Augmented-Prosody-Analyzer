from typing import Any, Dict

from .config import MODEL_VERSION_FALLBACK


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

.gradio-container * { text-align: right; }
.ltr-inline { direction: ltr; unicode-bidi: isolate; display: inline-block; text-align: left; }

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
.hero h1 { margin: 0; font-size: 2rem; }

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
.summary-grid span { display: block; color: var(--muted); font-size: 0.85rem; margin-bottom: 6px; }
.summary-grid strong { font-size: 1.05rem; }
.result-card__head h3 { margin: 0; font-size: 1.1rem; }
.result-card__body { margin-top: 14px; line-height: 1.9; white-space: pre-wrap; unicode-bidi: plaintext; }
.gr-button-primary, button.primary {
    background: linear-gradient(135deg, var(--accent), #4f46e5) !important;
    border: none !important;
    color: white !important;
}
"""


def status_badge(text: str, kind: str) -> str:
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


def render_result_card(title: str, payload: Dict[str, Any]) -> str:
    result = payload.get("result", "")
    source = payload.get("source", "unknown")
    fail = bool(payload.get("fail", False))

    source_kind = "info"
    if source == "gemini_fallback":
        source_kind = "warning"
    elif source == "local_qwen_rag":
        source_kind = "success"

    fail_badge = status_badge("فشل" if fail else "نجاح", "danger" if fail else "success")
    source_badge = status_badge(f"<span class='ltr-inline'>{source}</span>", source_kind)

    return f"""
    <div class="result-card">
        <div class="result-card__head">
            <h3>{title}</h3>
            <div class="badge-row">{source_badge} {fail_badge}</div>
        </div>
        <div class="result-card__body">{result if result else 'لا توجد نتيجة متاحة'}</div>
    </div>
    """


def build_summary_html(data: Dict[str, Any]) -> str:
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
            cards.append(render_result_card(labels.get(key, key), results[key]))

    for key, value in results.items():
        if key not in order:
            cards.append(render_result_card(key, value))

    source_notes = []
    if any((value.get("source") == "gemini_fallback" for value in results.values() if isinstance(value, dict))):
        source_notes.append(status_badge("Gemini fallback تم استخدامه تلقائيًا", "warning"))
    if overall_fail:
        source_notes.append(status_badge("هناك فشل جزئي في أحد المسارات", "danger"))
    if not source_notes:
        source_notes.append(status_badge("النتيجة مكتملة", "success"))

    return f"""
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
