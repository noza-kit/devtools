import pyperclip


class ClipboardUnavailableError(RuntimeError):
    pass


def read_clipboard() -> str:
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException as exc:
        raise ClipboardUnavailableError(str(exc)) from exc


def write_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise ClipboardUnavailableError(str(exc)) from exc
