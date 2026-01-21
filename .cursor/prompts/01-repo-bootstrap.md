You are an exacting repo bootstrap agent.

## Goal
Turn the current single-file prototype (`rss_dash.py`) into a clean, minimal repository structure without changing runtime behavior.

## Constraints
- Minimal diffs. Do not refactor logic.
- Do not introduce new dependencies.
- Keep the app runnable as: `python rss_dash.py`
- Keep DB schema and extraction behavior identical.

## Tasks
1. Create a conventional repo layout:
   - `rss_dash.py` remains the entrypoint.
   - Add `src/` directory and move implementation modules into:
     - `src/db.py` (schema + db helpers)
     - `src/rules.py` (TOPIC_RULES, cue lists, classifiers)
     - `src/ingest.py` (fetch_once, fetch_loop)
     - `src/web.py` (Flask app, routes, template)
   - `rss_dash.py` should import from these modules and remain thin.

2. Add supporting files:
   - `requirements.txt` (already defined)
   - `.gitignore` for Python + SQLite (`rss_dash.sqlite3`, `*.db`, `.venv`, `__pycache__`)
   - `README.md` placeholder (detailed runbook will come later)
   - `LICENSE` placeholder (MIT unless repo already specifies otherwise)

3. Ensure the app still works:
   - `python rss_dash.py` starts on localhost.
   - Dashboard loads.
   - Manual fetch works.
   - Background loop works.

## Output
Provide:
- A short summary of the file tree changes
- A diff-friendly commit plan (1–2 commits max)
- Any minor adjustments needed in imports or package init files (e.g., `src/__init__.py`)

Do not:
- Change routes, HTML, or CSS behavior.
- Change extraction rules or SQL schema.
