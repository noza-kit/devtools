from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from gazemouse.calibration import CalibrationData

DEFAULT_CALIBRATION_PATH = Path.home() / ".gazemouse" / "calibration.json"


def save_calibration(data: CalibrationData, path: Optional[Path] = None) -> Path:
    resolved = path or DEFAULT_CALIBRATION_PATH
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(
            {
                "iris_min_x": data.iris_min_x,
                "iris_max_x": data.iris_max_x,
                "iris_min_y": data.iris_min_y,
                "iris_max_y": data.iris_max_y,
                "screen_width": data.screen_width,
                "screen_height": data.screen_height,
            }
        ),
        encoding="utf-8",
    )
    return resolved


def load_calibration(path: Optional[Path] = None) -> CalibrationData:
    resolved = path or DEFAULT_CALIBRATION_PATH
    if not resolved.exists():
        raise FileNotFoundError(
            f"キャリブレーションデータが見つかりません: {resolved} (先に `gazemouse calibrate` を実行してください)"
        )
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    return CalibrationData(**raw)
