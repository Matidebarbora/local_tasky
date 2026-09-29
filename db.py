from __future__ import annotations


def db_save_view_settings(vs: dict) -> None:
    from config import save_view_settings
    save_view_settings(vs)


def db_load_data() -> dict:
    from local_db import local_load_data
    from config import load_config
    data = local_load_data()
    cfg = load_config()
    vs = cfg.get("view_settings", {})
    data["view_settings"] = {
        "sort_by":          vs.get("sort_by", "priority"),
        "filter_project":   vs.get("filter_project"),
        "filter_priority":  vs.get("filter_priority"),
        "theme":            vs.get("theme", "textual-dark"),
        "hide_done":        vs.get("hide_done", False),
        "border_color":     vs.get("border_color", "#00FF00"),
        "bg_color":         vs.get("bg_color", ""),
    }
    return data


def db_get_task(task_id: int) -> dict | None:
    from local_db import local_get_task
    return local_get_task(task_id)


def db_get_subtask(sub_id: int) -> dict | None:
    from local_db import local_get_subtask
    return local_get_subtask(sub_id)


def db_get_subtask_parent(sub_id: int) -> int | None:
    from local_db import local_get_subtask_parent
    return local_get_subtask_parent(sub_id)


def db_get_project_for_task(task_id: int) -> str | None:
    from local_db import local_get_project_for_task
    return local_get_project_for_task(task_id)


# ---------------------------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------------------------

def db_add_project(name: str, color: str) -> bool:
    from local_db import local_add_project
    return local_add_project(name, color)


def db_edit_project(old_name: str, new_name: str | None, new_color: str | None) -> bool:
    from local_db import local_update_project
    try:
        local_update_project(old_name, new_name, new_color)
        return True
    except Exception:
        return False


def db_delete_project(name: str) -> None:
    from local_db import local_delete_project
    local_delete_project(name)


# ---------------------------------------------------------------------------
# TASKS
# ---------------------------------------------------------------------------

def db_add_task(project: str, task: str, priority: str, status: str, notes: str | None) -> int:
    from local_db import local_add_task
    return local_add_task(project, task, priority, status, notes)


def db_update_task(task_id: int, task: str, priority: str, status: str, notes: str | None) -> None:
    from local_db import local_update_task
    local_update_task(task_id, task, priority, status, notes)


def db_delete_task(task_id: int) -> None:
    from local_db import local_delete_task
    local_delete_task(task_id)


# ---------------------------------------------------------------------------
# SUB-TASKS
# ---------------------------------------------------------------------------

def db_add_subtask(task_id: int, task: str, status: str, notes: str | None) -> int:
    from local_db import local_add_subtask
    return local_add_subtask(task_id, task, status, notes)


def db_update_subtask(sub_id: int, task: str, status: str, notes: str | None) -> None:
    from local_db import local_update_subtask
    local_update_subtask(sub_id, task, status, notes)


def db_delete_subtask(sub_id: int) -> None:
    from local_db import local_delete_subtask
    local_delete_subtask(sub_id)


# ---------------------------------------------------------------------------
# PROJECT LOGS
# ---------------------------------------------------------------------------

def db_get_project_logs(project: str) -> list[dict]:
    from local_db import local_get_project_logs
    return local_get_project_logs(project)


def db_get_log_by_id(log_id: int) -> dict | None:
    from local_db import local_get_log_by_id
    return local_get_log_by_id(log_id)


def db_add_project_log(project: str, log_date: str, title: str, notes: str) -> int:
    from local_db import local_add_project_log
    return local_add_project_log(project, log_date, title, notes)


def db_update_project_log(log_id: int, log_date: str, title: str, notes: str) -> None:
    from local_db import local_update_project_log
    local_update_project_log(log_id, log_date, title, notes)


def db_delete_project_log(log_id: int) -> None:
    from local_db import local_delete_project_log
    local_delete_project_log(log_id)
