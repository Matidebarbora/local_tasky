from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

DB_PATH = Path.home() / ".tasky_local" / "tasky.db"

# Serializa TODO el acceso a SQLite dentro del proceso — protección barata
# contra "database is locked" frente a cualquier acceso concurrente.
_db_lock = threading.RLock()


class _LockedConn:
    """Context manager: toma _db_lock, entrega la conexión y la cierra al salir."""

    def __enter__(self) -> sqlite3.Connection:
        _db_lock.acquire()
        try:
            self._conn = sqlite3.connect(str(DB_PATH), timeout=10)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        except BaseException:
            _db_lock.release()
            raise
        return self._conn

    def __exit__(self, *exc) -> None:
        try:
            self._conn.__exit__(*exc)   # commit si no hubo excepción, si no rollback
        finally:
            try:
                self._conn.close()
            finally:
                _db_lock.release()


def _conn() -> _LockedConn:
    return _LockedConn()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                name  TEXT PRIMARY KEY,
                color TEXT NOT NULL DEFAULT 'cyan'
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                task        TEXT NOT NULL,
                priority    TEXT NOT NULL DEFAULT '2. MEDIUM',
                status      TEXT NOT NULL DEFAULT 'TO DO',
                notes       TEXT,
                sort_order  INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sub_tasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id    INTEGER NOT NULL,
                task       TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'TO DO',
                notes      TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS project_logs (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                project  TEXT NOT NULL,
                log_date TEXT NOT NULL,
                title    TEXT NOT NULL,
                notes    TEXT NOT NULL DEFAULT ''
            );
        """)


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def local_load_data() -> dict:
    with _conn() as c:
        proj_rows = c.execute("SELECT name, color FROM projects ORDER BY name").fetchall()
        project_colors = {r["name"]: r["color"] for r in proj_rows}
        projects: dict[str, list] = {r["name"]: [] for r in proj_rows}

        task_rows = c.execute(
            "SELECT * FROM tasks ORDER BY project, sort_order, id"
        ).fetchall()
        task_ids = [r["id"] for r in task_rows]

        sub_map: dict[int, list] = {tid: [] for tid in task_ids}
        if task_ids:
            ph = ",".join("?" * len(task_ids))
            sub_rows = c.execute(
                f"SELECT * FROM sub_tasks WHERE task_id IN ({ph}) ORDER BY sort_order, id",
                task_ids,
            ).fetchall()
            for s in sub_rows:
                sub_map[s["task_id"]].append({
                    "task": s["task"], "status": s["status"],
                    "notes": s["notes"], "_id": s["id"],
                })

        for t in task_rows:
            projects[t["project"]].append({
                "task": t["task"], "priority": t["priority"],
                "status": t["status"], "notes": t["notes"],
                "sub_tasks": sub_map[t["id"]],
                "_id": t["id"],
            })

    return {"projects": projects, "project_colors": project_colors}


def local_get_task(task_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(r) if r else None


def local_get_subtask(sub_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM sub_tasks WHERE id=?", (sub_id,)).fetchone()
        return dict(r) if r else None


def local_get_subtask_parent(sub_id: int) -> int | None:
    with _conn() as c:
        r = c.execute("SELECT task_id FROM sub_tasks WHERE id=?", (sub_id,)).fetchone()
        return r["task_id"] if r else None


def local_get_project_for_task(task_id: int) -> str | None:
    with _conn() as c:
        r = c.execute("SELECT project FROM tasks WHERE id=?", (task_id,)).fetchone()
        return r["project"] if r else None


def local_get_project_logs(project: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, log_date, title, notes FROM project_logs "
            "WHERE project=? ORDER BY log_date DESC, id DESC",
            (project,),
        ).fetchall()
        return [dict(r) for r in rows]


def local_get_log_by_id(log_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute(
            "SELECT id, log_date, title, notes FROM project_logs WHERE id=?", (log_id,)
        ).fetchone()
        return dict(r) if r else None


# ---------------------------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------------------------

def local_add_project(name: str, color: str) -> bool:
    with _conn() as c:
        if c.execute("SELECT 1 FROM projects WHERE name=?", (name,)).fetchone():
            return False
        c.execute("INSERT INTO projects VALUES (?,?)", (name, color))
        return True


def local_update_project(old_name: str, new_name: str | None, new_color: str | None) -> None:
    with _conn() as c:
        if new_color:
            c.execute("UPDATE projects SET color=? WHERE name=?", (new_color, old_name))
        if new_name and new_name != old_name:
            c.execute("UPDATE tasks SET project=? WHERE project=?", (new_name, old_name))
            c.execute("UPDATE project_logs SET project=? WHERE project=?", (new_name, old_name))
            c.execute("UPDATE projects SET name=? WHERE name=?", (new_name, old_name))


def local_delete_project(name: str) -> None:
    with _conn() as c:
        task_ids = [r[0] for r in c.execute("SELECT id FROM tasks WHERE project=?", (name,)).fetchall()]
        if task_ids:
            ph = ",".join("?" * len(task_ids))
            c.execute(f"DELETE FROM sub_tasks WHERE task_id IN ({ph})", task_ids)
        c.execute("DELETE FROM tasks WHERE project=?", (name,))
        c.execute("DELETE FROM project_logs WHERE project=?", (name,))
        c.execute("DELETE FROM projects WHERE name=?", (name,))


# ---------------------------------------------------------------------------
# TASKS
# ---------------------------------------------------------------------------

def local_add_task(project: str, task: str, priority: str, status: str, notes: str | None) -> int:
    with _conn() as c:
        max_row = c.execute(
            "SELECT MAX(sort_order) AS m FROM tasks WHERE project=?", (project,)
        ).fetchone()
        sort_order = (max_row["m"] or 0) + 1
        cur = c.execute(
            "INSERT INTO tasks (project, task, priority, status, notes, sort_order) VALUES (?,?,?,?,?,?)",
            (project, task, priority, status, notes, sort_order),
        )
        return cur.lastrowid


def local_update_task(task_id: int, task: str, priority: str, status: str, notes: str | None) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET task=?, priority=?, status=?, notes=? WHERE id=?",
            (task, priority, status, notes, task_id),
        )


def local_delete_task(task_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sub_tasks WHERE task_id=?", (task_id,))
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))


# ---------------------------------------------------------------------------
# SUB-TASKS
# ---------------------------------------------------------------------------

def local_add_subtask(task_id: int, task: str, status: str, notes: str | None) -> int:
    with _conn() as c:
        max_row = c.execute(
            "SELECT MAX(sort_order) AS m FROM sub_tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        sort_order = (max_row["m"] or 0) + 1
        cur = c.execute(
            "INSERT INTO sub_tasks (task_id, task, status, notes, sort_order) VALUES (?,?,?,?,?)",
            (task_id, task, status, notes, sort_order),
        )
        return cur.lastrowid


def local_update_subtask(sub_id: int, task: str, status: str, notes: str | None) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE sub_tasks SET task=?, status=?, notes=? WHERE id=?",
            (task, status, notes, sub_id),
        )


def local_delete_subtask(sub_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sub_tasks WHERE id=?", (sub_id,))


# ---------------------------------------------------------------------------
# PROJECT LOGS
# ---------------------------------------------------------------------------

def local_add_project_log(project: str, log_date: str, title: str, notes: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO project_logs (project, log_date, title, notes) VALUES (?,?,?,?)",
            (project, log_date, title, notes),
        )
        return cur.lastrowid


def local_update_project_log(log_id: int, log_date: str, title: str, notes: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE project_logs SET log_date=?, title=?, notes=? WHERE id=?",
            (log_date, title, notes, log_id),
        )


def local_delete_project_log(log_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM project_logs WHERE id=?", (log_id,))
