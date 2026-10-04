#!/usr/bin/env python3
"""Deduce la finestra forecast comune tra piu' CSV sfalsati.

Ogni data nel CSV e' interpretata come INIZIO della finestra temporale.
La fine della finestra e' la data del record successivo; l'ultimo record usa
lo stesso delta del record precedente.
"""

import argparse
import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DATE_COLUMNS = ("date", "context", "timestamp", "time", "window_start", "start")
SCORE_COLUMNS = ("predicted", "pred", "pred_recalibrated", "score", "risk")


def _parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        raise ValueError("data vuota")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:10], "%Y-%m-%d")


def _fmt_dt(value):
    if value.time().isoformat() == "00:00:00":
        return value.date().isoformat()
    return value.isoformat(timespec="seconds")


def _to_float(value, default=0.0):
    try:
        out = float(value)
        if math.isfinite(out):
            return out
    except (TypeError, ValueError):
        pass
    return default


def _pick_column(fieldnames, requested, candidates, label, path):
    if requested and requested != "auto":
        if requested not in fieldnames:
            raise ValueError(f"{path}: colonna {label} richiesta non trovata: {requested}")
        return requested
    for name in candidates:
        if name in fieldnames:
            return name
    raise ValueError(f"{path}: nessuna colonna {label} trovata tra {', '.join(candidates)}")


def _source_label(path):
    parent = Path(path).parent.name
    name = Path(path).stem
    if len(name) > 70:
        name = name[:32] + "..." + name[-28:]
    return f"{parent}/{name}"


def read_forecast_csv(path, *, date_column="auto", score_column="auto", source_label=""):
    path = str(path)
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        dcol = _pick_column(fieldnames, date_column, DATE_COLUMNS, "data", path)
        scol = _pick_column(fieldnames, score_column, SCORE_COLUMNS, "score", path)
        raw_rows = []
        for i, row in enumerate(reader):
            try:
                start = _parse_datetime(row.get(dcol))
            except ValueError:
                continue
            raw_rows.append({
                "row_no": i + 1,
                "start": start,
                "score": _to_float(row.get(scol), 0.0),
                "row": dict(row),
            })
    raw_rows.sort(key=lambda r: r["start"])
    if len(raw_rows) < 2:
        raise ValueError(f"{path}: servono almeno 2 date per dedurre lo step temporale")

    deltas = []
    for prev, cur in zip(raw_rows, raw_rows[1:]):
        delta = cur["start"] - prev["start"]
        if delta.total_seconds() > 0:
            deltas.append(delta)
    if not deltas:
        raise ValueError(f"{path}: date non crescenti, impossibile dedurre lo step")

    intervals = []
    last_delta = deltas[-1]
    for i, item in enumerate(raw_rows):
        if i + 1 < len(raw_rows):
            end = raw_rows[i + 1]["start"]
        else:
            end = item["start"] + last_delta
        if end <= item["start"]:
            continue
        intervals.append({
            "source_path": path,
            "source_label": _source_label(path),
            "row_no": item["row_no"],
            "start": item["start"],
            "end": end,
            "duration_days": (end - item["start"]).total_seconds() / 86400.0,
            "score": item["score"],
            "row": item["row"],
        })
    if not intervals:
        raise ValueError(f"{path}: nessun intervallo valido")
    label = str(source_label or "").strip() or _source_label(path)
    return {
        "path": path,
        "label": label,
        "date_column": dcol,
        "score_column": scol,
        "intervals": intervals,
        "coverage_start": intervals[0]["start"],
        "coverage_end": intervals[-1]["end"],
        "steps_days": [d.total_seconds() / 86400.0 for d in deltas],
    }


def _find_covering(intervals, start, end):
    for item in intervals:
        if item["start"] <= start and item["end"] >= end:
            return item
    return None


def build_common_segments(sources, *, threshold):
    common_start = max(s["coverage_start"] for s in sources)
    common_end = min(s["coverage_end"] for s in sources)
    if common_end <= common_start:
        raise ValueError(
            "Nessuna sovrapposizione comune: "
            f"max start={_fmt_dt(common_start)} min end={_fmt_dt(common_end)}"
        )

    boundaries = {common_start, common_end}
    for source in sources:
        for item in source["intervals"]:
            if common_start < item["start"] < common_end:
                boundaries.add(item["start"])
            if common_start < item["end"] < common_end:
                boundaries.add(item["end"])
    ordered = sorted(boundaries)

    segments = []
    for start, end in zip(ordered, ordered[1:]):
        if end <= start:
            continue
        covers = []
        for source in sources:
            cover = _find_covering(source["intervals"], start, end)
            if cover is None:
                break
            covers.append(cover)
        if len(covers) != len(sources):
            continue
        scores = [float(c["score"]) for c in covers]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        segments.append({
            "window_start": start,
            "window_end": end,
            "duration_days": (end - start).total_seconds() / 86400.0,
            "risk_mean": mean_score,
            "risk_max": max(scores),
            "risk_min": min(scores),
            "risk_std": math.sqrt(variance),
            "consensus_count": sum(1 for s in scores if s >= threshold),
            "source_count": len(scores),
            "covers": covers,
        })
    if not segments:
        raise ValueError("La coverage comune esiste, ma nessun segmento e' coperto da tutti i CSV")
    return common_start, common_end, segments


def write_output_csv(path, segments):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "serial", "window_start", "window_end", "duration_days",
        "risk_mean", "risk_max", "risk_min", "risk_std",
        "consensus_count", "source_count", "source_scores",
        "source_window_starts", "source_window_ends", "source_files",
        "note",
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i, seg in enumerate(segments, start=1):
            writer.writerow({
                "serial": i,
                "window_start": _fmt_dt(seg["window_start"]),
                "window_end": _fmt_dt(seg["window_end"]),
                "duration_days": f"{seg['duration_days']:.6g}",
                "risk_mean": f"{seg['risk_mean']:.12g}",
                "risk_max": f"{seg['risk_max']:.12g}",
                "risk_min": f"{seg['risk_min']:.12g}",
                "risk_std": f"{seg['risk_std']:.12g}",
                "consensus_count": seg["consensus_count"],
                "source_count": seg["source_count"],
                "source_scores": ";".join(f"{c['score']:.12g}" for c in seg["covers"]),
                "source_window_starts": ";".join(_fmt_dt(c["start"]) for c in seg["covers"]),
                "source_window_ends": ";".join(_fmt_dt(c["end"]) for c in seg["covers"]),
                "source_files": ";".join(c["source_label"] for c in seg["covers"]),
                "note": "Each date/point is the start of its forecast time window.",
            })


def _risk_color(value):
    v = max(0.0, min(1.0, float(value)))
    lo = (220, 224, 229)
    hi = (204, 45, 45)
    return tuple(int(lo[i] + (hi[i] - lo[i]) * v) for i in range(3))


def _draw_text(draw, xy, text, fill=(20, 24, 30), font=None):
    draw.text(xy, str(text), fill=fill, font=font)


def _load_font(names, size):
    if isinstance(names, str):
        names = [names]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _text_size(draw, text, font=None):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_text(draw, text, max_width, font=None):
    text = str(text)
    if _text_size(draw, text, font=font)[0] <= max_width:
        return text
    ellipsis = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid] + ellipsis
        if _text_size(draw, candidate, font=font)[0] <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:max(1, lo)] + ellipsis


def _draw_dashed_vline(draw, x, y1, y2, *, fill, dash=8, gap=6, width=1):
    y = y1
    while y < y2:
        draw.line((x, y, x, min(y + dash, y2)), fill=fill, width=width)
        y += dash + gap


def _draw_vertical_text(img, xy, text, *, fill=(20, 24, 30), font=None):
    rot_w, rot_h = _vertical_text_size(text, font=font)
    scratch = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    bbox = scratch_draw.textbbox((0, 0), str(text), font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 10
    txt = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt)
    txt_draw.text((pad - bbox[0], pad - bbox[1]), str(text), fill=fill, font=font)
    rot = txt.rotate(90, expand=True)
    img.paste(rot, (int(xy[0]), int(xy[1])), rot)
    return rot_w, rot_h


def _vertical_text_size(text, font=None):
    scratch = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    bbox = scratch_draw.textbbox((0, 0), str(text), font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 10
    return th + pad * 2, tw + pad * 2


def _draw_double_arrow(draw, x1, x2, y, *, fill=(20, 24, 30), width=2):
    if x2 < x1:
        x1, x2 = x2, x1
    if x2 - x1 < 14:
        return
    draw.line((x1, y, x2, y), fill=fill, width=width)
    ah = 7
    draw.line((x1, y, x1 + ah, y - ah), fill=fill, width=width)
    draw.line((x1, y, x1 + ah, y + ah), fill=fill, width=width)
    draw.line((x2, y, x2 - ah, y - ah), fill=fill, width=width)
    draw.line((x2, y, x2 - ah, y + ah), fill=fill, width=width)


def _draw_diagonal_hatch(draw, x1, y1, x2, y2, *, fill=(40, 44, 52), step=9):
    """Disegna un hatch diagonale dentro il rettangolo dato, senza uscire dai bordi."""
    x1, x2 = int(min(x1, x2)), int(max(x1, x2))
    y1, y2 = int(min(y1, y2)), int(max(y1, y2))
    h = max(0, y2 - y1)
    if x2 <= x1 or h <= 0:
        return
    for x in range(x1 - h, x2 + step, step):
        sx = max(x1, x)
        sy = y1 + max(0, x1 - x)
        ex = min(x2, x + h)
        ey = y1 + (ex - x)
        if sx <= ex and y1 <= sy <= y2 and y1 <= ey <= y2:
            draw.line((sx, sy, ex, ey), fill=fill, width=1)


def _choose_time_markers(segments, common_start, common_end, x_of, *, min_label_px=96):
    raw = sorted({common_start, common_end} |
                 {s["window_start"] for s in segments} |
                 {s["window_end"] for s in segments})
    markers = []
    last_labeled_x = None
    for dt in raw:
        x = x_of(dt)
        show_label = False
        if dt in (common_start, common_end):
            show_label = True
        elif last_labeled_x is None or abs(x - last_labeled_x) >= min_label_px:
            show_label = True
        markers.append({"dt": dt, "x": x, "show_label": show_label})
        if show_label:
            last_labeled_x = x
    return markers


def write_png(path, sources, segments, *, title, common_start, common_end, best_segment):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1760
    left = 440
    right = 82
    top = 178
    row_h = 48
    final_h = 126
    bottom = 205
    height = top + row_h * len(sources) + final_h + bottom
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = _load_font("DejaVuSans.ttf", 17)
    small = _load_font("DejaVuSans.ttf", 13)
    title_font = _load_font("DejaVuSans-Bold.ttf", 24)
    bold = _load_font("DejaVuSans-Bold.ttf", 15)

    total = (common_end - common_start).total_seconds()

    def x_of(dt):
        if total <= 0:
            return left
        frac = (dt - common_start).total_seconds() / total
        return int(left + frac * (width - left - right))

    _draw_text(draw, (32, 26), title, font=title_font)
    _draw_text(
        draw, (32, 66),
        "Each point/date in the source CSV files is the START of its forecast window; the END is the next row date.",
        fill=(70, 76, 86), font=small,
    )
    _draw_text(
        draw, (32, 90),
        f"Common coverage: {_fmt_dt(common_start)} -> {_fmt_dt(common_end)}",
        fill=(70, 76, 86), font=small,
    )

    axis_y = top - 50
    plot_bottom = top + row_h * len(sources) + final_h - 6
    markers = _choose_time_markers(segments, common_start, common_end, x_of)
    label_lanes = [axis_y - 38, axis_y - 20]

    for row_i, source in enumerate(sources):
        y = top + row_i * row_h
        draw.line((left, y + 24, width - right, y + 24), fill=(235, 238, 242), width=1)
        for item in source["intervals"]:
            start = max(item["start"], common_start)
            end = min(item["end"], common_end)
            if end <= start:
                continue
            x1, x2 = x_of(start), x_of(end)
            draw.rectangle((x1, y + 8, max(x1 + 1, x2), y + 36),
                           fill=_risk_color(item["score"]), outline=(255, 255, 255))
        _draw_text(draw, (32, y + 10), source["label"], font=small)

    y = top + row_h * len(sources) + 22
    _draw_text(draw, (32, y + 11), "common fused risk", font=bold)
    draw.line((left, y + 28, width - right, y + 28), fill=(215, 219, 225), width=1)
    for seg in segments:
        x1, x2 = x_of(seg["window_start"]), x_of(seg["window_end"])
        draw.rectangle((x1, y + 4, max(x1 + 1, x2), y + 44),
                       fill=_risk_color(seg["risk_mean"]), outline=(255, 255, 255))
    bx1, bx2 = x_of(best_segment["window_start"]), x_of(best_segment["window_end"])

    draw.line((left, axis_y, width - right, axis_y), fill=(80, 88, 98), width=2)
    for i, marker in enumerate(markers):
        x = marker["x"]
        is_edge = marker["dt"] in (common_start, common_end)
        color = (145, 153, 164) if not is_edge else (76, 84, 96)
        _draw_dashed_vline(draw, x, axis_y + 7, plot_bottom, fill=color,
                           dash=7, gap=6, width=1 if not is_edge else 2)
        draw.line((x, axis_y - 6, x, axis_y + 6), fill=color, width=2)
        if marker["show_label"]:
            label = _fmt_dt(marker["dt"])
            tw, _ = _text_size(draw, label, font=small)
            tx = max(32, min(width - right - tw, x - tw // 2))
            _draw_text(draw, (tx, label_lanes[i % len(label_lanes)]),
                       label, fill=(56, 64, 76), font=small)

    _draw_diagonal_hatch(draw, bx1 + 2, y + 4, max(bx1 + 3, bx2 - 2), y + 44)
    draw.rectangle((bx1, y + 1, max(bx1 + 2, bx2), y + 47), outline=(20, 24, 30), width=3)
    arrow_y = y + 62
    draw.line((bx1, y + 47, bx1, arrow_y - 2), fill=(20, 24, 30), width=2)
    draw.line((bx2, y + 47, bx2, arrow_y - 2), fill=(20, 24, 30), width=2)
    _draw_double_arrow(draw, bx1 + 8, max(bx1 + 16, bx2 - 8), arrow_y,
                       fill=(20, 24, 30), width=2)
    for dt in (best_segment["window_start"], best_segment["window_end"]):
        label = _fmt_dt(dt)
        x = x_of(dt)
        label_w, _ = _vertical_text_size(label, font=small)
        label_x = x - label_w // 2
        _draw_vertical_text(img, (label_x, arrow_y + 30), label, fill=(20, 24, 30), font=small)

    legend_y = height - 112
    _draw_text(
        draw, (32, legend_y),
        "Highest-risk window: "
        f"{_fmt_dt(best_segment['window_start'])} -> {_fmt_dt(best_segment['window_end'])} "
        f"(risk_mean={best_segment['risk_mean']:.3f}, max={best_segment['risk_max']:.3f}, "
        f"consensus={best_segment['consensus_count']}/{best_segment['source_count']})",
        font=bold,
    )
    _draw_text(draw, (32, legend_y + 30), "low risk", fill=(80, 88, 98), font=small)
    lx = 110
    for i in range(120):
        v = i / 119.0
        draw.line((lx + i, legend_y + 38, lx + i, legend_y + 58), fill=_risk_color(v))
    _draw_text(draw, (lx + 132, legend_y + 30), "high risk", fill=(80, 88, 98), font=small)
    _draw_text(
        draw, (32, legend_y + 70),
        "Generated by forecast_common_window.py",
        fill=(120, 126, 136), font=small,
    )
    img.save(path)


def _best_segment(segments):
    return max(
        segments,
        key=lambda s: (
            s["risk_mean"],
            s["risk_max"],
            s["consensus_count"],
            s["duration_days"],
        ),
    )


def main():
    ap = argparse.ArgumentParser(
        description="Deduce the common forecast window across staggered forecast CSV files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("forecast_csvs", nargs="+", help="source forecast CSV files")
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--output-png", default="")
    ap.add_argument("--output-json", default="")
    ap.add_argument("--date-column", default="auto")
    ap.add_argument("--score-column", default="auto")
    ap.add_argument(
        "--source-labels",
        default="",
        help="Optional comma-separated labels for source rows, e.g. 'vertical autoclip,horizontal autoclip'.",
    )
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--title", default="Common detected forecast window")
    args = ap.parse_args()

    labels = [x.strip() for x in args.source_labels.split(",") if x.strip()]
    if labels and len(labels) != len(args.forecast_csvs):
        raise ValueError(
            f"--source-labels has {len(labels)} labels but {len(args.forecast_csvs)} forecast CSVs were provided"
        )
    sources = [
        read_forecast_csv(
            path,
            date_column=args.date_column,
            score_column=args.score_column,
            source_label=labels[i] if labels else "",
        )
        for i, path in enumerate(args.forecast_csvs)
    ]
    common_start, common_end, segments = build_common_segments(
        sources, threshold=args.threshold,
    )
    best = _best_segment(segments)

    output_csv = Path(args.output_csv)
    output_png = Path(args.output_png) if args.output_png else output_csv.with_suffix(".png")
    output_json = Path(args.output_json) if args.output_json else output_csv.with_suffix(".json")
    write_output_csv(output_csv, segments)
    write_png(
        output_png, sources, segments, title=args.title,
        common_start=common_start, common_end=common_end, best_segment=best,
    )

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "note": "Each date/point is the start of its forecast time window.",
        "common_start": _fmt_dt(common_start),
        "common_end": _fmt_dt(common_end),
        "source_count": len(sources),
        "sources": [
            {
                "path": s["path"],
                "label": s["label"],
                "date_column": s["date_column"],
                "score_column": s["score_column"],
                "coverage_start": _fmt_dt(s["coverage_start"]),
                "coverage_end": _fmt_dt(s["coverage_end"]),
                "steps_days": s["steps_days"],
            }
            for s in sources
        ],
        "best_risk_window": {
            "window_start": _fmt_dt(best["window_start"]),
            "window_end": _fmt_dt(best["window_end"]),
            "duration_days": best["duration_days"],
            "risk_mean": best["risk_mean"],
            "risk_max": best["risk_max"],
            "risk_min": best["risk_min"],
            "risk_std": best["risk_std"],
            "consensus_count": best["consensus_count"],
            "source_count": best["source_count"],
        },
        "outputs": {
            "csv": str(output_csv),
            "png": str(output_png),
            "json": str(output_json),
        },
    }
    with open(output_json, "w") as fh:
        json.dump(payload, fh, indent=2)

    print(f"Common window CSV: {output_csv}")
    print(f"Common window PNG: {output_png}")
    print(f"Common window JSON: {output_json}")
    print(
        "Highest-risk window: "
        f"{_fmt_dt(best['window_start'])} -> {_fmt_dt(best['window_end'])} "
        f"(risk_mean={best['risk_mean']:.4f}, risk_max={best['risk_max']:.4f}, "
        f"consensus={best['consensus_count']}/{best['source_count']})."
    )


if __name__ == "__main__":
    main()
