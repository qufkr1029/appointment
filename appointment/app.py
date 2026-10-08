import tkinter as tk
from pathlib import Path

from appointment.data.appointment_repository import AppointmentRepository
from appointment.services.scheduler import Scheduler
from appointment.tray import TrayManager
from appointment.ui.main_window import MainWindow
from appointment.ui.window_utils import center_on_screen


class AppointmentApp:
    def __init__(self):
        self.root = tk.Tk()

        package_dir = Path(__file__).resolve().parent
        database_path = package_dir.parent / "data" / "appointment.db"
        self.repository = AppointmentRepository(database_path)
        self.main_window = MainWindow(
            self.root,
            self.repository,
            on_hide=self.hide_window,
        )
        self.scheduler = Scheduler(
            self.root,
            self.repository,
            on_show_list=self.show_window,
            on_snoozed=self.main_window.refresh,
        )
        self.tray = TrayManager(
            on_show=self._show_from_tray,
            on_exit=self._exit_from_tray,
        )
        self._is_exiting = False

    def run(self):
        self.show_window()
        self.root.after(100, self._start_background_services)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.exit()

    def _start_background_services(self):
        self.scheduler.start()
        self.tray.start()

    def _show_from_tray(self):
        self.root.after(0, self.show_window)

    def _exit_from_tray(self):
        self.root.after(0, self.exit)

    def show_window(self):
        try:
            self.root.deiconify()
            center_on_screen(self.root)
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def hide_window(self):
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

    def exit(self):
        if self._is_exiting:
            return
        self._is_exiting = True
        self.scheduler.stop()
        self.tray.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def main():
    app = AppointmentApp()
    app.run()
