import sqlite3
import threading
from datetime import datetime, timezone

from .models import Category, Classification, Priority, Status, Ticket


class TicketRepository:
    """Small SQLite-backed store. Swap for PostgreSQL by changing this class only."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    @staticmethod
    def _to_ticket(row: sqlite3.Row) -> Ticket:
        return Ticket(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            category=row["category"],
            priority=row["priority"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def create(self, title: str, body: str, classification: Classification) -> Ticket:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO tickets (title, body, category, priority, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    title,
                    body,
                    classification.category.value,
                    classification.priority.value,
                    Status.open.value,
                    now,
                ),
            )
            self._conn.commit()
            ticket_id = cursor.lastrowid
        return self.get(ticket_id)

    def get(self, ticket_id: int):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
        return self._to_ticket(row) if row else None

    def list(self, category=None, priority=None, status=None) -> list[Ticket]:
        query, params = "SELECT * FROM tickets WHERE 1=1", []
        for column, value in (("category", category), ("priority", priority), ("status", status)):
            if value is not None:
                query += f" AND {column} = ?"
                params.append(value.value)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._to_ticket(row) for row in rows]

    def update_status(self, ticket_id: int, status: Status):
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE tickets SET status = ? WHERE id = ?", (status.value, ticket_id)
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                return None
        return self.get(ticket_id)

    def stats(self) -> dict:
        def count_by(column: str, enum_cls) -> dict:
            with self._lock:
                rows = self._conn.execute(
                    f"SELECT {column} AS key, COUNT(*) AS n FROM tickets GROUP BY {column}"
                ).fetchall()
            counts = {member.value: 0 for member in enum_cls}
            counts.update({row["key"]: row["n"] for row in rows})
            return counts

        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        return {
            "total": total,
            "by_category": count_by("category", Category),
            "by_priority": count_by("priority", Priority),
            "by_status": count_by("status", Status),
        }
