#!/usr/bin/env python3
"""Build event-only spatial masters with bounded, cache-first zone coverage search.

This standalone builder does not import or alter the active production runner.
Validation magnitude may decrease; training magnitude and dates remain explicit.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
import pandas as pd

API = 'https://earthquake.usgs.gov/fdsnws/event/1/'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + '\n')

def utc(value):
    return pd.Timestamp(value).tz_localize('UTC') if pd.Timestamp(value).tzinfo is None else pd.Timestamp(value).tz_convert('UTC')

def events_from(path):
    """Accept an event catalog or an event-rich master; never infer absent events."""
    frame = pd.read_csv(path, low_memory=False)
    aliases = {'time': ['time', 'event_time', 'origin_time'],
               'mag': ['mag', 'event_magnitude', 'magnitude'],
               'latitude': ['latitude', 'event_latitude'],
               'longitude': ['longitude', 'event_longitude'],
               'id': ['id', 'event_id', 'usgs_id']}
    for dest, names in aliases.items():
        found = next((name for name in names if name in frame), None)
        if found and found != dest:
            frame[dest] = frame[found]
    required = ['time', 'mag', 'latitude', 'longitude']
    if not all(name in frame for name in required):
        raise ValueError(f'{path}: not an event-rich source; requires {required}')
    frame['time'] = pd.to_datetime(frame.time, utc=True, errors='coerce')
    for name in required[1:]:
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
    frame = frame.dropna(subset=required).copy()
    frame = frame[frame.mag.gt(0)]
    if 'type' in frame:
        frame = frame[frame['type'].eq('earthquake')]
    if 'id' not in frame:
        frame['id'] = frame[required].astype(str).agg('|'.join, axis=1)
    frame['source_file'] = str(Path(path).resolve())
    return frame

def assign_zones(frame, zones, bbox):
    lo_lat, hi_lat, lo_lon, hi_lon = bbox
    mask = frame.latitude.between(lo_lat, hi_lat) & frame.longitude.between(lo_lon, hi_lon)
    mask &= ~((frame.longitude < 135) & (frame.latitude > 38))
    frame = frame[mask].copy()
    a = np.radians(frame[['latitude', 'longitude']].to_numpy())
    b = np.radians([[z['centroid_lat'], z['centroid_lon']] for z in zones])
    distance = np.sin((a[:, None, 0] - b[None, :, 0]) / 2) ** 2
    distance += np.cos(a[:, None, 0]) * np.cos(b[None, :, 0]) * np.sin((a[:, None, 1] - b[None, :, 1]) / 2) ** 2
    indexes = distance.argmin(axis=1)
    frame['zone_id'] = [zones[i]['zone_id'] for i in indexes]
    frame['zone_name'] = [zones[i]['name'] for i in indexes]
    frame['date'] = frame.time.dt.tz_localize(None).dt.to_period('W-SUN').dt.start_time
    return frame.drop_duplicates('id').sort_values(['time', 'id']).reset_index(drop=True)

class CatalogAccess:
    def __init__(self, args, output, started):
        self.args, self.output, self.started = args, output, started
        self.requests = []

    def request(self, method, params):
        if len(self.requests) >= self.args.max_requests:
            raise RuntimeError('USGS request budget reached')
        remaining = self.args.max_runtime_seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise TimeoutError('Master preparation time budget reached')
        url = API + method + '?' + urlencode(params)
        entry = {'url': url, 'method': method}
        self.requests.append(entry)
        save_json(self.output / 'download_log.json', self.requests)
        with urlopen(url, timeout=min(self.args.request_timeout_seconds, remaining)) as response:
            payload = response.read()
        entry.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        save_json(self.output / 'download_log.json', self.requests)
        return payload

    def fetch(self, start, end, magnitude):
        a = self.args
        params = dict(starttime=start.isoformat(), endtime=end.isoformat(),
                      minmagnitude=magnitude, eventtype='earthquake',
                      minlatitude=a.bbox[0], maxlatitude=a.bbox[1],
                      minlongitude=a.bbox[2], maxlongitude=a.bbox[3])
        count = int(self.request('count', params).strip())
        if count == 0:
            return pd.DataFrame(columns=['time', 'latitude', 'longitude', 'mag', 'id'])
        if count > a.max_events_per_request:
            if end - start < pd.Timedelta(seconds=1):
                raise RuntimeError('USGS count exceeds the limit within a one-second interval')
            middle = start + (end - start) / 2
            return pd.concat([self.fetch(start, middle, magnitude), self.fetch(middle, end, magnitude)]).drop_duplicates('id')
        payload = self.request('query', dict(params, format='csv', orderby='time-asc', limit=a.max_events_per_request))
        file = self.output / f'usgs_chunk_{len(self.requests):03d}_m{magnitude:.1f}.csv'
        file.write_bytes(payload)
        frame = events_from(file)
        if len(frame) != count:
            raise RuntimeError(f'USGS count/query changed: {count} vs {len(frame)}; download retained')
        return frame

def coverage_manifest(path, source_paths, start, end, magnitude, bbox):
    if not path:
        return False
    manifest = json.loads(Path(path).read_text())
    for source in manifest['sources']:
        file = Path(source['path']).resolve()
        if file not in source_paths or digest(file) != source['sha256']:
            continue
        b = source['bbox']
        geographic = b[0] <= bbox[0] and b[1] >= bbox[1] and b[2] <= bbox[2] and b[3] >= bbox[3]
        if geographic and utc(source['start']) <= start and utc(source['end']) >= end and source['min_magnitude'] <= magnitude:
            return True
    return False

def make_weekly(events, zones):
    rows = []
    for date, group in events.groupby('date', sort=True):
        ids = sorted(int(i) for i in group.zone_id.unique())
        row = dict(date=date, event_count=len(group), event_ids=';'.join(group.id.astype(str)),
                   target_zone_ids=';'.join(map(str, ids)),
                   event_magnitude_max=float(group.mag.max()))
        row.update({f'target_Zone_{z["zone_id"]}': int(z['zone_id'] in ids) for z in zones})
        rows.append(row)
    return pd.DataFrame(rows)

def build(args):
    started = time.monotonic()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    data = output / '01_data'; data.mkdir()
    config = vars(args).copy(); save_json(output / 'run_config.json', config)
    try:
        zones = json.loads(Path(args.zones_json).read_text())['zones']
        expected = {int(z['zone_id']) for z in zones}
        assert len(expected) == len(zones) and len(zones) > 1
        end = utc(args.end_time)
        if args.min_time < 7:
            raise ValueError('--min-time is a duration in days and must be at least seven for the weekly feature grid')
        requested_start = end.normalize() - pd.Timedelta(days=args.min_time - 1)
        # Move forward to the first full weekly feature bin, never extend the
        # user-selected time window backward to obtain extra validation events.
        start = requested_start + pd.Timedelta(days=(-requested_start.dayofweek) % 7)
        if not 0 < args.min_download_mag <= args.validation_mag or args.mag_step <= 0:
            raise ValueError('Require 0 < minimum download magnitude <= initial validation magnitude, and a positive step')
        sources, source_paths, rejected = [], set(), []
        for name in args.event_source:
            path = Path(name).resolve()
            try:
                frame = events_from(path); sources.append(frame); source_paths.add(path)
            except (ValueError, OSError) as exc:
                rejected.append({'path': str(path), 'reason': str(exc)})
        empty = pd.DataFrame(columns=['time', 'latitude', 'longitude', 'mag', 'id'])
        empty['time'] = pd.to_datetime(empty.time, utc=True)
        cache = assign_zones(pd.concat(sources, ignore_index=True) if sources else empty, zones, args.bbox)
        access = CatalogAccess(args, data, started)
        decisions = []
        selected = None
        magnitude = args.validation_mag
        while True:
            if time.monotonic() - started > args.max_runtime_seconds:
                raise TimeoutError('Master preparation time budget reached')
            candidate = cache[(cache.time >= start) & (cache.time <= end) & (cache.mag >= magnitude)].copy()
            counts = candidate.groupby('zone_id').size().to_dict()
            covered = all(counts.get(i, 0) >= args.min_events_per_zone for i in expected)
            complete_cache = coverage_manifest(args.cache_coverage, source_paths, start, end, magnitude, args.bbox)
            origin = 'local_event_sources'
            if not covered and not complete_cache:
                fresh = assign_zones(access.fetch(start, end, magnitude), zones, args.bbox)
                candidate = pd.concat([fresh, candidate]).drop_duplicates('id').sort_values('time')
                counts = candidate.groupby('zone_id').size().to_dict()
                covered = all(counts.get(i, 0) >= args.min_events_per_zone for i in expected)
                origin = 'local_sources_plus_bounded_usgs_download'
            decisions.append(dict(magnitude=round(magnitude, 3), source=origin,
                                  complete_cache_coverage=complete_cache,
                                  event_counts={str(i): int(counts.get(i, 0)) for i in sorted(expected)},
                                  all_zones_covered=covered))
            save_json(output / 'selection_audit.json', decisions)
            if covered:
                selected = candidate; break
            if magnitude <= args.min_download_mag + 1e-9:
                raise ValueError('Zone coverage remains incomplete at the minimum download magnitude; no valid master exported')
            magnitude = max(args.min_download_mag, round(magnitude - args.mag_step, 6))
        training = cache[(cache.mag >= args.train_mag) & (cache.time < start)].copy()
        if set(training.zone_id) != expected:
            earliest = max(pd.to_datetime(pd.read_csv(path, usecols=['date']).date).min()
                           for path in [args.main_master, args.minor_master])
            # A missing/unusable local event source falls back to the same bounded
            # regional service. The training magnitude is never reduced.
            fresh = assign_zones(access.fetch(utc(earliest), start-pd.Timedelta(microseconds=1), args.train_mag), zones, args.bbox)
            training = pd.concat([fresh, training]).drop_duplicates('id').sort_values('time')
            if set(training.zone_id) != expected:
                raise ValueError('Training events do not cover every geographic class, even after bounded USGS fallback')
        validation = selected.sort_values(['time', 'id']).reset_index(drop=True)
        validation['validation_event_id'] = np.arange(1, len(validation) + 1)
        assert not set(training.id) & set(validation.id)
        training.to_csv(data / 'training_events.csv', index=False)
        validation.to_csv(data / 'validation_events.csv', index=False)
        weekly = {'training': make_weekly(training, zones), 'validation': make_weekly(validation, zones)}
        assert not set(weekly['training'].date) & set(weekly['validation'].date)
        matrices = []
        for label, path in [('main_bodies_branch', args.main_master), ('minor_bodies_branch', args.minor_master)]:
            base = pd.read_csv(path, low_memory=False); base['date'] = pd.to_datetime(base.date)
            features = [c for c in base if c.startswith(('astro_', 'seis_', 'packed_'))]
            if not features or base.date.duplicated().any():
                raise ValueError('Feature master must have features and one row per week')
            branch = output / label / '01_data'; branch.mkdir(parents=True)
            for split, targets in weekly.items():
                joined = targets.merge(base[['date'] + features], on='date', how='left', validate='one_to_one', indicator=True)
                if not joined['_merge'].eq('both').all():
                    raise ValueError(f'Existing ephemeris grid does not cover all {label}/{split} weeks')
                joined = joined.drop(columns='_merge')
                if not np.isfinite(joined[features].to_numpy(float)).all():
                    raise ValueError('Feature master has missing or infinite values')
                assert joined.event_count.gt(0).all()
                assert joined[[f'target_Zone_{z}' for z in sorted(expected)]].sum(axis=1).gt(0).all()
                joined.to_csv(branch / f'{split}_master.csv', index=False)
                matrices.append(dict(branch=label, split=split, rows=len(joined), events=int(joined.event_count.sum()), features=len(features)))
            forecast = base[base.date.between(pd.Timestamp(args.forecast_start), pd.Timestamp(args.forecast_end))][['date'] + features]
            forecast.to_csv(branch / 'prospective_master.csv', index=False)
        save_json(data / 'spatial_zones_metadata.json', {'zones': zones, 'class_names': [z['name'] for z in zones], 'calm_class': False})
        result = dict(status='masters_complete_models_not_retrained', validation_start=start,
                      requested_window_days=args.min_time, requested_window_start=requested_start,
                      validation_end=end, training_magnitude=args.train_mag, validation_magnitude=magnitude,
                      validation_events=len(validation), validation_weeks=len(weekly['validation']),
                      validation_event_counts={str(k): int(v) for k, v in validation.groupby('zone_id').size().items()},
                      matrices=matrices, download_requests=len(access.requests), jpl_downloads=0,
                      target_representation='one weekly row; multi-hot zone labels; preserve every event in event tables',
                      same_week_multi_zone_validation_rows=int((weekly['validation'].filter(like='target_Zone_').sum(axis=1)>1).sum()),
                      rejected_cache_sources=rejected,
                      input_hashes={str(p): digest(p) for p in source_paths | {Path(args.zones_json).resolve(), Path(args.main_master).resolve(), Path(args.minor_master).resolve()}},
                      elapsed_seconds=time.monotonic()-started)
        save_json(output / 'master_manifest.json', result)
        (output / 'README.md').write_text('# Event-only spatial masters\n\n'
            f'Validation dates: {start} to {end}. No backward extension. Training magnitude remains M{args.train_mag:g}; validation magnitude is M{magnitude:g}.\n\n'
            f'Validation: {len(validation)} earthquakes in {len(weekly["validation"])} weeks; counts per zone: {result["validation_event_counts"]}.\n\n'
            'All training and validation rows contain real catalog events. There is no Calm target or quiescence metric. '
            'Five multi-hot zone targets retain weeks with earthquakes in more than one zone. '
            'The event CSVs retain origin time, coordinates, magnitude and catalog ID.\n\n'
            f'Existing feature matrices were reused: JPL downloads = 0; USGS requests during this build = {len(access.requests)}. '
            'Lowering the validation threshold does not change the training threshold, energy master or zone definitions.\n\n'
            'These are rebuilt masters, not newly trained forecasts. The old six-class Calm model is incompatible and must not consume them unchanged. '
            'The lower-magnitude validation population is explicit in run_config.json and master_manifest.json.\n\n'
            'selection_audit.json records every threshold and the coverage decision. Input hashes and cache provenance are retained.\n')
        return result
    except Exception as exc:
        save_json(output / 'failure.json', {'status': 'not_complete', 'error': str(exc)})
        raise

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--event-source', action='append', default=[], help='Local catalog/event-rich master CSV; repeat to combine sources; use USGS fallback if unavailable')
    p.add_argument('--cache-coverage', help='Coverage and SHA-256 manifest proving completeness of local event sources')
    p.add_argument('--main-master', required=True)
    p.add_argument('--minor-master', required=True)
    p.add_argument('--zones-json', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--min-time', type=int, required=True, metavar='DAYS', help='Validation lookback duration in days (e.g. 1095), ending at --end-time; no automatic backward extension')
    p.add_argument('--end-time', required=True)
    p.add_argument('--validation-mag', type=float, default=6.8)
    p.add_argument('--train-mag', type=float, default=6.8)
    p.add_argument('--min-download-mag', type=float, required=True, help='Hard lower bound for automatic validation magnitude search')
    p.add_argument('--mag-step', type=float, default=.1)
    p.add_argument('--min-events-per-zone', type=int, default=1)
    p.add_argument('--bbox', type=float, nargs=4, default=[28, 47, 128, 149.5], metavar=('MIN_LAT','MAX_LAT','MIN_LON','MAX_LON'))
    p.add_argument('--forecast-start', default='2026-08-01')
    p.add_argument('--forecast-end', default='2027-01-31')
    p.add_argument('--max-events-per-request', type=int, default=19000)
    p.add_argument('--max-requests', type=int, default=40)
    p.add_argument('--request-timeout-seconds', type=float, default=30)
    p.add_argument('--max-runtime-seconds', type=float, default=300)
    return p

if __name__ == '__main__':
    args = parser().parse_args()
    if not 1 <= args.max_events_per_request < 20000 or args.min_events_per_zone < 1:
        raise SystemExit('Require at least one event per zone and a download batch below 20000 events')
    print(json.dumps(build(args), indent=2, default=str))
