import pyperclip


class ClipboardUnavailableError(RuntimeError):
    pass


def write_clipboard(text: str) -> None:
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise ClipboardUnavailableError(str(exc)) from exc
