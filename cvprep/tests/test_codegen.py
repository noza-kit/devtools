import pytest

from cvprep.codegen import generate_script
from cvprep.pipeline import UnknownOpError


def test_generate_script_calls_ops_in_order():
    steps = [
        {"op": "grayscale"},
        {"op": "blur", "ksize": 5},
        {"op": "canny", "threshold1": 50, "threshold2": 150},
    ]
    script = generate_script(steps)

    assert "def process(image):" in script
    assert "image = ops.grayscale(image)" in script
    assert "image = ops.blur(image, ksize=5)" in script
    # 'canny' preset op maps to the actual function name, canny_edge
    assert "image = ops.canny_edge(image, threshold1=50, threshold2=150)" in script

    gray_line = script.index("ops.grayscale")
    blur_line = script.index("ops.blur")
    canny_line = script.index("ops.canny_edge")
    assert gray_line < blur_line < canny_line


def test_generate_script_bakes_in_input_and_output_paths():
    script = generate_script([{"op": "grayscale"}], input_path="a.jpg", output_path="b.png")
    assert "cv2.imread('a.jpg')" in script
    assert "cv2.imwrite('b.png', result)" in script


def test_generate_script_is_valid_python():
    steps = [
        {"op": "resize", "width": 224, "height": 224},
        {"op": "normalize", "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
    ]
    script = generate_script(steps)
    compile(script, "<generated>", "exec")  # raises SyntaxError if malformed


def test_generate_script_unknown_op_raises():
    with pytest.raises(UnknownOpError):
        generate_script([{"op": "not_a_real_op"}])


def test_generate_script_missing_op_key_raises():
    with pytest.raises(ValueError):
        generate_script([{"width": 10}])


def test_generate_script_empty_steps_produces_passthrough():
    script = generate_script([])
    assert "pass" in script
    compile(script, "<generated>", "exec")
