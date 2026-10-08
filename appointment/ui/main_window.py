from collections.abc import Callable
from datetime import datetime
import tkinter as tk
from tkinter import ttk

from appointment.data.appointment_repository import AppointmentRepository
from appointment.models import Appointment
from appointment.ui.appointment_dialog import AppointmentDialog
from appointment.ui.window_utils import center_window


class MainWindow:
    BG = "#F5F6F8"
    SURFACE = "#FFFFFF"
    TEXT = "#20242B"
    MUTED = "#68707C"
    ACCENT = "#315EFB"

    def __init__(
        self,
        root: tk.Tk,
        repository: AppointmentRepository,
        on_hide: Callable[[], None],
    ):
        self.root = root
        self.repository = repository
        self.on_hide = on_hide
        self.current_status = "pending"
        self.appointments: list[Appointment] = []
        self.search_query = ""
        self.selected_ids: set[int] = set()
        self._checkbox_vars: dict[int, tk.BooleanVar] = {}
        self._sort_descending = True

        self._configure_styles()
        self.root.title("일정 알림")
        self.root.geometry("980x700")
        self.root.minsize(760, 520)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_hide)
        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<F5>", self._on_refresh_key)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        content = ttk.Frame(root, padding=24, style="App.TFrame")
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)

        self._select_all_var = tk.BooleanVar(value=False)
        self._build_header(content)
        self._build_toolbar(content)
        self._build_search_controls(content)
        self._build_list_area(content)
        self.refresh()

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="일정", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.add_button = ttk.Button(
            header, text="+ 일정 추가", command=self._add_appointment, style="Accent.TButton"
        )
        self.add_button.grid(row=0, column=1, sticky="e")

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="App.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        toolbar.grid_columnconfigure(0, weight=1)
        view_group = ttk.LabelFrame(
            toolbar, text="목록 보기", padding=(8, 5), style="Group.TLabelframe"
        )
        view_group.grid(row=0, column=0, sticky="w")
        views = ttk.Frame(view_group, style="App.TFrame")
        views.pack()
        self.view_buttons = {}
        view_options = (
            ("예정 목록", "pending"),
            ("완료 목록", "completed"),
            ("삭제 목록", "deleted"),
        )
        for label, status in view_options:
            button = ttk.Button(
                views, text=label, command=lambda value=status: self._change_view(value)
            )
            button.pack(side="left", padx=(0, 6))
            self.view_buttons[status] = button

        action_group = ttk.LabelFrame(
            toolbar, text="선택한 일정 작업", padding=(8, 5), style="Group.TLabelframe"
        )
        action_group.grid(row=0, column=1, sticky="e")
        self.selection_label = ttk.Label(action_group, text="", style="Muted.TLabel")
        self.selection_label.pack(side="left", padx=(0, 8))
        actions = ttk.Frame(action_group, style="App.TFrame")
        actions.pack(side="left")
        self.edit_button = self._action_button(actions, "수정", self._edit_selected)
        self.complete_button = self._action_button(actions, "완료 처리", self._complete_selected)
        self.restore_button = self._action_button(actions, "복구", self._restore_selected)
        self.delete_button = self._action_button(actions, "삭제", self._delete_selected)
        for button in (
            self.edit_button,
            self.complete_button,
            self.restore_button,
            self.delete_button,
        ):
            button.pack(side="left", padx=(0, 6))

    def _build_search_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent, style="App.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure(1, weight=1)
        ttk.Label(controls, text="검색", style="Muted.TLabel").grid(
            row=0, column=0, padx=(0, 8)
        )
        self.search_entry = ttk.Entry(controls)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self.search_entry.bind("<Return>", self._on_search)
        self.sort_switch = ttk.Combobox(
            controls, state="readonly", width=13, values=("날짜 오름차순", "날짜 내림차순")
        )
        self.sort_switch.set("날짜 내림차순")
        self.sort_switch.grid(row=0, column=2, sticky="e")
        self.sort_switch.bind("<<ComboboxSelected>>", self._change_sort)

    def _build_list_area(self, parent: ttk.Frame) -> None:
        list_outer = ttk.Frame(parent, style="List.TFrame")
        list_outer.grid(row=3, column=0, sticky="nsew")
        list_outer.grid_columnconfigure(0, weight=1)
        list_outer.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            list_outer, background=self.SURFACE, highlightthickness=0, borderwidth=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.list_frame = ttk.Frame(self.canvas, style="List.TFrame")
        self._list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_list)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.list_frame.grid_columnconfigure(1, weight=1)

    def _bind_mousewheel(self, _event=None):
        # 포인터가 일정 목록 위에 있을 때만 휠 입력을 연결합니다.
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def _configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=self.BG)
        style.configure("TFrame", background=self.BG)
        style.configure("List.TFrame", background=self.SURFACE)
        style.configure("Group.TLabelframe", background=self.BG, padding=0)
        style.configure(
            "Group.TLabelframe.Label",
            background=self.BG,
            foreground=self.MUTED,
            font=("Malgun Gothic", 9),
        )
        style.configure(
            "TLabel", background=self.BG, foreground=self.TEXT, font=("Malgun Gothic", 10)
        )
        style.configure("Title.TLabel", font=("Malgun Gothic", 21, "bold"), foreground=self.TEXT)
        style.configure("Muted.TLabel", foreground=self.MUTED)
        style.configure("List.Muted.TLabel", background=self.SURFACE, foreground=self.MUTED)
        style.configure(
            "Selected.TButton",
            padding=(12, 7),
            foreground=self.ACCENT,
            font=("Malgun Gothic", 10, "bold"),
        )
        style.configure("TButton", padding=(12, 7), font=("Malgun Gothic", 10))
        style.configure(
            "Accent.TButton", padding=(14, 8), foreground="#FFFFFF", background=self.ACCENT
        )
        style.map("Accent.TButton", background=[("active", "#244BD1")])
        style.configure("TEntry", padding=7)
        style.configure("TCombobox", padding=5)
        style.configure("TCheckbutton", background=self.SURFACE, font=("Malgun Gothic", 10))
        style.configure("Dialog.TCheckbutton", background=self.BG, font=("Malgun Gothic", 10))

    def _action_button(self, parent: ttk.Frame, text: str, command: Callable[[], None]):
        return ttk.Button(parent, text=text, command=command, state="disabled")

    def _update_scroll_region(self, _event=None):
        bounds = self.canvas.bbox("all")
        if bounds is None:
            return
        content_height = bounds[3] - bounds[1]
        viewport_height = self.canvas.winfo_height()
        # 목록이 화면보다 짧으면 스크롤 여백 없이 맨 위에 고정합니다.
        if content_height <= viewport_height:
            self.canvas.configure(scrollregion=(0, 0, bounds[2] - bounds[0], viewport_height))
            self.canvas.yview_moveto(0)
        else:
            self.canvas.configure(scrollregion=bounds)

    def _resize_list(self, event):
        self.canvas.itemconfigure(self._list_window, width=event.width)

    def _on_mousewheel(self, event):
        bounds = self.canvas.bbox("all")
        if bounds is None or bounds[3] - bounds[1] <= self.canvas.winfo_height():
            return "break"
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _on_escape(self, _event=None):
        self.on_hide()
        return "break"

    def _on_refresh_key(self, _event=None):
        self._refresh_unselected()
        return "break"

    def _change_view(self, status: str):
        self.current_status = status
        self.selected_ids.clear()
        self.refresh()

    def _on_search(self, _event=None):
        self.search_query = self.search_entry.get().strip().casefold()
        self.refresh()
        return "break"

    def _change_sort(self, _event=None):
        self._sort_descending = self.sort_switch.get() == "날짜 내림차순"
        self.refresh()

    def _add_appointment(self):
        AppointmentDialog(self.root, self.repository, on_saved=self._refresh_unselected)

    def _selected(self) -> list[Appointment]:
        return [item for item in self.appointments if item.id in self.selected_ids]

    def _edit_selected(self):
        selected = self._selected()
        if len(selected) == 1:
            AppointmentDialog(
                self.root,
                self.repository,
                on_saved=self._refresh_unselected,
                appointment=selected[0],
            )

    def _complete_selected(self):
        if self.current_status == "pending" and self.selected_ids:
            self.repository.complete(sorted(self.selected_ids))
            self._refresh_unselected()

    def _restore_selected(self):
        if self.current_status not in {"completed", "deleted"} or not self.selected_ids:
            return
        ids = sorted(self.selected_ids)
        if self.current_status == "deleted":
            self.repository.restore_deleted(ids)
        else:
            self.repository.restore(ids)
        self._refresh_unselected()

    def _delete_selected(self):
        selected = self._selected()
        if not selected:
            return
        permanently = self.current_status == "deleted"
        self._show_delete_confirmation(selected, permanently)

    def _show_delete_confirmation(self, selected: list[Appointment], permanently: bool):
        names = "\n".join(f"• {item.title}" for item in selected[:5])
        suffix = "\n…" if len(selected) > 5 else ""
        dialog = tk.Toplevel(self.root)
        dialog.title("일정 영구 삭제" if permanently else "일정 삭제")
        dialog.geometry("400x240")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.BG)
        dialog.bind("<Escape>", lambda _event: (dialog.destroy(), "break")[1])
        dialog.bind("<Return>", lambda _event: (confirm(), "break")[1])
        body = ttk.Frame(dialog, padding=22, style="App.TFrame")
        body.pack(fill="both", expand=True)
        if permanently:
            message = "선택한 일정을 영구 삭제할까요?\n이 작업은 되돌릴 수 없습니다."
        else:
            message = f"선택한 일정 {len(selected)}개를 삭제할까요?"
        ttk.Label(body, text=message, style="Title.TLabel", wraplength=350).pack(
            anchor="w", pady=(0, 14)
        )
        ttk.Label(
            body, text=names + suffix, justify="left", style="Muted.TLabel", wraplength=350
        ).pack(anchor="w", fill="x", expand=True)
        buttons = ttk.Frame(body, style="App.TFrame")
        buttons.pack(anchor="e", pady=(16, 0))
        ttk.Button(buttons, text="취소", command=dialog.destroy).pack(side="left", padx=(0, 8))

        def confirm():
            ids = [item.id for item in selected]
            if permanently:
                self.repository.permanently_delete(ids)
            else:
                self.repository.delete(ids)
            dialog.destroy()
            self._refresh_unselected()

        delete_label = "영구 삭제" if permanently else "삭제"
        ttk.Button(buttons, text=delete_label, command=confirm).pack(side="left")
        dialog.update_idletasks()
        dialog.geometry(f"420x{max(220, body.winfo_reqheight() + 44)}")
        center_window(dialog, self.root)

    def _set_selection(self, appointment_id: int, selected: bool):
        if selected:
            self.selected_ids.add(appointment_id)
        else:
            self.selected_ids.discard(appointment_id)
        all_selected = bool(self.appointments) and len(self.selected_ids) == len(self.appointments)
        self._select_all_var.set(all_selected)
        self._update_action_states()

    def _toggle_select_all(self):
        if self._select_all_var.get():
            self.selected_ids = {item.id for item in self.appointments}
        else:
            self.selected_ids.clear()
        for appointment_id, variable in self._checkbox_vars.items():
            variable.set(appointment_id in self.selected_ids)
        self._update_action_states()

    def _update_action_states(self):
        count = len(self._selected())
        self.edit_button.configure(state="normal" if count == 1 else "disabled")
        self.delete_button.configure(state="normal" if count else "disabled")
        can_complete = self.current_status == "pending" and count > 0
        self.complete_button.configure(state="normal" if can_complete else "disabled")
        can_restore = self.current_status in {"completed", "deleted"} and count > 0
        restore_label = "복원" if self.current_status == "deleted" else "복구"
        self.restore_button.configure(
            text=restore_label,
            state="normal" if can_restore else "disabled",
        )
        self.delete_button.configure(text="영구 삭제" if self.current_status == "deleted" else "삭제")
        self.selection_label.configure(text=f"{count}개 선택" if count else "")
        self._show_actions_for_status()
        for status, button in self.view_buttons.items():
            style_name = "Selected.TButton" if status == self.current_status else "TButton"
            button.configure(style=style_name)

    def _show_actions_for_status(self):
        all_actions = (
            self.edit_button,
            self.complete_button,
            self.restore_button,
            self.delete_button,
        )
        actions_by_status = {
            "pending": (self.complete_button, self.edit_button, self.delete_button),
            "completed": (self.restore_button, self.edit_button, self.delete_button),
            "deleted": (self.restore_button, self.delete_button),
        }
        for button in all_actions:
            button.pack_forget()
        for button in actions_by_status[self.current_status]:
            button.pack(side="left", padx=(0, 6))

    def refresh(self):
        self.appointments = self._visible_appointments()
        self.selected_ids.intersection_update(item.id for item in self.appointments)
        self._clear_list()
        self._render_list()
        self._update_scroll_region()
        self._update_action_states()

    def _visible_appointments(self) -> list[Appointment]:
        appointments = self.repository.list_by_status(self.current_status)
        if self.search_query:
            appointments = [
                item for item in appointments if self.search_query in item.title.casefold()
            ]
        return sorted(
            appointments,
            key=lambda item: (item.local_scheduled_at, item.id),
            reverse=self._sort_descending,
        )

    def _clear_list(self):
        self._checkbox_vars.clear()
        for child in self.list_frame.winfo_children():
            child.destroy()

    def _render_list(self):
        self._render_list_header()
        # 전체 선택은 검색 결과로 현재 표시 중인 일정에만 적용합니다.
        self._select_all_var.set(
            bool(self.appointments) and len(self.selected_ids) == len(self.appointments)
        )
        if not self.appointments:
            self._render_empty_state()
            return
        for index, appointment in enumerate(self.appointments):
            self._render_appointment_row(index, appointment)

    def _render_list_header(self):
        self.select_all_checkbox = ttk.Checkbutton(
            self.list_frame,
            text="전체 선택",
            variable=self._select_all_var,
            command=self._toggle_select_all,
        )
        self.select_all_checkbox.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 10))
        ttk.Label(self.list_frame, text="제목", style="List.Muted.TLabel").grid(
            row=0, column=1, sticky="w", pady=(12, 10)
        )
        ttk.Label(self.list_frame, text="날짜 및 시간", style="List.Muted.TLabel").grid(
            row=0, column=2, sticky="e", padx=18, pady=(12, 10)
        )
        self.list_frame.grid_columnconfigure(1, weight=1)

    def _render_empty_state(self):
        if self.search_query:
            message = "검색 결과가 없습니다"
        else:
            message = {
                "pending": "등록된 일정이 없습니다",
                "completed": "완료한 일정이 없습니다",
                "deleted": "삭제한 일정이 없습니다",
            }[self.current_status]
        ttk.Label(self.list_frame, text=message, style="List.Muted.TLabel").grid(
            row=1, column=0, columnspan=3, pady=48
        )

    def _render_appointment_row(self, index: int, appointment: Appointment):
        row_index = 1 + index * 2
        row_bg = "#F7F8FA" if index % 2 else self.SURFACE
        row = tk.Frame(self.list_frame, background=row_bg, padx=12, pady=10)
        row.grid(row=row_index, column=0, columnspan=3, sticky="ew")
        row.grid_columnconfigure(1, weight=1)

        variable = tk.BooleanVar(value=appointment.id in self.selected_ids)
        self._checkbox_vars[appointment.id] = variable
        tk.Checkbutton(
            row,
            variable=variable,
            command=lambda: self._set_selection(appointment.id, variable.get()),
            background=row_bg,
            activebackground=row_bg,
            highlightthickness=0,
            borderwidth=0,
        ).grid(row=0, column=0, padx=(0, 12))

        title = tk.Label(
            row,
            text=appointment.title,
            font=("Malgun Gothic", 11, "bold"),
            foreground=self.TEXT,
            background=row_bg,
            anchor="w",
            justify="left",
            wraplength=500,
            cursor="hand2",
            padx=0,
            pady=2,
        )
        title.bind(
            "<Button-1>",
            lambda event: self._select_from_title(event, appointment.id, variable),
        )
        title.bind("<Configure>", lambda event: self._wrap_title(event, title))
        title.grid(row=0, column=1, sticky="ew")

        scheduled_text = appointment.local_scheduled_at.strftime("%Y.%m.%d  %H:%M")
        ttk.Label(row, text=scheduled_text, style="Muted.TLabel", background=row_bg).grid(
            row=0, column=2, padx=(18, 0), sticky="e"
        )
        if not appointment.is_completed and self._is_overdue(appointment):
            tk.Label(row, text="지난 일정", font=("Malgun Gothic", 9), fg="#B54745", bg=row_bg).grid(
                row=0, column=3, padx=(12, 0)
            )
        ttk.Separator(self.list_frame, orient="horizontal").grid(
            row=row_index + 1, column=0, columnspan=3, sticky="ew"
        )

    def _select_from_title(self, event, appointment_id: int, variable: tk.BooleanVar):
        selected = not variable.get()
        variable.set(selected)
        self._set_selection(appointment_id, selected)
        return None

    @staticmethod
    def _wrap_title(event, widget):
        width = max(160, event.width)
        if int(widget.cget("wraplength")) != width:
            widget.configure(wraplength=width)

    def _refresh_unselected(self):
        self.selected_ids.clear()
        self.refresh()

    @staticmethod
    def _is_overdue(appointment: Appointment) -> bool:
        return appointment.local_scheduled_at <= datetime.now().astimezone()
