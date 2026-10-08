from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk

from appointment.data.appointment_repository import AppointmentRepository
from appointment.models import Appointment
from appointment.ui.window_utils import center_window


class AppointmentDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        repository: AppointmentRepository,
        on_saved: Callable[[], None],
        appointment: Appointment | None = None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.on_saved = on_saved
        self.appointment = appointment
        self._closed = False

        self.title("일정 수정" if appointment else "새 일정")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Return>", self._on_enter)
        self.bind("<Escape>", self._on_escape)
        self.grid_columnconfigure(0, weight=1)

        body = ttk.Frame(self, padding=24, style="App.TFrame")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        heading = "일정 수정" if appointment else "새 일정"
        ttk.Label(body, text=heading, font=("Malgun Gothic", 18, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 20)
        )
        ttk.Label(body, text="제목").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.title_entry = ttk.Entry(body, width=42)
        self.title_entry.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        if appointment:
            self.title_entry.insert(0, appointment.title)

        if appointment:
            local_time = appointment.local_scheduled_at
        else:
            local_time = datetime.now().astimezone() + timedelta(minutes=5)
        fields = ttk.Frame(body)
        fields.grid(row=3, column=0, sticky="w", pady=(0, 16))
        ttk.Label(fields, text="시간 (24시간제)").grid(row=0, column=0, sticky="w")
        ttk.Label(fields, text="날짜 (YYYYMMDD)").grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.time_entry = ttk.Entry(fields, width=12)
        self.time_entry.insert(0, local_time.strftime("%H:%M"))
        self.time_entry.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.date_entry = ttk.Entry(fields, width=16)
        self.date_entry.insert(0, local_time.strftime("%Y-%m-%d"))
        self.date_entry.grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(6, 0))
        self.title_entry.bind("<Tab>", self._focus_time)
        self.time_entry.bind("<Tab>", self._focus_date)
        self.date_entry.bind("<Tab>", self._focus_title_from_date)
        self.title_entry.bind("<Shift-Tab>", self._focus_date)
        self.time_entry.bind("<Shift-Tab>", self._focus_title)
        self.date_entry.bind("<Shift-Tab>", self._focus_time)

        self.error_label = ttk.Label(body, text="", foreground="#B42318", wraplength=380)
        self.error_label.grid(row=4, column=0, sticky="w", pady=(0, 12))
        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, sticky="e")
        ttk.Button(buttons, text="취소", command=self.cancel).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="저장", command=self.save).pack(side="left")

        self.update_idletasks()
        self.geometry(f"440x{max(300, body.winfo_reqheight())}")
        center_window(self, parent)
        self.grab_set()
        self.after(80, self._focus_title)

    def _focus_title(self):
        if self.winfo_exists():
            self.title_entry.focus_set()
            self.title_entry.icursor("end")

    def _on_enter(self, _event=None):
        self.save()
        return "break"

    def _on_escape(self, _event=None):
        self.cancel()
        return "break"

    def _focus_time(self, _event=None):
        self.time_entry.focus_set()
        if self.appointment is not None:
            self.time_entry.after_idle(self.time_entry.select_range, 0, "end")
        return "break"

    def _focus_date(self, _event=None):
        self.date_entry.focus_set()
        return "break"

    def _focus_title_from_date(self, _event=None):
        self.title_entry.focus_set()
        return "break"

    def _scheduled_datetime(self) -> datetime:
        date_text = self.date_entry.get().strip()
        # 숫자만 입력한 날짜도 받아 표준 날짜 형식으로 변환합니다.
        if len(date_text) == 8 and date_text.isdigit():
            date_text = f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:]}"
        selected_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        time_text = self.time_entry.get().strip()
        if len(time_text) == 4 and time_text.isdigit():
            time_text = f"{time_text[:2]}:{time_text[2:]}"
        selected_time = datetime.strptime(time_text, "%H:%M").time()
        local_value = datetime.combine(selected_date, selected_time)
        return local_value.astimezone(timezone.utc).replace(microsecond=0)

    def save(self):
        title = self.title_entry.get().strip()
        if not title:
            self.error_label.configure(text="제목을 입력해 주세요.")
            self.title_entry.focus_set()
            return

        try:
            scheduled_at = self._scheduled_datetime()
        except (ValueError, TypeError):
            self.error_label.configure(
                text=(
                    "날짜는 YYYYMMDD 또는 YYYY-MM-DD, 시간은 HHMM 또는 HH:MM "
                    "형식으로 입력해 주세요."
                )
            )
            self.date_entry.focus_set()
            return

        validation_error = self._schedule_validation_error(scheduled_at)
        if validation_error:
            self.error_label.configure(text=validation_error)
            return

        self._save_appointment(title, scheduled_at)

    def _schedule_validation_error(self, scheduled_at: datetime) -> str | None:
        if scheduled_at > datetime.now(timezone.utc):
            return None
        if self.appointment is None:
            return "지난 시각은 새 일정으로 등록할 수 없습니다."
        same_time = scheduled_at == self.appointment.scheduled_at
        if not same_time and not self.appointment.is_completed:
            return "미완료 일정의 새 예정 시각은 미래여야 합니다."
        return None

    def _save_appointment(self, title: str, scheduled_at: datetime):
        try:
            if self.appointment is None:
                self.repository.create(title, scheduled_at)
            else:
                self.repository.update(self.appointment.id, title, scheduled_at)
        except (OSError, LookupError, ValueError) as error:
            self.error_label.configure(text=f"저장하지 못했습니다: {error}")
            return
        self.close()
        self.on_saved()

    def cancel(self):
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.grab_release()
        self.destroy()
