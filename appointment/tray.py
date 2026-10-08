from collections.abc import Callable

from PIL import Image, ImageDraw
import pystray


class TrayManager:
    def __init__(self, on_show: Callable[[], None], on_exit: Callable[[], None]):
        self.on_show = on_show
        self.on_exit = on_exit
        self.icon = pystray.Icon(
            "appointment_reminder",
            self._make_image(),
            "일정 알림",
            menu=pystray.Menu(
                pystray.MenuItem("창 열기", self._show, default=True),
                pystray.MenuItem("앱 종료", self._exit),
            ),
        )

    @staticmethod
    def _make_image():
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=15, fill="#5B5FEF")
        draw.ellipse((15, 15, 49, 49), outline="white", width=3)
        draw.line((32, 21, 32, 32, 40, 36), fill="white", width=3)
        return image

    def _show(self, _icon, _item):
        self.on_show()

    def _exit(self, _icon, _item):
        self.on_exit()

    def start(self):
        self.icon.run_detached()

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
