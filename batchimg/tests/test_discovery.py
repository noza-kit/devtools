from pathlib import Path

from batchimg.discovery import classify, find_files


def test_classify_image_extension():
    assert classify(Path("photo.JPG")) == "image"
    assert classify(Path("photo.png")) == "image"


def test_classify_video_extension():
    assert classify(Path("clip.mp4")) == "video"
    assert classify(Path("clip.MOV")) == "video"


def test_classify_unsupported_extension_is_none():
    assert classify(Path("notes.txt")) is None
    assert classify(Path("noext")) is None


def test_find_files_default_patterns_picks_images_and_videos(tmp_path, make_image, make_video):
    make_image(tmp_path / "a.jpg")
    make_video(tmp_path / "b.mp4", frames=3)
    (tmp_path / "notes.txt").write_text("not media", encoding="utf-8")

    files = find_files(tmp_path)

    assert [f.name for f in files] == ["a.jpg", "b.mp4"]


def test_find_files_non_recursive_ignores_subdirectories(tmp_path, make_image):
    make_image(tmp_path / "top.jpg")
    make_image(tmp_path / "sub" / "nested.jpg")

    files = find_files(tmp_path, recursive=False)

    assert [f.name for f in files] == ["top.jpg"]


def test_find_files_recursive_includes_subdirectories(tmp_path, make_image):
    make_image(tmp_path / "top.jpg")
    make_image(tmp_path / "sub" / "nested.jpg")

    files = find_files(tmp_path, recursive=True)

    assert sorted(f.name for f in files) == ["nested.jpg", "top.jpg"]


def test_find_files_custom_pattern(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    make_image(tmp_path / "b.png")

    files = find_files(tmp_path, patterns=["*.png"])

    assert [f.name for f in files] == ["b.png"]
