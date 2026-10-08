def center_window(window, parent) -> None:
    """Center a dialog over its parent, keeping it within the screen bounds."""
    parent.update_idletasks()
    window.update_idletasks()

    width = window.winfo_width()
    height = window.winfo_height()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    x = parent.winfo_rootx() + (parent_width - width) // 2
    y = parent.winfo_rooty() + (parent_height - height) // 2

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, min(x, screen_width - width))
    y = max(0, min(y, screen_height - height))
    window.geometry(f"{width}x{height}+{x}+{y}")


def center_on_screen(window) -> None:
    """Center a window on the screen without depending on its owner position."""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
