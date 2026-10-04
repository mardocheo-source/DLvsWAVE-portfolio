"""Data and split contracts for the new geographic joint-study orchestration."""
from __future__ import annotations

import hashlib
import copy
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str, allow_nan=False) + "\n")
    temporary.replace(path)


def fingerprint(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def timestamp(value):
    return pd.to_datetime(value, utc=True).tz_localize(None)


def slot_dates(values, config):
    dates = pd.to_datetime(values, utc=True).dt.tz_localize(None)
    anchor = timestamp(config["grid_anchor"])
    width = pd.Timedelta(days=config["interval_days"])
    return anchor + ((dates - anchor) // width) * width


def normalize_catalog(frame, config):
    required = {"id", "time", "latitude", "longitude", "mag"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing catalog fields: {required - set(frame.columns)}")
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame.time, utc=True, errors="coerce").dt.tz_localize(None)
    for name in ("mag", "latitude", "longitude"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    frame = frame.dropna(subset=["time", "mag", "latitude", "longitude"])
    frame = frame.loc[frame.latitude.between(-90, 90)].copy()
    frame["longitude"] = ((frame.longitude + 180) % 360) - 180
    # Stable fallback only for exact matches; nearby separate earthquakes stay separate.
    absent = frame.id.isna() | frame.id.astype(str).str.strip().eq("")
    frame.loc[absent, "id"] = frame.loc[absent].apply(
        lambda r: "fallback_" + hashlib.sha256(f"{r.time}|{r.latitude}|{r.longitude}|{r.mag}".encode()).hexdigest()[:20], axis=1)
    frame = frame.sort_values("time").drop_duplicates("id", keep="last")
    frame = frame.loc[(frame.time >= timestamp(config["training_start"])) &
                      (frame.time < timestamp(config["reference_date"]))].copy()
    frame["slot"] = slot_dates(frame.time, config)
    # Incomplete last intervals must not be interpreted as complete negative labels.
    frame["complete_slot"] = frame.slot + pd.Timedelta(days=config["interval_days"]) <= timestamp(config["reference_date"])
    return frame.reset_index(drop=True)


class DownloadBudget:
    def __init__(self, root, config):
        self.root, self.limits = Path(root), config["budgets"]
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "download_audit.json"
        self.audit = json.loads(self.path.read_text()) if self.path.exists() else {"bytes": 0, "requests": [], "active_seconds": 0}
        self.started = time.monotonic()
        self.previous_seconds = self.audit["active_seconds"]

    def check(self, kind):
        elapsed = self.previous_seconds + time.monotonic() - self.started
        if elapsed >= self.limits["download_seconds"]:
            raise RuntimeError("download_time_budget_exhausted")
        count = sum(r["kind"] == kind for r in self.audit["requests"])
        if count >= self.limits[f"maximum_{kind}_requests"]:
            raise RuntimeError(f"{kind}_request_budget_exhausted")
        if self.audit["bytes"] >= self.limits["maximum_download_bytes"]:
            raise RuntimeError("download_byte_budget_exhausted")

    def record(self, kind, details, size=0):
        self.audit["requests"].append({"kind": kind, **details})
        self.audit["bytes"] += size
        self.audit["active_seconds"] = self.previous_seconds + time.monotonic() - self.started
        atomic_json(self.path, self.audit)


def fetch_catalog(root, config, budget):
    root = Path(root) / "catalog_snapshot"
    root.mkdir(parents=True, exist_ok=True)
    floor = min(config[c]["minimum_magnitude"] for c in ("energy", "location"))
    # Fetch the bounded allowed spectrum once; never repeatedly download a century per child.
    start, end = timestamp(config["training_start"]), timestamp(config["reference_date"])
    frames = []
    while start < end:
        stop = min(start + pd.DateOffset(years=10), end)
        params = {"format": "csv", "starttime": start.isoformat(), "endtime": stop.isoformat(),
                  "minmagnitude": floor, "orderby": "time-asc", "limit": 20000}
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urllib.parse.urlencode(params)
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        path = root / f"{key}.csv"
        receipt = path.with_suffix(".json")
        if path.exists() and receipt.exists():
            meta = json.loads(receipt.read_text())
            if meta["sha256"] != fingerprint(path):
                raise RuntimeError("catalog_snapshot_checksum_mismatch")
        else:
            budget.check("catalog")
            budget.record("catalog", {"url": url, "status": "requested"})
            request = urllib.request.Request(url, headers={"User-Agent": "DLVS-Wave-nested-research/1.0"})
            with urllib.request.urlopen(request, timeout=budget.limits["request_timeout_seconds"]) as response:
                data = response.read(budget.limits["maximum_download_bytes"] - budget.audit["bytes"] + 1)
            if len(data) + budget.audit["bytes"] > budget.limits["maximum_download_bytes"]:
                raise RuntimeError("download_byte_budget_exhausted")
            parsed = pd.read_csv(io.BytesIO(data)) if data.strip() else pd.DataFrame(columns=["id", "time", "latitude", "longitude", "mag"])
            if len(parsed) >= 20000:
                raise RuntimeError("catalog_chunk_may_be_truncated: reduce query chunk duration")
            path.write_bytes(data if data.strip() else b"id,time,latitude,longitude,mag\n")
            budget.audit["bytes"] += len(data)
            atomic_json(budget.path, budget.audit)
            atomic_json(receipt, {"url": url, "sha256": fingerprint(path), "rows": len(parsed), "download_floor": floor})
        frames.append(pd.read_csv(path))
        start = stop
    catalog = normalize_catalog(pd.concat(frames, ignore_index=True), config)
    catalog.to_csv(root / "events.csv", index=False)
    atomic_json(root / "manifest.json", {"sha256": fingerprint(root / "events.csv"), "download_floor": floor,
                "rows": len(catalog), "cutoff_exclusive": config["reference_date"],
                "note": "Bounded spectrum prefetched once for all nodes. Historical completeness is not assumed."})
    return catalog


def unit_vectors(latitude, longitude):
    lat, lon = np.radians(latitude), np.radians(longitude)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def assign_zones(events, centers):
    centers = np.asarray(centers)
    return np.argmax(unit_vectors(events.latitude, events.longitude) @ centers.T, axis=1)


def scope_catalog(events, path):
    selected = events
    for rule in path:
        selected = selected.loc[assign_zones(selected, rule["centers"]) == rule["zone"]]
    return selected.copy().reset_index(drop=True)


def zone_geometry(path, step=2):
    lat = np.arange(-90 + step / 2, 90, step)
    lon = np.arange(-180 + step / 2, 180, step)
    xx, yy = np.meshgrid(lon, lat)
    grid = pd.DataFrame({"longitude": xx.ravel(), "latitude": yy.ravel()})
    selected = scope_catalog(grid, path)
    if selected.empty:
        return {"area_fraction": 0.0, "diameter_km": 0.0, "bounds": None}
    weights = np.cos(np.radians(grid.latitude))
    area = float(np.cos(np.radians(selected.latitude)).sum() / weights.sum())
    if not path:
        return {"area_fraction": 1.0, "diameter_km": 20015.1,
                "bounds": [-90.0, 90.0, -180.0, 180.0], "crosses_antimeridian": False, "centroid": [0.0, 0.0]}
    c = np.asarray(path[-1]["centers"])[path[-1]["zone"]]
    center_lat = float(np.degrees(np.arcsin(c[2])))
    center_lon = float(np.degrees(np.arctan2(c[1], c[0])))
    unwrapped = center_lon + ((selected.longitude.to_numpy() - center_lon + 180) % 360) - 180
    lo, hi = unwrapped.min() - step, unwrapped.max() + step
    west, east = float((lo + 180) % 360 - 180), float((hi + 180) % 360 - 180)
    radius = np.arccos(np.clip(unit_vectors(selected.latitude, selected.longitude) @ c, -1, 1)).max() * 6371.0088
    return {"area_fraction": area, "diameter_km": float(min(20015.1, 2 * radius)),
            "bounds": [float(max(-90, selected.latitude.min() - step)), float(min(90, selected.latitude.max() + step)), west, east],
            "crosses_antimeridian": west > east, "centroid": [center_lat, center_lon],
            "geometry_note": "Approximate 2-degree download envelope; exact membership uses stored spherical ancestor rules."}


def select_validation(events, config, component):
    policy, spec = config["validation"], config[component]
    events = events.loc[events.complete_slot].sort_values("time")
    audit = []
    months = range(policy["initial_months"], policy["maximum_months"] + 1, policy["step_months"])
    for reduction in range(config["adaptation"]["maximum_reductions"] + 1):
        threshold = round(spec["magnitude"] - reduction * config["adaptation"]["step"], 6)
        if threshold < spec["minimum_magnitude"] - 1e-8:
            break
        eligible = events.loc[events.mag >= threshold].copy()
        fallback = None
        for duration in months:
            raw_start = timestamp(config["reference_date"]) - pd.DateOffset(months=duration)
            # Start at the next complete grid boundary; never include older events.
            start = slot_dates(pd.Series([raw_start]), config).iloc[0]
            if start < raw_start:
                start += pd.Timedelta(days=config["interval_days"])
            train = eligible.loc[eligible.slot < start]
            val = eligible.loc[eligible.slot >= start]
            ntr, nval = train.slot.nunique(), val.slot.nunique()
            fraction = nval / max(1, ntr + nval)
            enough = nval >= spec["minimum_events"] and ntr >= policy["minimum_training_event_slots"] and fraction <= policy["maximum_withheld_fraction"]
            row = {"threshold": threshold, "months": duration, "training_event_slots": ntr,
                   "validation_event_slots": nval, "training_events": len(train), "validation_events": len(val),
                   "withheld_fraction": fraction, "admissible": enough}
            audit.append(row)
            if enough:
                result = {**row, "validation_start": start.isoformat(), "validation_end_exclusive": config["reference_date"],
                          "training_start": config["training_start"], "training_end_exclusive": start.isoformat(),
                          "initial_threshold": spec["magnitude"], "reduction": round(spec["magnitude"] - threshold, 6),
                          "status": "sufficient", "desired_count_met": nval >= spec["desired_events"],
                          "validation_ids": val.id.astype(str).tolist(), "audit": audit.copy()}
                if nval >= spec["desired_events"]:
                    return result
                if fallback is None:
                    fallback = result
        # Minimum is sufficient; do not lower a scientific threshold merely to improve scores.
        if fallback:
            fallback["audit"] = audit.copy()
            return fallback
    return {"status": "insufficient_data", "initial_threshold": spec["magnitude"], "audit": audit,
            "reason": "No bounded recent split preserves the required training events and validation count."}


def fit_spherical_zones(events, config):
    coordinates = unit_vectors(events.latitude, events.longitude)
    choices = []
    for count in range(config["zones"]["minimum"], config["zones"]["maximum"] + 1):
        if len(events) < count * config["zones"]["minimum_training_events"]:
            continue
        fit = KMeans(n_clusters=count, random_state=config["models"]["seed"], n_init=10).fit(coordinates)
        centers = fit.cluster_centers_ / np.maximum(np.linalg.norm(fit.cluster_centers_, axis=1, keepdims=True), 1e-12)
        labels = np.argmax(coordinates @ centers.T, axis=1)
        counts = np.bincount(labels, minlength=count)
        if counts.min() < config["zones"]["minimum_training_events"]:
            continue
        quality = float(silhouette_score(coordinates, labels, sample_size=min(1500, len(events)), random_state=42))
        choices.append({"count": count, "centers": centers.tolist(), "counts": counts.tolist(), "silhouette": quality})
    if not choices:
        raise ValueError("insufficient_zone_construction_events")
    selected = max(choices, key=lambda c: (c["silhouette"], -c["count"]))
    return {**selected, "candidates": choices, "construction_event_ids": events.id.astype(str).tolist(),
            "method": "Training-only spherical KMeans; nearest unit-centroid assignment. Not tectonic fault boundaries."}


def plan_spatial_validation(events, config):
    """Adapt for geometric sufficiency as well as counts, never for model scores."""
    initial = config["location"]["magnitude"]
    all_attempts, geometry_attempts = [], []
    for reduction in range(config["adaptation"]["maximum_reductions"] + 1):
        threshold = round(initial - reduction * config["adaptation"]["step"], 6)
        if threshold < config["location"]["minimum_magnitude"] - 1e-8:
            break
        trial_config = copy.deepcopy(config)
        trial_config["location"]["magnitude"] = threshold
        trial_config["adaptation"]["maximum_reductions"] = 0
        split = select_validation(events, trial_config, "location")
        all_attempts.extend(split["audit"])
        if split["status"] != "sufficient": continue
        eligible = events.loc[(events.mag >= threshold) & events.complete_slot]
        training = eligible.loc[eligible.slot < timestamp(split["validation_start"])]
        slots = sorted(training.slot.unique())
        construction = training.loc[training.slot < pd.Timestamp(slots[-config["validation"]["inner_events"]])]
        try:
            zones = fit_spherical_zones(construction, config)
        except ValueError as error:
            geometry_attempts.append({"threshold": threshold, "reason": str(error)})
            continue
        validation = eligible.loc[eligible.slot >= timestamp(split["validation_start"])]
        represented = len(np.unique(assign_zones(validation, zones["centers"])))
        geometry_attempts.append({"threshold": threshold, "represented_validation_zones": represented})
        if represented < config["location"]["minimum_validation_zones"]: continue
        split.update({"initial_threshold": initial, "reduction": round(initial-threshold, 6),
                      "audit": all_attempts, "geometry_attempts": geometry_attempts})
        return split, zones
    return {"status": "insufficient_data", "initial_threshold": initial, "audit": all_attempts,
            "geometry_attempts": geometry_attempts, "reason": "Counts, retained training or spatial diversity fail within bounded magnitude adaptation."}, None


def fetch_astronomy(root, config, node, budget):
    from astroquery.jplhorizons import Horizons
    from astroquery.jplhorizons import conf
    from horizons import STANDARD_BASE_BODIES
    from uncompressed_pipeline.minor_bodies_fetcher import MINOR_BODIES
    conf.timeout = budget.limits["request_timeout_seconds"]
    cadence = config["interval_days"]
    start = slot_dates(pd.Series([config["training_start"]]), config).iloc[0] - pd.Timedelta(days=13 * cadence)
    end = timestamp(config["reference_date"]) + pd.Timedelta(days=config["horizon_days"] + 14 * cadence)
    observer = "500@399" if node["level"] == 0 else {"lat": node["geometry"]["centroid"][0], "lon": node["geometry"]["centroid"][1], "elevation": 0.0}
    groups = {"main": [{"name": b.name, "command": b.command, "id_type": b.id_type} for b in STANDARD_BASE_BODIES], "minor": MINOR_BODIES}
    output = {}
    for group, bodies in groups.items():
        frames, source_rows = [], []
        for body in bodies:
            request = {"body": body, "observer": observer, "start": str(start.date()), "stop": str(end.date()), "step": f"{cadence}d", "quantities": "1,4,20"}
            key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
            path = Path(root) / "ephemerides" / f"{key}.csv"
            receipt = path.with_suffix(".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and receipt.exists():
                meta = json.loads(receipt.read_text())
                if meta["sha256"] != fingerprint(path):
                    raise RuntimeError("ephemeris_checksum_mismatch")
                frame = pd.read_csv(path, parse_dates=["date"])
            else:
                budget.check("ephemeris")
                budget.record("ephemeris", {"request": request, "status": "requested"})
                raw = Horizons(id=body["command"], id_type=body["id_type"], location=observer,
                               epochs={"start": request["start"], "stop": request["stop"], "step": request["step"]}).ephemerides(quantities=request["quantities"], cache=False).to_pandas()
                frame = pd.DataFrame({"date": pd.to_datetime(raw.datetime_jd, unit="D", origin="julian").dt.round("s")})
                for source, name in [("RA", "ra_app_min"), ("DEC", "dec_app_min"), ("delta", "dist_min"), ("EL", "elev_min")]:
                    if source in raw and pd.to_numeric(raw[source], errors="coerce").notna().all():
                        frame[f"astro_{body['name']}_{name}"] = pd.to_numeric(raw[source])
                frame.to_csv(path, index=False)
                size = path.stat().st_size
                budget.audit["bytes"] += size
                atomic_json(budget.path, budget.audit)
                if budget.audit["bytes"] > budget.limits["maximum_download_bytes"]:
                    raise RuntimeError("download_byte_budget_exhausted")
                atomic_json(receipt, {"request": request, "sha256": fingerprint(path), "rows": len(frame)})
            frames.append(frame.set_index("date"))
            source_rows.append({"file": str(path), "sha256": fingerprint(path), "request": request})
        merged = pd.concat(frames, axis=1).sort_index()
        if merged.isna().any().any():
            raise RuntimeError("incomplete_ephemeris_alignment")
        base_cols = list(merged.columns)
        shifted = {}
        for col in base_cols[:12]:
            for shift in [-13, 13, -4]:
                shifted[f"{col}_shift_{shift}"] = merged[col].shift(shift)
        merged = pd.concat([merged, pd.DataFrame(shifted, index=merged.index)], axis=1)
        merged = merged.loc[(merged.index >= timestamp(config["training_start"])) &
                            (merged.index < timestamp(config["reference_date"]) + pd.Timedelta(days=config["horizon_days"]))]
        if merged.isna().any().any() or not np.isfinite(merged.to_numpy()).all():
            raise RuntimeError("nonfinite_ephemeris_features: no filler or backward imputation permitted")
        output[group] = merged.reset_index()
        atomic_json(Path(root) / "ephemerides" / f"{node['id']}_{group}_manifest.json", source_rows)
    return output
