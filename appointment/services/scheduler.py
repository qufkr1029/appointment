from collections import deque
from collections.abc import Callable
import tkinter as tk

from appointment.data.appointment_repository import AppointmentRepository
from appointment.models import Appointment
from appointment.ui.alert_dialog import AlertDialog


class Scheduler:
    def __init__(
        self,
        root: tk.Tk,
        repository: AppointmentRepository,
        on_show_list: Callable[[], None],
        on_snoozed: Callable[[], None] | None = None,
        interval_ms: int = 1000,
    ):
        self.root = root
        self.repository = repository
        self.on_show_list = on_show_list
        self.on_snoozed = on_snoozed or (lambda: None)
        self.interval_ms = interval_ms
        self._queue: deque[int] = deque()
        # 주기적으로 확인해도 같은 알림이 중복 등록되지 않게 합니다.
        self._queued_ids: set[int] = set()
        self._active_dialog: AlertDialog | None = None
        self._running = False
        self._poll_after_id = None

    def start(self) -> None:
        self._running = True
        self._poll()

    def stop(self) -> None:
        self._running = False
        if self._poll_after_id is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        if self._active_dialog is not None:
            self._active_dialog.shutdown()
            self._active_dialog = None

    def _poll(self) -> None:
        if not self._running:
            return

        try:
            for appointment in self.repository.list_due_unalerted():
                if appointment.id not in self._queued_ids:
                    self._queue.append(appointment.id)
                    self._queued_ids.add(appointment.id)
            self._show_next()
        finally:
            if self._running:
                self._poll_after_id = self.root.after(self.interval_ms, self._poll)

    def _show_next(self) -> None:
        if self._active_dialog is not None:
            return

        while self._queue:
            appointment_id = self._queue.popleft()
            appointment = self.repository.get(appointment_id)
            if (
                appointment is None
                or appointment.status != "pending"
                or appointment.alerted_at is not None
            ):
                self._queued_ids.discard(appointment_id)
                continue
            self._present(appointment)
            return

    def _present(self, appointment: Appointment) -> None:
        self._active_dialog = AlertDialog(
            self.root,
            appointment,
            on_dismiss=lambda: self._dismiss(appointment.id),
            on_show_list=self.on_show_list,
            on_snooze=lambda: self._snooze(appointment.id),
        )

    def _dismiss(self, appointment_id: int) -> None:
        self.repository.mark_alert_dismissed(appointment_id)
        self._finish_alert(appointment_id)

    def _snooze(self, appointment_id: int) -> None:
        self.repository.snooze_alert(appointment_id)
        self.on_snoozed()
        self._finish_alert(appointment_id)

    def _finish_alert(self, appointment_id: int) -> None:
        self._queued_ids.discard(appointment_id)
        self._active_dialog = None
        self._show_next()
