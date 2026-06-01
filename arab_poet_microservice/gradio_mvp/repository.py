import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import get_conn


def create_user(username: str, password_hash: str) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, now),
        )
        return int(cur.lastrowid)


def get_user_by_username(username: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def save_analysis(user_id: int, poem_text: str, is_full_poem: bool, task: str, response: Dict[str, Any], success: bool) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO poems (user_id, poem_text, is_full_poem, created_at) VALUES (?, ?, ?, ?)",
            (user_id, poem_text, 1 if is_full_poem else 0, now),
        )
        poem_id = cur.lastrowid
        conn.execute(
            "INSERT INTO analyses (user_id, poem_id, task, response_json, success, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, poem_id, task, json.dumps(response, ensure_ascii=False), 1 if success else 0, now),
        )


def get_history_rows(user_id: int) -> List[List[Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id AS analysis_id,
                a.created_at,
                a.task,
                a.success,
                p.is_full_poem,
                substr(replace(p.poem_text, char(10), ' '), 1, 70) AS poem_preview
            FROM analyses a
            JOIN poems p ON p.id = a.poem_id
            WHERE a.user_id = ?
            ORDER BY a.id DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()

    table: List[List[Any]] = []
    for r in rows:
        table.append(
            [
                int(r["analysis_id"]),
                r["created_at"],
                r["task"],
                "نعم" if int(r["is_full_poem"]) else "لا",
                "نجاح" if int(r["success"]) else "فشل",
                r["poem_preview"],
            ]
        )
    return table


def get_history_choices(user_id: int) -> List[str]:
    rows = get_history_rows(user_id)
    return [f"{r[0]} | {r[1]} | {r[2]}" for r in rows]


def load_analysis_record(user_id: int, analysis_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT a.id, a.task, a.response_json, p.poem_text, p.is_full_poem
            FROM analyses a
            JOIN poems p ON p.id = a.poem_id
            WHERE a.id = ? AND a.user_id = ?
            """,
            (analysis_id, user_id),
        ).fetchone()

    if not row:
        return None

    return {
        "analysis_id": int(row["id"]),
        "task": row["task"],
        "poem_text": row["poem_text"],
        "is_full_poem": bool(row["is_full_poem"]),
        "response": json.loads(row["response_json"]),
    }
