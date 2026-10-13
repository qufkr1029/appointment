from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from appointment.models import Appointment
from appointment.ui.window_utils import center_on_screen


class AlertDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        appointment: Appointment,
        on_dismiss: Callable[[], None],
        on_show_list: Callable[[], None],
        on_snooze: Callable[[int], None],
    ):
        super().__init__(parent)
        self._on_dismiss = on_dismiss
        self._on_show_list = on_show_list
        self._on_snooze = on_snooze
        self._closed = False
        self._focused_control = "confirm"

        self.title("일정 알림")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Return>", self._on_enter)
        self.bind("<Escape>", self._on_escape)
        self.bind("<Tab>", self._on_tab)
        self.bind("<Shift-Tab>", self._on_tab)
        self.attributes("-topmost", True)

        body = ttk.Frame(self, padding=24, style="App.TFrame")
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="일정 알림", font=("Malgun Gothic", 17, "bold")).pack(
            anchor="w", pady=(0, 12)
        )
        ttk.Label(
            body,
            text=appointment.title,
            font=("Malgun Gothic", 13, "bold"),
            wraplength=360,
        ).pack(anchor="w")
        ttk.Label(
            body,
            text=appointment.local_scheduled_at.strftime("%Y년 %m월 %d일 %H:%M"),
            foreground="#68707C",
        ).pack(anchor="w", pady=(8, 14))
        snooze_options = {"5분": 5, "10분": 10, "30분": 30, "1시간": 60}
        self.snooze_var = tk.StringVar(value="5분")
        snooze_row = ttk.Frame(body)
        snooze_row.pack(anchor="w", fill="x", pady=(0, 16))
        ttk.Label(snooze_row, text="다시 알림 간격").pack(side="left", padx=(0, 8))
        self.snooze_combo = ttk.Combobox(
            snooze_row,
            textvariable=self.snooze_var,
            values=tuple(snooze_options),
            state="readonly",
            width=8,
        )
        self.snooze_combo.pack(side="left")
        self.snooze_combo.bind("<<ComboboxSelected>>", self._on_snooze_selected)
        self._snooze_options = snooze_options

        buttons = ttk.Frame(body)
        buttons.pack(anchor="e")
        self.list_button = ttk.Button(buttons, text="목록 보기", command=self.show_list)
        self.list_button.pack(side="left", padx=(0, 8))
        self.confirm_button = ttk.Button(buttons, text="확인", command=self.close)
        self.confirm_button.pack(side="left")
        self._focus_order = ["list", "snooze_combo", "confirm"]
        self._focus_controls = {
            "list": self.list_button,
            "snooze_combo": self.snooze_combo,
            "confirm": self.confirm_button,
        }

        self.update_idletasks()
        self.geometry(f"420x{max(225, body.winfo_reqheight())}")
        center_on_screen(self)
        self.grab_set()
        self.lift()
        self.focus_force()
        self._set_button_focus("confirm")
        self.after(250, self._release_topmost)

    def _release_topmost(self):
        if self.winfo_exists():
            self.attributes("-topmost", False)

    def _on_enter(self, _event=None):
        if self._focused_control == "list":
            self.show_list()
        else:
            self.close()
        return "break"

    def _on_escape(self, _event=None):
        self.close()
        return "break"

    def _on_tab(self, _event=None):
        current = self._focus_order.index(self._focused_control)
        direction = -1 if _event is not None and _event.state & 0x1 else 1
        self._set_button_focus(self._focus_order[(current + direction) % len(self._focus_order)])
        return "break"

    def _set_button_focus(self, name):
        self._focused_control = name
        self._focus_controls[name].focus_set()

    def show_list(self):
        if self._closed:
            return
        self._finish(self._on_dismiss, self._on_show_list)

    def close(self):
        if self._closed:
            return
        self._finish(self._on_dismiss)

    def snooze(self):
        if self._closed:
            return
        minutes = self._snooze_options[self.snooze_var.get()]
        self._finish(lambda: self._on_snooze(minutes))

    def _on_snooze_selected(self, _event=None):
        self.snooze()
        return "break"

    def _finish(self, *callbacks: Callable[[], None]) -> None:
        self._closed = True
        self.grab_release()
        self.destroy()
        for callback in callbacks:
            callback()

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
