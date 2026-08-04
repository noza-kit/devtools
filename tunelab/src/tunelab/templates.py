from __future__ import annotations

TEMPLATE = """\
study: {study}
direction: maximize        # maximize | minimize
backend: optuna             # optuna | skopt | random | grid

budget:
  n_trials: 50
  # timeout: 3600            # seconds, optional
  n_jobs: 1                  # parallel workers (optuna/random backends only)

space:
  lr:
    type: float
    low: 1.0e-5
    high: 1.0e-1
    log: true
  batch_size:
    type: int
    low: 16
    high: 256
    step: 16
  optimizer:
    type: categorical
    choices: [adam, sgd, rmsprop]

objective:
  mode: command              # command | callable
  # Runs a training script; literal {{ and }} in the command must be doubled
  # since this string is a str.format template.
  command: "python train.py --lr {{lr}} --batch-size {{batch_size}} --optimizer {{optimizer}} --result-file {{result_file}}"
  result_file: json          # train.py must write {{"value": <float>}} to this path
  # result_regex: "val_acc:\\\\s*([0-9.]+)"   # alternative: parse stdout instead
  timeout_per_trial: 1800
  working_dir: .
  # For an in-process Python function instead of a subprocess:
  # mode: callable
  # entrypoint: mypackage.train:objective   # def objective(params: dict) -> float
"""


def render_template(study_name: str) -> str:
    return TEMPLATE.format(study=study_name)
