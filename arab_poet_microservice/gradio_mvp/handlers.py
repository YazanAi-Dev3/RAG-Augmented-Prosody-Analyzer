import sqlite3
from typing import Any, Dict, List, Tuple

import gradio as gr

from .analysis_service import request_analysis
from .rendering import build_summary_html, status_badge
from .repository import (
    create_user,
    get_history_choices,
    get_history_rows,
    get_user_by_username,
    load_analysis_record,
    save_analysis,
)
from .security import hash_password, verify_password


def register_user(username: str, password: str) -> Tuple[Dict[str, Any], str, Any, Any, str]:
    username = (username or "").strip()
    if len(username) < 3 or len(password or "") < 6:
        return (
            {},
            status_badge("اسم المستخدم 3 أحرف على الأقل وكلمة المرور 6 أحرف على الأقل", "danger"),
            gr.update(visible=True),
            gr.update(visible=False),
            "",
        )

    try:
        user_id = create_user(username, hash_password(password))
    except sqlite3.IntegrityError:
        return (
            {},
            status_badge("اسم المستخدم مستخدم مسبقًا", "danger"),
            gr.update(visible=True),
            gr.update(visible=False),
            "",
        )

    user = {"id": user_id, "username": username}
    return (
        user,
        status_badge("تم إنشاء الحساب وتسجيل الدخول", "success"),
        gr.update(visible=False),
        gr.update(visible=True),
        f"<b>مرحبًا {username}</b>",
    )


def login_user(username: str, password: str) -> Tuple[Dict[str, Any], str, Any, Any, str]:
    username = (username or "").strip()
    row = get_user_by_username(username)

    if not row or not verify_password(password or "", row["password_hash"]):
        return (
            {},
            status_badge("بيانات الدخول غير صحيحة", "danger"),
            gr.update(visible=True),
            gr.update(visible=False),
            "",
        )

    user = {"id": int(row["id"]), "username": row["username"]}
    return (
        user,
        status_badge("تم تسجيل الدخول", "success"),
        gr.update(visible=False),
        gr.update(visible=True),
        f"<b>مرحبًا {user['username']}</b>",
    )


def logout_user() -> Tuple[Dict[str, Any], str, Any, Any, str, str, List[List[Any]], Any]:
    return (
        {},
        status_badge("تم تسجيل الخروج", "info"),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        "",
        [],
        gr.update(choices=[], value=None),
    )


def analyze_and_store(poem_text: str, task: str, is_full_poem: bool, user: Dict[str, Any]) -> Tuple[str, str, List[List[Any]], Any]:
    if not user or not user.get("id"):
        return (
            "<div class='summary-box'>يجب تسجيل الدخول أولًا.</div>",
            status_badge("غير مصرح", "danger"),
            [],
            gr.update(choices=[], value=None),
        )

    data, summary_html, status = request_analysis(poem_text, task, is_full_poem)

    if data is not None:
        save_analysis(
            user_id=int(user["id"]),
            poem_text=poem_text,
            is_full_poem=is_full_poem,
            task=task,
            response=data,
            success=True,
        )

    rows = get_history_rows(int(user["id"]))
    choices = get_history_choices(int(user["id"]))
    return summary_html, status, rows, gr.update(choices=choices, value=None)


def refresh_history(user: Dict[str, Any]) -> Tuple[List[List[Any]], Any, str]:
    if not user or not user.get("id"):
        return [], gr.update(choices=[], value=None), status_badge("يجب تسجيل الدخول أولًا", "danger")

    rows = get_history_rows(int(user["id"]))
    choices = get_history_choices(int(user["id"]))
    return rows, gr.update(choices=choices, value=None), status_badge("تم تحديث السجل", "success")


def view_history_item(selected_item: str, user: Dict[str, Any]) -> Tuple[str, str, bool, str]:
    if not user or not user.get("id"):
        return "", "all", False, "<div class='summary-box'>يجب تسجيل الدخول أولًا.</div>"

    if not selected_item:
        return "", "all", False, "<div class='summary-box'>اختر عنصرًا من السجل أولًا.</div>"

    analysis_id = int(selected_item.split("|", 1)[0].strip())
    record = load_analysis_record(int(user["id"]), analysis_id)
    if not record:
        return "", "all", False, "<div class='summary-box'>العنصر غير موجود أو لا يخص هذا المستخدم.</div>"

    return (
        record["poem_text"],
        record["task"],
        bool(record["is_full_poem"]),
        build_summary_html(record["response"]),
    )


def clear_inputs() -> Tuple[str, str, bool, str, str]:
    return "", "all", False, status_badge("تم المسح", "info"), ""
