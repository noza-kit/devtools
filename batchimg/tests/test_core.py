import cv2

from batchimg.core import Options, execute, plan


def test_plan_default_keeps_original_names(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    make_image(tmp_path / "b.png")
    out_dir = tmp_path / "out"

    items = plan(tmp_path, out_dir, Options())

    assert [i.destination.name for i in items] == ["a.jpg", "b.png"]
    assert all(i.destination.parent == out_dir for i in items)


def test_plan_applies_rename_template_in_discovery_order(tmp_path, make_image):
    make_image(tmp_path / "b.jpg")
    make_image(tmp_path / "a.jpg")
    out_dir = tmp_path / "out"

    items = plan(tmp_path, out_dir, Options(rename_template="img_{n}"))

    assert [i.destination.name for i in items] == ["img_0001.jpg", "img_0002.jpg"]


def test_plan_start_and_digits_options(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    out_dir = tmp_path / "out"

    items = plan(tmp_path, out_dir, Options(rename_template="img_{n}", start=10, digits=2))

    assert items[0].destination.name == "img_10.jpg"


def test_plan_excludes_files_inside_nested_output_dir(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    out_dir = tmp_path / "batchimg_out"
    make_image(out_dir / "already_processed.jpg")  # simulate a prior run's output

    items = plan(tmp_path, out_dir, Options(), recursive=True)

    assert [i.source.name for i in items] == ["a.jpg"]


def test_plan_resolves_name_conflicts(tmp_path, make_image):
    # Both land in the same output directory and render to the same name
    # (a fixed --rename template with no {n}), so the second must be renumbered.
    make_image(tmp_path / "a.jpg")
    make_image(tmp_path / "b.jpg")
    out_dir = tmp_path / "out"

    items = plan(tmp_path, out_dir, Options(rename_template="photo"))

    names = sorted(i.destination.name for i in items)
    assert names == ["photo (1).jpg", "photo.jpg"]


def test_plan_ignores_unsupported_extensions(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    (tmp_path / "notes.txt").write_text("skip me", encoding="utf-8")

    items = plan(tmp_path, tmp_path / "out", Options())

    assert [i.source.name for i in items] == ["a.jpg"]


def test_execute_copies_without_resize(tmp_path, make_image):
    make_image(tmp_path / "a.jpg", size=(40, 30))
    out_dir = tmp_path / "out"
    items = plan(tmp_path, out_dir, Options())

    processed, errors = execute(items, Options())

    assert processed == 1
    assert errors == []
    result = cv2.imread(str(out_dir / "a.jpg"))
    assert result.shape[:2] == (30, 40)


def test_execute_resizes_images(tmp_path, make_image):
    make_image(tmp_path / "a.jpg", size=(40, 30))
    out_dir = tmp_path / "out"
    options = Options(resize=(20, 20), keep_aspect=False)
    items = plan(tmp_path, out_dir, options)

    processed, errors = execute(items, options)

    assert processed == 1
    result = cv2.imread(str(out_dir / "a.jpg"))
    assert result.shape[:2] == (20, 20)


def test_execute_reports_error_and_continues(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")
    bad = tmp_path / "b.jpg"
    bad.write_bytes(b"not an image")
    out_dir = tmp_path / "out"
    options = Options(resize=(10, 10))
    items = plan(tmp_path, out_dir, options)

    processed, errors = execute(items, options)

    assert processed == 1
    assert len(errors) == 1
    assert "b.jpg" in errors[0]
    assert (out_dir / "a.jpg").exists()
    assert not (out_dir / "b.jpg").exists()


def test_execute_in_place_overwrites_source(tmp_path, make_image):
    path = make_image(tmp_path / "a.jpg", size=(40, 30))
    options = Options(resize=(20, 20), keep_aspect=False)
    items = plan(tmp_path, tmp_path, options)

    processed, errors = execute(items, options)

    assert processed == 1
    assert errors == []
    result = cv2.imread(str(path))
    assert result.shape[:2] == (20, 20)


def test_plan_in_place_own_path_is_not_treated_as_a_conflict(tmp_path, make_image):
    # A file's own on-disk path always "exists", so the conflict resolver must not
    # bump it to "a (1).jpg" when the plan is a plain --in-place overwrite of itself.
    make_image(tmp_path / "a.jpg")

    items = plan(tmp_path, tmp_path, Options())

    assert items[0].destination == tmp_path / "a.jpg"


def test_plan_in_place_rename_colliding_with_another_source_file_is_bumped(tmp_path, make_image):
    # a.jpg -> "photo.jpg" and b.jpg -> "photo.jpg" (fixed template, no {n}): the
    # first legitimately claims photo.jpg (renaming a.jpg in place); the second is
    # a genuine collision and must be bumped, even though b.jpg is also a source file.
    make_image(tmp_path / "a.jpg")
    make_image(tmp_path / "photo.jpg")

    items = plan(tmp_path, tmp_path, Options(rename_template="photo"))

    destinations = sorted(i.destination.name for i in items)
    assert destinations == ["photo (1).jpg", "photo.jpg"]
