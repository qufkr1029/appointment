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
        on_snooze: Callable[[], None],
    ):
        super().__init__(parent)
        self._on_dismiss = on_dismiss
        self._on_show_list = on_show_list
        self._on_snooze = on_snooze
        self._closed = False
        self._focused_button = "confirm"

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
        ttk.Checkbutton(
            body,
            text="5분 후 다시 알림",
            command=self.snooze,
            style="Dialog.TCheckbutton",
        ).pack(anchor="w", pady=(0, 16))

        buttons = ttk.Frame(body)
        buttons.pack(anchor="e")
        self.list_button = ttk.Button(buttons, text="목록 보기", command=self.show_list)
        self.list_button.pack(side="left", padx=(0, 8))
        self.confirm_button = ttk.Button(buttons, text="확인", command=self.close)
        self.confirm_button.pack(side="left")

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
        if self._focused_button == "list":
            self.show_list()
        else:
            self.close()
        return "break"

    def _on_escape(self, _event=None):
        self.close()
        return "break"

    def _on_tab(self, _event=None):
        self._set_button_focus("confirm" if self._focused_button == "list" else "list")
        return "break"

    def _set_button_focus(self, name):
        self._focused_button = name
        button = self.list_button if name == "list" else self.confirm_button
        button.focus_set()

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
        self._finish(self._on_snooze)

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
