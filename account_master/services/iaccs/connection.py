"""Read-only MySQL connection for the iAccs core-banking source.

Connection settings resolve from the ``MYSQL56_*`` environment convention
(the same convention used by the URBD analysis scripts ``mysql56.py``):

    MYSQL56_HOST  (default 127.0.0.1)
    MYSQL56_PORT  (default 3306)
    MYSQL56_USER  (default root)
    MYSQL56_PASS  (default empty)
    MYSQL56_DB    (default: no database selected)

A ``.env`` file in the repository root is loaded for any variable not already
set. Every statement executed through :func:`query` is guarded to be read
only; the importer never issues writes against the source database.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import pymysql
from pymysql.cursors import DictCursor

ENV_FILE = ".env"

#: Statements that would modify the source database. Detected on whole words
#: only, so a column merely containing a keyword (e.g. ``UPDATED_BY``) does
#: not trip the guard.
WRITE_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "RENAME",
    "LOAD",
    "CALL",
    "LOCK",
    "UNLOCK",
    "OPTIMIZE",
    "REPAIR",
    "FLUSH",
    "KILL",
)
_WRITE_PATTERN = re.compile(r"\b(" + "|".join(WRITE_KEYWORDS) + r")\b")


def _load_env(path: str = ENV_FILE) -> None:
    """Load ``KEY=value`` lines from *path* into ``os.environ``.

    Existing environment variables win. Values are never printed, so
    credentials stay out of logs and transcripts.
    """
    if not path or not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if key not in os.environ:
                os.environ[key] = value


def connection_settings() -> Dict[str, Any]:
    """Resolve the MySQL connection settings from the environment."""
    _load_env()
    return {
        "host": os.environ.get("MYSQL56_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL56_PORT", 3306)),
        "user": os.environ.get("MYSQL56_USER", "root"),
        "password": os.environ.get("MYSQL56_PASS", ""),
        "database": os.environ.get("MYSQL56_DB") or None,
    }


def get_connection():
    """Open a read-only connection to the iAccs MySQL database."""
    return pymysql.connect(
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        **connection_settings(),
    )


def _is_read_only(sql: str) -> bool:
    """Return True if *sql* contains no write-statement keyword."""
    first = sql.lstrip()
    if not first[:6].upper().startswith("SELECT") and not first.upper().startswith(
        ("SHOW", "DESCRIBE", "EXPLAIN")
    ):
        return False
    return _WRITE_PATTERN.search(sql) is None


def query(conn, sql: str, params: Any = None) -> List[Dict[str, Any]]:
    """Execute a read-only statement and return rows as dicts.

    Raises ``ValueError`` when *sql* is not read-only, so the importer cannot
    accidentally mutate the source database.
    """
    if not _is_read_only(sql):
        raise ValueError(
            "Refusing non read-only statement against the iAccs source database"
        )
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())