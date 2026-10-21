import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_concurrent_database_initialization_is_safe(tmp_path: Path) -> None:
    database_path = tmp_path / "concurrent.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    command = [
        sys.executable,
        "-c",
        "from app.services import initialize_database; initialize_database()",
    ]
    project_root = Path(__file__).resolve().parents[1]
    processes = [
        subprocess.Popen(
            command,
            cwd=project_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]

    results = [process.communicate(timeout=30) for process in processes]
    assert [process.returncode for process in processes] == [0, 0], results

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tasks").fetchone() == (3,)
        assert connection.execute("SELECT COUNT(*) FROM user_preferences").fetchone() == (1,)
