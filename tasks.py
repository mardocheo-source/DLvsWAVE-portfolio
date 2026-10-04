"""
Task: funzioni matematiche che generano dataset sintetici.
Dict-based, facile aggiungere nuovi task.
Supporto CSV load/save per custom datasets.
"""
import csv
import json
import os
from datetime import datetime
import numpy as np


def sin_sum(X):
    return np.sin(X[:, 0]) + X[:, 1] ** 2


def poly3(X):
    return X[:, 0] ** 3 - 2 * X[:, 0] + 0.5


def sin_product(X):
    return np.sin(X[:, 0] * X[:, 1]) + X[:, 0]


def friedman1(X):
    # Benchmark ML classico (5 feature)
    return (10 * np.sin(np.pi * X[:, 0] * X[:, 1])
            + 20 * (X[:, 2] - 0.5) ** 2
            + 10 * X[:, 3] + 5 * X[:, 4])


def step_fn(X):
    return (X[:, 0] > 0).astype(float)


def mult_modulated(X):
    return np.sin(3 * X[:, 0]) * np.cos(2 * X[:, 1]) + 0.1 * X[:, 0] * X[:, 1]


def high_freq(X):
    # Stressa i banchi a bassa frequenza
    return np.sin(10 * X[:, 0]) + 0.5 * np.cos(7 * X[:, 0])


TASKS = {
    "sin_sum":        {"fn": sin_sum,        "n_features": 2, "range": (-3, 3)},
    "poly3":          {"fn": poly3,          "n_features": 1, "range": (-2, 2)},
    "sin_product":    {"fn": sin_product,    "n_features": 2, "range": (-3, 3)},
    "friedman1":      {"fn": friedman1,      "n_features": 5, "range": (0, 1)},
    "step_fn":        {"fn": step_fn,        "n_features": 1, "range": (-2, 2)},
    "mult_modulated": {"fn": mult_modulated, "n_features": 2, "range": (-2, 2)},
    "high_freq":      {"fn": high_freq,      "n_features": 1, "range": (-3, 3)},
}


def generate_dataset(task_name, n_samples, seed=0, noise_std=0.0):
    task = TASKS[task_name]
    rng = np.random.RandomState(seed)
    lo, hi = task["range"]
    X = rng.uniform(lo, hi, (n_samples, task["n_features"]))
    y = task["fn"](X)
    if noise_std > 0:
        y = y + rng.normal(0, noise_std, size=y.shape)
    return X, y


def save_csv(X, y, path):
    d = X.shape[1]
    header = [f"x{i+1}" for i in range(d)] + ["y"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i in range(len(X)):
            w.writerow(list(X[i]) + [float(y[i])])


def load_csv(path):
    with open(path) as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [list(map(float, r)) for r in reader]
    arr = np.array(rows)
    return arr[:, :-1], arr[:, -1], header


def is_csv_task(value):
    return isinstance(value, str) and value.lower().endswith(".csv")


def parse_datetime_like(value):
    s = str(value).strip()
    if not s:
        return None
    normalized = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    fmts = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_datetime_like(value):
    return parse_datetime_like(value)


def load_csv_dataset(path, target_cols_list="", skip_cols_list=""):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV senza header: {path}")
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV vuoto: {path}")

    header = list(reader.fieldnames)
    skip_cols = [c.strip() for c in (skip_cols_list or "").split(",") if c.strip()]
    target_cols = [c.strip() for c in (target_cols_list or "").split(",") if c.strip()]

    if not target_cols:
        target_cols = [header[-1]]

    missing_targets = [c for c in target_cols if c not in header]
    if missing_targets:
        raise ValueError(f"Colonne target non trovate nel CSV: {missing_targets}")

    # Silently ignore missing skip columns
    missing_skip = [c for c in skip_cols if c not in header]

    selected_target = target_cols[0]
    multi_target_requested = len(target_cols) > 1
    context_col = None
    for preferred in ("date", "datetime", "timestamp", "time"):
        for col in header:
            if col.strip().lower() == preferred:
                context_col = col
                break
        if context_col is not None:
            break

    # Auto-exclude seismic columns
    def _is_seismic_col(c):
        c_lower = c.lower()
        if c_lower in ("mag", "depth", "latitude", "longitude"):
            return True
        if c_lower.startswith("tt_seis_") or "seis" in c_lower:
            return True
        if c_lower.startswith("tt_days_") or c_lower.startswith("tt_lookup_"):
            return True
        return False

    feature_cols = [
        c for c in header 
        if c != selected_target and c not in skip_cols and not _is_seismic_col(c)
    ]
    if not feature_cols:
        raise ValueError("Nessuna feature disponibile dopo target/skip ed esclusione sismica")

    X_rows = []
    y_rows = []
    for idx, row in enumerate(rows, start=2):
        try:
            X_rows.append([float(row[c]) for c in feature_cols])
            y_rows.append(float(row[selected_target]))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Valore non numerico nel CSV alla riga {idx}: {exc}"
            ) from exc

    X = np.asarray(X_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)
    context_values = [row[context_col] for row in rows] if context_col else None
    context_datetimes = None
    if context_values is not None:
        parsed_datetimes = [parse_datetime_like(v) for v in context_values]
        if all(dt is not None for dt in parsed_datetimes):
            context_datetimes = parsed_datetimes
    location_target_meta = None
    sidecar_json = os.path.splitext(path)[0] + ".json"
    if os.path.exists(sidecar_json):
        try:
            with open(sidecar_json) as f:
                sidecar = json.load(f)
            if sidecar.get("target_name") == selected_target and sidecar.get("mode") in {"analog", "binary"}:
                location_target_meta = sidecar
        except Exception:
            location_target_meta = None

    return {
        "X": X,
        "y": y,
        "header": header,
        "row_indices": np.arange(len(rows), dtype=int),
        "feature_cols": feature_cols,
        "target_col": selected_target,
        "requested_target_cols": target_cols,
        "multi_target_requested": multi_target_requested,
        "skip_cols": skip_cols,
        "context_col": context_col,
        "context_values": context_values,
        "context_datetimes": context_datetimes,
        "path": path,
        "location_target_meta": location_target_meta,
    }
