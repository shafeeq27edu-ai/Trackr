# Code Style Rule

- All Python code follows PEP 8.
- Every function has a docstring (one line minimum: what it does, params, return).
- Type hints required on function signatures, especially for arrays/tensors
  (e.g. `boxes: np.ndarray`, `frame: np.ndarray`).
- No magic numbers — confidence thresholds, IoU thresholds, frame-drop
  limits, etc. go in named constants or a config dict at the top of the file.
- New functionality goes in the appropriate `tracker/` module — never grows
  `app.py` into a dumping ground for logic.
- No bare `except:` — catch specific exceptions.
- Random seeds set wherever reproducibility matters (e.g. any sampling in analytics).
