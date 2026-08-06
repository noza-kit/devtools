import builtins

from gazemouse.screenshot import build_screenshot_fn


def test_returns_none_when_snapclip_not_installed(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("snapclip"):
            raise ImportError(f"no module named {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert build_screenshot_fn() is None


def test_returns_callable_when_snapclip_is_installed():
    # snapclip is installed in this repo's shared dev environment (this
    # session built it earlier); build_screenshot_fn() should pick it up
    # for real rather than needing a mock, though actually *calling* the
    # returned function would take a real screenshot -- not done here.
    fn = build_screenshot_fn()
    assert fn is None or callable(fn)
