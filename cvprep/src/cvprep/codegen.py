"""Render a preset's pipeline steps as a standalone Python script that calls
the same cvprep.ops functions the Pipeline class would, in the same order."""

from __future__ import annotations

from cvprep.pipeline import OPS, UnknownOpError

_TEMPLATE = '''\
import cv2
from cvprep import ops


def process(image):
{body}
    return image


if __name__ == "__main__":
    image = cv2.imread({input_path!r})
    result = process(image)
    cv2.imwrite({output_path!r}, result)
'''


def generate_script(
    steps: list[dict],
    *,
    input_path: str = "input.jpg",
    output_path: str = "output.jpg",
) -> str:
    body_lines = []
    for step in steps:
        step = dict(step)
        op = step.pop("op", None)
        if op is None:
            raise ValueError(f"Pipeline step missing 'op': {step}")
        func = OPS.get(op)
        if func is None:
            raise UnknownOpError(f"Unknown op {op!r}. Available ops: {', '.join(sorted(OPS))}")

        args = ", ".join(f"{key}={value!r}" for key, value in step.items())
        call = f"ops.{func.__name__}(image{', ' + args if args else ''})"
        body_lines.append(f"    image = {call}")

    body = "\n".join(body_lines) if body_lines else "    pass"
    return _TEMPLATE.format(body=body, input_path=input_path, output_path=output_path)
