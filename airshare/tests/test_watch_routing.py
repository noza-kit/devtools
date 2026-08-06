from pathlib import Path

from airshare.watch_config import RoutingRule
from airshare.watch_routing import pick_destination, route_file


def _rules(tmp_path: Path) -> tuple[RoutingRule, ...]:
    return (
        RoutingRule(name="pictures", extensions=(".jpg", ".png", ".heic"), destination=tmp_path / "Pictures"),
        RoutingRule(name="docs", extensions=(".pdf", ".md"), destination=tmp_path / "Documents"),
    )


def test_pick_destination_matches_extension(tmp_path: Path):
    rules = _rules(tmp_path)
    assert pick_destination(Path("photo.JPG"), rules, fallback=tmp_path) == tmp_path / "Pictures"
    assert pick_destination(Path("report.pdf"), rules, fallback=tmp_path) == tmp_path / "Documents"


def test_pick_destination_no_match_returns_fallback(tmp_path: Path):
    rules = _rules(tmp_path)
    assert pick_destination(Path("archive.zip"), rules, fallback=tmp_path) == tmp_path


def test_route_file_moves_and_creates_destination(tmp_path: Path):
    src = tmp_path / "inbox" / "photo.jpg"
    src.parent.mkdir()
    src.write_bytes(b"data")
    rules = _rules(tmp_path)

    result = route_file(src, rules, fallback=tmp_path / "inbox")

    assert result == tmp_path / "Pictures" / "photo.jpg"
    assert result.exists()
    assert not src.exists()


def test_route_file_avoids_collision(tmp_path: Path):
    dest_dir = tmp_path / "Pictures"
    dest_dir.mkdir()
    (dest_dir / "photo.jpg").write_bytes(b"existing")

    src = tmp_path / "inbox" / "photo.jpg"
    src.parent.mkdir()
    src.write_bytes(b"new")
    rules = _rules(tmp_path)

    result = route_file(src, rules, fallback=tmp_path / "inbox")

    assert result == dest_dir / "photo (1).jpg"
    assert (dest_dir / "photo.jpg").read_bytes() == b"existing"
    assert result.read_bytes() == b"new"


def test_route_file_unmatched_extension_stays_in_fallback(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    src = inbox / "archive.zip"
    src.write_bytes(b"data")
    rules = _rules(tmp_path)

    result = route_file(src, rules, fallback=inbox)

    assert result == src
    assert src.exists()
