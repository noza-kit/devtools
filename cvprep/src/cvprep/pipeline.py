from __future__ import annotations

from dataclasses import dataclass, field

from cvprep import ops
from cvprep.presets import get_preset

OPS = {
    "resize": ops.resize,
    "normalize": ops.normalize,
    "roi_crop": ops.roi_crop,
    "grayscale": ops.grayscale,
    "blur": ops.blur,
    "canny": ops.canny_edge,
    "edge_detect": ops.canny_edge,
    "threshold": ops.threshold,
    "rotate": ops.rotate,
    "flip": ops.flip,
    "equalize_hist": ops.equalize_hist,
    "denoise": ops.denoise,
}


class UnknownOpError(Exception):
    pass


@dataclass
class Pipeline:
    steps: list[tuple[str, dict]] = field(default_factory=list)

    @classmethod
    def from_steps(cls, steps: list[dict]) -> "Pipeline":
        parsed = []
        for step in steps:
            step = dict(step)
            op = step.pop("op", None)
            if op is None:
                raise ValueError(f"Pipeline step missing 'op': {step}")
            parsed.append((op, step))
        return cls(parsed)

    @classmethod
    def from_preset(cls, name: str) -> "Pipeline":
        return cls.from_steps(get_preset(name))

    def run(self, image):
        result = image
        for op_name, kwargs in self.steps:
            func = OPS.get(op_name)
            if func is None:
                raise UnknownOpError(
                    f"Unknown op {op_name!r}. Available ops: {', '.join(sorted(OPS))}"
                )
            result = func(result, **kwargs)
        return result
