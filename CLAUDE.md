# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tasky Local: a single-user, single-machine, fully offline task manager for the terminal. Fork of `task` (the Supabase-backed multi-user version) with the entire cloud/auth/sync layer removed.

## Running the app

```bash
python sqtask.py
```

No login screen — the app opens directly into the task table. Data lives at `~/.tasky_local/tasky.db`; view preferences at `~/.tasky_local/config.json`.

## Dependencies

```bash
pip install -r requirements.txt
```

Only dependency: `textual==7.4.0`. No `supabase` package, no network access anywhere in the app.

Requires Python 3.10 or newer (the codebase uses `X | None` type annotations that need 3.10+).

## File structure

```
local_tasky/
├── sqtask.py     # Entry point (3-line wrapper)
├── app.py        # TaskManagerApp + table rendering helpers + entry point
├── screens.py    # All Screen and ModalScreen classes
├── db.py         # Public db_* API — thin synchronous wrapper over local_db
├── local_db.py   # SQLite layer (~/.tasky_local/tasky.db)
├── config.py     # Local config file management (~/.tasky_local/config.json)
├── styles.tcss   # Textual CSS
└── requirements.txt
```

## Architecture

SQLite is the only store — no remote, no sync, no threads writing in the background. `local_db.py` implements the CRUD; `db.py` is a thin pass-through the rest of the app imports (kept as its own module so the wrapper boundary matches the original `task` project's conventions, even though today it does no orchestration).

Data model — four tables, no `users`:

| Table | Key columns |
|---|---|
| `projects` | `name PK`, `color` |
| `tasks` | `id`, `project FK`, `task`, `priority`, `status`, `notes`, `sort_order` |
| `sub_tasks` | `id`, `task_id FK`, `task`, `status`, `notes`, `sort_order` |
| `project_logs` | `id`, `project FK`, `log_date`, `title`, `notes` |

`id` columns are SQLite `AUTOINCREMENT` — there is no external source of truth to defer to, unlike the Supabase-backed version.

`view_settings` (sort, filters, theme, colors) live in `~/.tasky_local/config.json`, not in the database.

### Screen stack

`TaskManagerApp` owns the root screen. Navigation uses `push_screen` / `pop_screen`:

| Screen | Purpose |
|---|---|
| `SplashScreen` | Startup animation |
| `TaskManagerApp` | Main task list (DataTable) |
| `ProjectLogScreen` | Full-screen milestone log for a project |
| `TaskFormScreen` | Modal — add/edit task or sub-task (no assignee field) |
| `ProjectManagerScreen` | Modal — create/rename/delete projects |
| `ViewFilterScreen` | Modal — sort and filter options |
| `PreferencesScreen` | Modal — border and background color |
| `LogFormScreen` | Modal — add/edit/delete a log entry |
| `LogDetailScreen` | Modal — read-only view of a log entry |
| `ConfirmScreen` | Modal — generic yes/no confirmation |
| `HelpScreen` | Modal — keybinding reference |
| `UpdateGuideScreen` | Modal — in-app manual |

### Row keys

The main DataTable encodes type and DB id into row keys: `task::<id>` (a task row), `sub::<id>` (a sub-task row, indented under its parent when expanded). `ProjectLogScreen` uses `log::<id>` and `note::<id>`.

### Reactive state

`TaskManagerApp` has two reactive attributes (`app_border`, `app_bg`) that propagate border/background colors to all widgets and persist to local config via their `watch_*` methods.

## Keybindings

| Shortcut | Action |
|---|---|
| `ctrl+o` | Manage projects |
| `ctrl+n` | New task |
| `ctrl+s` | New sub-task |
| `ctrl+e` | Edit task/sub-task |
| `ctrl+d` | Delete task/sub-task |
| `ctrl+f` | Filters / view |
| `ctrl+k` | Toggle hide DONE |
| `ctrl+w` | Focus mode (filters the table to IN PROGRESS only) |
| `ctrl+down` | Expand all tasks (sub-tasks) |
| `ctrl+up` | Collapse all tasks |
| `ctrl+p` | Preferences |
| `ctrl+l` | Project log (while on a task) |
| `ctrl+u` | Manual (in-app) |
| `ctrl+q` | Quit |
| `?` | Help |

**Log screen only:** `ctrl+a` add entry, `ctrl+r` edit entry, `escape` back.

## Schema changes

There is no remote schema — everything lives in `local_db.py`'s `init_db()`. To add a column or table: edit the `CREATE TABLE` statements there, and note that existing users' `~/.tasky_local/tasky.db` won't pick up a new column automatically (SQLite's `CREATE TABLE IF NOT EXISTS` is a no-op on an existing table) — add an `ALTER TABLE` migration in `init_db()` if that ever matters, following the pattern the original `task` project used in its own `_migrate_schema`.
