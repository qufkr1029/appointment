from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Appointment:
    id: int
    title: str
    scheduled_at: datetime
    status: str
    alerted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def local_scheduled_at(self) -> datetime:
        return self.scheduled_at.astimezone()
