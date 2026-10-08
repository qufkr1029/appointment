import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from appointment.models import Appointment

STATUSES = {"pending", "completed", "deleted"}
STATUS_ORDER = {
    "pending": "scheduled_at ASC, id ASC",
    "completed": "completed_at DESC, id DESC",
    "deleted": "completed_at DESC, id DESC",
}

APPOINTMENT_COLUMNS_SQL = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'deleted')),
    deleted_from_status TEXT CHECK (deleted_from_status IN ('pending', 'completed')),
    deleted_alerted_at TEXT,
    alerted_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (status = 'pending' AND completed_at IS NULL)
        OR (status = 'completed' AND completed_at IS NOT NULL)
        OR status = 'deleted'
    )
)
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.astimezone()
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class AppointmentRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f"CREATE TABLE IF NOT EXISTS appointment {APPOINTMENT_COLUMNS_SQL}")
            table_sql, columns = self._table_definition(connection)
            if "'deleted'" not in table_sql:
                # SQLite는 CHECK 제약 조건을 직접 바꿀 수 없어 기존 테이블을 다시 만듭니다.
                self._migrate_status_check(connection)
                _, columns = self._table_definition(connection)
            if "deleted_from_status" not in columns:
                connection.execute(
                    "ALTER TABLE appointment ADD COLUMN deleted_from_status TEXT "
                    "CHECK (deleted_from_status IN ('pending', 'completed'))"
                )
            if "deleted_alerted_at" not in columns:
                connection.execute("ALTER TABLE appointment ADD COLUMN deleted_alerted_at TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_appointment_status_scheduled "
                "ON appointment (status, scheduled_at)"
            )

    @staticmethod
    def _table_definition(connection: sqlite3.Connection) -> tuple[str, set[str]]:
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'appointment'"
        ).fetchone()["sql"]
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(appointment)")}
        return table_sql, columns

    @staticmethod
    def _migrate_status_check(connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("ALTER TABLE appointment RENAME TO appointment_old")
        connection.execute(f"CREATE TABLE appointment {APPOINTMENT_COLUMNS_SQL}")
        connection.execute(
            """
            INSERT INTO appointment
                (id, title, scheduled_at, status, deleted_from_status,
                 deleted_alerted_at, alerted_at, completed_at, created_at, updated_at)
            SELECT id, title, scheduled_at, status, NULL, NULL, alerted_at,
                   completed_at, created_at, updated_at
            FROM appointment_old
            """
        )
        connection.execute("DROP TABLE appointment_old")
        connection.commit()
        connection.execute("PRAGMA foreign_keys = ON")

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Appointment:
        return Appointment(
            id=row["id"],
            title=row["title"],
            scheduled_at=parse_datetime(row["scheduled_at"]),
            status=row["status"],
            alerted_at=parse_datetime(row["alerted_at"]),
            completed_at=parse_datetime(row["completed_at"]),
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def list_by_status(self, status: str) -> list[Appointment]:
        if status not in STATUSES:
            raise ValueError("status must be 'pending', 'completed', or 'deleted'")
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM appointment WHERE status = ? ORDER BY {STATUS_ORDER[status]}",
                (status,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, appointment_id: int) -> Appointment | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM appointment WHERE id = ?", (appointment_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def create(self, title: str, scheduled_at: datetime) -> int:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO appointment
                    (title, scheduled_at, status, alerted_at, completed_at, created_at, updated_at)
                VALUES (?, ?, 'pending', NULL, NULL, ?, ?)
                """,
                (title.strip(), serialize_datetime(scheduled_at), now, now),
            )
            return int(cursor.lastrowid)

    def update(self, appointment_id: int, title: str, scheduled_at: datetime) -> None:
        now = serialize_datetime(utc_now())
        new_time = serialize_datetime(scheduled_at)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT status, scheduled_at FROM appointment WHERE id = ?",
                (appointment_id,),
            ).fetchone()
            if existing is None:
                raise LookupError("일정을 찾을 수 없습니다.")

            schedule_changed = existing["scheduled_at"] != new_time
            reset_alert = schedule_changed and existing["status"] == "pending"
            connection.execute(
                """
                UPDATE appointment
                SET title = ?, scheduled_at = ?,
                    alerted_at = CASE WHEN ? THEN NULL ELSE alerted_at END,
                    updated_at = ?
                WHERE id = ?
                """,
                (title.strip(), new_time, reset_alert, now, appointment_id),
            )

    def complete(self, appointment_ids: list[int]) -> None:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            connection.executemany(
                """
                UPDATE appointment
                SET status = 'completed', completed_at = ?, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                [(now, now, appointment_id) for appointment_id in appointment_ids],
            )

    def restore(self, appointment_ids: list[int]) -> None:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            connection.executemany(
                """
                UPDATE appointment
                SET status = 'pending', completed_at = NULL, updated_at = ?
                WHERE id = ? AND status = 'completed'
                """,
                [(now, appointment_id) for appointment_id in appointment_ids],
            )

    def restore_deleted(self, appointment_ids: list[int]) -> None:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            # 이전 상태를 복구하고, 지난 일정 알림이 곧바로 반복되지 않게 합니다.
            connection.executemany(
                """
                UPDATE appointment
                SET status = COALESCE(deleted_from_status, 'pending'),
                    completed_at = CASE
                        WHEN deleted_from_status = 'completed' THEN completed_at
                        ELSE NULL
                    END,
                    alerted_at = CASE
                        WHEN scheduled_at <= ? THEN COALESCE(deleted_alerted_at, ?)
                        ELSE deleted_alerted_at
                    END,
                    deleted_from_status = NULL,
                    deleted_alerted_at = NULL,
                    updated_at = ?
                WHERE id = ? AND status = 'deleted'
                """,
                [(now, now, now, appointment_id) for appointment_id in appointment_ids],
            )

    def delete(self, appointment_ids: list[int]) -> None:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            # 복구할 수 있도록 삭제 전 상태와 알림 기록을 보존합니다.
            connection.executemany(
                """
                UPDATE appointment
                SET deleted_from_status = status, deleted_alerted_at = alerted_at,
                    status = 'deleted', updated_at = ?
                WHERE id = ? AND status != 'deleted'
                """,
                [(now, appointment_id) for appointment_id in appointment_ids],
            )

    def permanently_delete(self, appointment_ids: list[int]) -> None:
        with self._connect() as connection:
            connection.executemany(
                "DELETE FROM appointment WHERE id = ? AND status = 'deleted'",
                [(appointment_id,) for appointment_id in appointment_ids],
            )

    def mark_alert_dismissed(self, appointment_id: int) -> None:
        now = serialize_datetime(utc_now())
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE appointment
                SET alerted_at = ?, updated_at = ?
                WHERE id = ? AND status = 'pending' AND alerted_at IS NULL
                """,
                (now, now, appointment_id),
            )

    def snooze_alert(self, appointment_id: int, minutes: int = 5) -> None:
        now = utc_now()
        new_scheduled_at = serialize_datetime(now + timedelta(minutes=minutes))
        with self._connect() as connection:
            connection.execute(
                """
                -- 기존 일정 시각을 미루고 알림 여부를 초기화합니다.
                UPDATE appointment
                SET scheduled_at = ?, alerted_at = NULL, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (new_scheduled_at, serialize_datetime(now), appointment_id),
            )

    def list_due_unalerted(self, now: datetime | None = None) -> list[Appointment]:
        cutoff = serialize_datetime(now or utc_now())
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM appointment
                WHERE status = 'pending'
                  AND alerted_at IS NULL
                  AND scheduled_at <= ?
                ORDER BY scheduled_at ASC, id ASC
                """,
                (cutoff,),
            ).fetchall()
        return [self._from_row(row) for row in rows]
