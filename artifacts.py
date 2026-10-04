"""
Export dei trial migliori: CSV + PNG con titolo, date e naming leggibile.
"""
import csv
import json
import math
import os
import re
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


def timestamp_slug():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_slug(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-") or "item"


def get_pipeline_serial():
    if "DLVSWAVE_SERIAL" in os.environ:
        return os.environ["DLVSWAVE_SERIAL"]
    
    from pathlib import Path
    serial_file = Path("/mnt/git0/git/repository/DLvsWAVE/.pipeline_serial")
    try:
        if serial_file.exists():
            val = int(serial_file.read_text().strip())
        else:
            val = 0
    except Exception:
        val = 0
    val += 1
    try:
        serial_file.write_text(str(val))
    except Exception:
        pass
    ser_str = f"{val:03d}"
    os.environ["DLVSWAVE_SERIAL"] = ser_str
    return ser_str


def ensure_run_dir(dataset_path, command_name, stamp, parent_dir=None, level=None):
    if parent_dir is not None and level is not None and int(level) > 0:
        run_dir = os.path.join(parent_dir, f"L{int(level):02d}")
    else:
        dataset_dir = os.path.dirname(os.path.abspath(dataset_path))
        serial = get_pipeline_serial()
        suffix = f"_{serial}"
        if not stamp.endswith(suffix):
            stamp = f"{stamp}{suffix}"
        run_dir = os.path.join(dataset_dir, f"pulsar_{safe_slug(command_name)}_best_trials_{stamp}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return str(value)


def write_json(path, payload):
    with open(path, "w") as f:
        json.dump(json_safe(payload), f, indent=2, sort_keys=True)


def write_run_signature(run_dir, payload):
    path = os.path.join(run_dir, "run_signature.json")
    write_json(path, payload)
    return path


def write_run_index_csv(run_dir, rows):
    path = os.path.join(run_dir, "best_trials_index.csv")
    if not rows:
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(["task"])
        return path
    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            encoded = {}
            for k in fieldnames:
                v = row.get(k)
                if isinstance(v, (dict, list, tuple)):
                    encoded[k] = json.dumps(json_safe(v), sort_keys=True)
                else:
                    encoded[k] = v
            w.writerow(encoded)
    return path


def _font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _format_context_label(value):
    if value is None:
        return ""
    text = str(value).strip()
    return text[:24] if len(text) > 24 else text


def _looks_like_date_label(value):
    text = str(value or "").strip()
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$", text))


def _context_looks_temporal(values):
    if values is None:
        return False
    checked = 0
    matches = 0
    for value in values:
        if value is None or str(value).strip() == "":
            continue
        checked += 1
        if _looks_like_date_label(value):
            matches += 1
        if checked >= 8:
            break
    return checked > 0 and matches == checked


def _format_score(score):
    return f"{float(score):.3f}"


def _series_range(values):
    numeric = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not numeric:
        return 0.0, 1.0
    vmin = min(numeric)
    vmax = max(numeric)
    if abs(vmax - vmin) < 1e-12:
        pad = max(abs(vmax) * 0.05, 1.0)
        return vmin - pad, vmax + pad
    pad = (vmax - vmin) * 0.08
    return vmin - pad, vmax + pad


def _resolve_plot_range(context_values, indices):
    if context_values is None or indices is None or len(indices) == 0:
        return None
    first = _format_context_label(context_values[int(indices[0])])
    last = _format_context_label(context_values[int(indices[-1])])
    return f"{first} -> {last}"


def _model_detail_label(result):
    extra = result.get("extra", {}) or {}
    if result.get("bank") == "__hybrid__":
        cfg = extra.get("hybrid_cfg", {}) or {}
        partner = cfg.get("partner", {}) or {}
        if partner.get("kind") == "deep":
            partner_label = f"deep:{partner.get('preset')}"
        else:
            partner_label = f"{partner.get('bank')}:{partner.get('readout')}"
        mode = str(cfg.get("mode", ""))
        bits = [
            f"LCS={cfg.get('lcs_label')}",
            f"partner={partner_label}",
            f"mode={mode}",
        ]
        if mode == "weighted":
            bits.append(f"alpha={cfg.get('alpha')}")
            bits.append(f"thr={cfg.get('hybrid_threshold')}")
        return "hybrid " + " ".join(bits)
    if result.get("bank") == "__none__":
        cfg = extra.get("deep_cfg", {}) or {}
        hidden = cfg.get("hidden_sizes", "auto")
        return f"DeepNet hidden={hidden} act={cfg.get('activation')} epochs={cfg.get('epochs')}"
    if result.get("bank") == "__lcs__":
        cfg = extra.get("lcs_cfg", {}) or {}
        return (f"LCS pop={cfg.get('population_size')} epochs={cfg.get('epochs')} "
                f"thr={cfg.get('binary_threshold')}")
    if result.get("bank") == "__kan__":
        cfg = extra.get("kan_cfg", {}) or {}
        return (f"KAN width={cfg.get('hidden_width')} grid={cfg.get('grid')} "
                f"epochs={cfg.get('epochs')}")
    if result.get("bank") == "__kan_hybrid__":
        cfg = extra.get("kan_hybrid_cfg", {}) or {}
        partner = cfg.get("partner", {}) or {}
        if partner.get("kind") == "deep":
            partner_label = f"deep:{partner.get('preset')}"
        else:
            partner_label = f"{partner.get('bank')}:{partner.get('readout')}"
        return (f"KAN hybrid KAN={cfg.get('kan_label')} partner={partner_label} "
                f"mode={cfg.get('mode')}")
    return ""


def _plot_title(result, plot_kind, indices, csv_meta):
    if result["bank"] == "__none__":
        bank = "end_to_end"
    elif result["bank"] == "__lcs__":
        bank = "lcs"
    elif result["bank"] == "__hybrid__":
        bank = "hybrid"
    elif result["bank"] == "__kan__":
        bank = "kan"
    elif result["bank"] == "__kan_hybrid__":
        bank = "kan_hybrid"
    else:
        bank = result["bank"]
    readout = result["readout"]
    score = _format_score(result.get("overall_kpi", 0.0))
    extra = result.get("extra", {})
    count = 0 if indices is None else len(indices)
    model_detail = _model_detail_label(result)

    if plot_kind == "test":
        split_info = extra.get("split_info", {}) or {}
        parts = [f"TEST | {bank}/{readout}", f"score={score}", f"rows={count}"]
        used_events = split_info.get("used_event_count")
        if used_events is not None:
            parts.append(f"events={used_events}")
        subtitle = _resolve_plot_range(csv_meta.get("context_values"), indices)
        if subtitle and _context_looks_temporal(_slice_context(csv_meta.get("context_values"), indices)):
            subtitle = f"{subtitle} | point dates = period start"
        if model_detail:
            subtitle = f"{subtitle} | {model_detail}" if subtitle else model_detail
        return "  ".join(parts), subtitle

    forecast_info = extra.get("forecast_info", {}) or {}
    parts = [f"FORECAST | {bank}/{readout}", f"score={score}", f"rows={count}"]
    requested_start = forecast_info.get("requested_start")
    requested_end = forecast_info.get("requested_end")
    subtitle = _resolve_plot_range(csv_meta.get("context_values"), indices)
    if subtitle and _context_looks_temporal(_slice_context(csv_meta.get("context_values"), indices)):
        subtitle = f"{subtitle} | point dates = period start"
    if not subtitle and requested_start:
        if requested_end:
            subtitle = f"{requested_start} -> {requested_end}"
        else:
            subtitle = requested_start
    if model_detail:
        subtitle = f"{subtitle} | {model_detail}" if subtitle else model_detail
    return "  ".join(parts), subtitle


def _autoscale_pred_to_actual(y_true, y_pred):
    """Rescala linearmente y_pred nel min-max di y_true, preservando la forma.
    Se y_true e' costante (es. forecast tutto-zero) o vuota, restituisce y_pred
    invariato cosi' la curva predetta resta visibile in scala nativa."""
    yt = [float(v) for v in y_true if v is not None and math.isfinite(float(v))]
    yp = [float(v) for v in y_pred if v is not None and math.isfinite(float(v))]
    if not yt or not yp:
        return list(y_pred)
    t_min, t_max = min(yt), max(yt)
    if abs(t_max - t_min) < 1e-12:
        # actual costante: nessuna informazione di ampiezza, lascia pred nativo
        return list(y_pred)
    p_min, p_max = min(yp), max(yp)
    if abs(p_max - p_min) < 1e-12:
        mid = 0.5 * (t_min + t_max)
        return [mid for _ in y_pred]
    out = []
    for v in y_pred:
        if v is None or not math.isfinite(float(v)):
            out.append(None)
            continue
        norm = (float(v) - p_min) / (p_max - p_min)
        out.append(t_min + norm * (t_max - t_min))
    return out


def location_display_meta(csv_meta):
    """Return location target metadata when plots/CSVs should use physical values."""
    if not isinstance(csv_meta, dict):
        return None
    meta = csv_meta.get("location_target_meta")
    if not isinstance(meta, dict):
        return None
    if meta.get("mode") != "analog":
        return None
    if meta.get("target_name") != csv_meta.get("target_col"):
        return None
    if meta.get("analog_scale") != "minmax":
        return None
    try:
        float(meta["clip_min"])
        float(meta["clip_max"])
    except Exception:
        return None
    return meta


def is_location_analog_display(csv_meta):
    return location_display_meta(csv_meta) is not None


def _decode_location_value(value, meta, *, actual=False):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    fill = meta.get("forecast_target_fill", None)
    if actual and fill is not None:
        try:
            if abs(v - float(fill)) < 1e-12:
                return None
        except (TypeError, ValueError):
            pass
    lo = float(meta["clip_min"])
    hi = float(meta["clip_max"])
    clipped = max(0.0, min(1.0, v))
    return lo + clipped * (hi - lo)


def decode_location_series(csv_meta, values, *, actual=False):
    meta = location_display_meta(csv_meta)
    raw = _as_list(values)
    if meta is None:
        return raw
    return [_decode_location_value(v, meta, actual=actual) for v in raw]


def location_display_subtitle(csv_meta):
    meta = location_display_meta(csv_meta)
    if meta is None:
        return ""
    target = meta.get("target_source") or csv_meta.get("target_col") or "target"
    lo = float(meta["clip_min"])
    hi = float(meta["clip_max"])
    return f"{target} decoded to original units [{lo:.6g}..{hi:.6g}]"


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return [value]


def _wrap_lines_for_width(draw, text, font, max_width, max_lines):
    words = str(text or "").split()
    if not words:
        return []
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1]:
            candidate = lines[-1].rstrip(".") + " ..."
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                lines[-1] = candidate
                break
            lines[-1] = lines[-1][:-1].rstrip()
        if not lines[-1]:
            lines[-1] = "..."
    return lines


def _draw_fit_text_block(draw, xy, text, fill, *, base_size, min_size,
                         max_width, max_lines, line_gap=2):
    x, y = xy
    text = str(text or "").strip()
    if not text:
        return y
    chosen_font = _font(min_size)
    chosen_lines = []
    for size in range(int(base_size), int(min_size) - 1, -1):
        font = _font(size)
        lines = _wrap_lines_for_width(draw, text, font, max_width, max_lines)
        if len(lines) <= max_lines:
            chosen_font = font
            chosen_lines = lines
            break
    if not chosen_lines:
        chosen_lines = _wrap_lines_for_width(draw, text, chosen_font, max_width, max_lines)
    line_h = draw.textbbox((0, 0), "Ag", font=chosen_font)[3] + line_gap
    yy = y
    for line in chosen_lines:
        draw.text((x, yy), line, fill=fill, font=chosen_font)
        yy += line_h
    return yy


def _draw_panel(draw, frame_box, panel_spec, *, title_font, body_font, small_font,
                actual_c, pred_c, axis, grid, text_c, muted_c, autoscale=True,
                separator_dashed=True, compact_x_labels=False):
    """Disegna un pannello dentro frame_box=(left, top, right, bottom).

    panel_spec = {
      'title': str,
      'subtitle': str,
      'segments': [
        {'label': str, 'y_true': [...], 'y_pred': [...], 'context': [...] | None}
        ...
      ],
      'separator_indices': [list di indici dove disegnare la linea tratteggiata]
    }
    """
    fl, ft, fr, fb = frame_box
    panel_spec["_rotated_labels"] = []
    # cornice esterna
    draw.rectangle((fl, ft, fr, fb), outline=axis, width=2)

    title = panel_spec.get("title", "")
    subtitle = panel_spec.get("subtitle", "")
    legend_w = 220
    header_max_w = max(240, (fr - fl) - legend_w - 38)
    header_bottom = ft + 6
    if title:
        header_bottom = _draw_fit_text_block(
            draw, (fl + 10, ft + 6), title, text_c,
            base_size=getattr(title_font, "size", 22), min_size=15,
            max_width=header_max_w, max_lines=2, line_gap=2,
        )
    if subtitle:
        header_bottom = _draw_fit_text_block(
            draw, (fl + 10, header_bottom + 2), subtitle, muted_c,
            base_size=getattr(body_font, "size", 14), min_size=10,
            max_width=header_max_w, max_lines=2, line_gap=1,
        )

    # plot area dentro la cornice
    plot_left = fl + 80
    plot_right = fr - 20
    plot_top = max(ft + 70, header_bottom + 10)
    temporal_context = _context_looks_temporal([
        value
        for seg in panel_spec.get("segments", [])
        for value in (seg.get("context") or [])
    ])

    if compact_x_labels:
        plot_bottom = fb - (100 if temporal_context else 20)
    else:
        plot_bottom = fb - (130 if temporal_context else 90)
    plot_w = max(1, plot_right - plot_left)
    plot_h = max(1, plot_bottom - plot_top)

    # raccoglie i dati
    segments = panel_spec.get("segments", [])
    full_y_true = []
    full_y_pred_orig = []
    full_y_pred = []
    full_context = []
    seg_boundaries = []  # indice cumulativo del primo elemento di ogni segmento (esclusi 0)
    for seg in segments:
        yt = [float(v) for v in seg.get("y_true", []) if v is not None]
        yp = [float(v) for v in seg.get("y_pred", []) if v is not None]
        ctx = seg.get("context") or [None] * max(len(yt), len(yp))
        n_seg = min(len(yt), len(yp))
        if n_seg == 0:
            # forecast senza y_true: usa solo y_pred
            yt_seg = []
            yp_seg = [float(v) for v in seg.get("y_pred", []) if v is not None]
            n_seg = len(yp_seg)
        else:
            yt_seg = yt[:n_seg]
            yp_seg = yp[:n_seg]
        if autoscale and yt_seg and yp_seg:
            yp_scaled = _autoscale_pred_to_actual(yt_seg, yp_seg)
        else:
            yp_scaled = list(yp_seg)
        if full_y_true:
            seg_boundaries.append(len(full_y_true) if yt_seg else len(full_y_pred))
        full_y_true.extend(yt_seg)
        full_y_pred_orig.extend(yp_seg)
        full_y_pred.extend(yp_scaled)
        full_context.extend(ctx[:max(len(yt_seg), len(yp_seg))])

    n = max(len(full_y_true), len(full_y_pred))
    if n == 0:
        draw.text((plot_left + 10, plot_top + 10), "No data", fill=muted_c, font=body_font)
        return

    # actual e' "informativa" solo se ha almeno 2 valori distinti
    actual_unique = {round(float(v), 12) for v in full_y_true if v is not None}
    actual_meaningful = len(actual_unique) > 1

    pool = []
    if full_y_true and actual_meaningful:
        pool.extend(full_y_true)
    if full_y_pred:
        pool.extend(full_y_pred)
    vmin, vmax = _series_range(pool)

    # gridlines
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = plot_top + int(round((1.0 - frac) * plot_h))
        draw.line((plot_left, y, plot_right, y), fill=grid, width=1)
        value = vmin + frac * (vmax - vmin)
        draw.text((fl + 6, y - 9), f"{value:.3f}", fill=muted_c, font=small_font)

    if temporal_context:
        for pos in range(len(full_context)):
            x = plot_left + (int(round(pos * plot_w / max(len(full_context) - 1, 1))) if len(full_context) > 1 else plot_w // 2)
            draw.line((x, plot_top, x, plot_bottom), fill=grid, width=1)

    draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill=axis, width=2)
    draw.line((plot_left, plot_top, plot_left, plot_bottom), fill=axis, width=2)

    def to_xy(i, value):
        if n <= 1:
            x = plot_left + plot_w // 2
        else:
            x = plot_left + int(round(i * plot_w / (n - 1)))
        y_norm = (float(value) - vmin) / max(vmax - vmin, 1e-12)
        y = plot_bottom - int(round(y_norm * plot_h))
        return x, y

    # linea actual + predicted (allineate per indice)
    if full_y_true and actual_meaningful:
        pts_true = [to_xy(i, full_y_true[i]) for i in range(len(full_y_true))]
        if len(pts_true) > 1:
            draw.line(pts_true, fill=actual_c, width=3)
        marker_r = 6 if len(pts_true) == 1 else 3
        for x, y in pts_true:
            draw.ellipse((x - marker_r, y - marker_r, x + marker_r, y + marker_r),
                         fill=actual_c, outline=actual_c)
    if full_y_pred:
        pts_pred = [to_xy(i, full_y_pred[i]) for i in range(len(full_y_pred))]
        if len(pts_pred) > 1:
            draw.line(pts_pred, fill=pred_c, width=3)
        marker_r = 6 if len(pts_pred) == 1 else 3
        for x, y in pts_pred:
            draw.ellipse((x - marker_r, y - marker_r, x + marker_r, y + marker_r),
                         fill=pred_c, outline=pred_c)

    # separator tratteggiato fra segmenti
    if separator_dashed:
        for sep_idx in seg_boundaries:
            if 0 < sep_idx < n:
                x = plot_left + (int(round(sep_idx * plot_w / max(n - 1, 1))) if n > 1 else plot_w // 2)
                # tratteggio verticale 6px on, 6px off
                seg_y = plot_top
                while seg_y < plot_bottom:
                    seg_end = min(seg_y + 6, plot_bottom)
                    draw.line((x, seg_y, x, seg_end), fill=muted_c, width=1)
                    seg_y += 12

    # legenda
    legend_x = fr - 200
    legend_y = ft + 8
    if full_y_true and actual_meaningful:
        draw.line((legend_x, legend_y + 12, legend_x + 30, legend_y + 12), fill=actual_c, width=4)
        draw.text((legend_x + 38, legend_y + 2), "actual", fill=text_c, font=small_font)
    draw.line((legend_x, legend_y + 30, legend_x + 30, legend_y + 30), fill=pred_c, width=4)
    draw.text((legend_x + 38, legend_y + 20), "predicted", fill=text_c, font=small_font)
    if autoscale and full_y_true and actual_meaningful and full_y_pred_orig:
        op_min = min(full_y_pred_orig)
        op_max = max(full_y_pred_orig)
        draw.text((legend_x, legend_y + 42),
                  f"autoscale: pred [{op_min:.3g}..{op_max:.3g}]",
                  fill=muted_c, font=small_font)

    # date per i punti temporali: ogni punto ha una linea verticale; le label
    # sono tutte presenti quando lo spazio lo permette, altrimenti campionate.
    n_labels = len(full_context)
    if n_labels > 0 and compact_x_labels and temporal_context:
        approx_label_w = 56
        step = max(1, int(math.ceil((n_labels * approx_label_w) / max(plot_w * 1.15, 1))))
        label_positions = list(range(0, n_labels, step))
        if (n_labels - 1) not in label_positions:
            label_positions.append(n_labels - 1)
        for pos in label_positions:
            label = _format_context_label(full_context[pos]) if full_context[pos] is not None else ""
            if not label:
                continue
            x_anchor = plot_left + (int(round(pos * plot_w / max(n_labels - 1, 1))) if n_labels > 1 else plot_w // 2)
            txt_img = Image.new("RGBA", (small_font.size * len(label), small_font.size + 4), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(txt_img)
            tdraw.text((0, 0), label, fill=muted_c + (255,), font=small_font)
            rotated = txt_img.rotate(90, expand=True)
            rw, _ = rotated.size
            paste_x = int(x_anchor - rw / 2)
            paste_y = plot_bottom + 6
            panel_spec.setdefault("_rotated_labels", []).append((rotated, paste_x, paste_y))
    elif n_labels > 0 and not compact_x_labels:
        if temporal_context:
            step = max(1, int(math.ceil((n_labels * 12) / max(plot_w, 1))))
        else:
            step = max(1, int(round(n_labels * 8 / max(plot_w, 1))))
        for pos in range(0, n_labels, step):
            label = _format_context_label(full_context[pos]) if full_context[pos] is not None else ""
            if not label:
                continue
            x_anchor = plot_left + (int(round(pos * plot_w / max(n_labels - 1, 1))) if n_labels > 1 else plot_w // 2)
            # disegna verticale: ruoto il testo creando un'immagine separata e incollando
            txt_img = Image.new("RGBA", (small_font.size * len(label), small_font.size + 4), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(txt_img)
            tdraw.text((0, 0), label, fill=muted_c + (255,), font=small_font)
            rotated = txt_img.rotate(90, expand=True)
            rw, rh = rotated.size
            paste_x = int(x_anchor - rw / 2)
            paste_y = plot_bottom + 6
            # converto draw target ad RGBA per blend? PIL Image.paste richiede l'immagine PIL
            # qui passo la posizione a chi gestisce il paste (vedi caller)
            panel_spec.setdefault("_rotated_labels", []).append((rotated, paste_x, paste_y))
    if temporal_context and not compact_x_labels:
        draw.text((plot_left, fb - 18), "point dates = period start",
                  fill=muted_c, font=small_font)


def write_combined_panels_png(path, panels, *, autoscale=True):
    """Compone un PNG con piu' pannelli verticali, ciascuno in una propria cornice.

    panels: lista di panel_spec (vedi _draw_panel).
    """
    width = 1500
    n_panels = max(1, len(panels))
    panel_h = 520
    margin_top = 40
    margin_between = 36
    margin_bottom = 30
    height = margin_top + n_panels * panel_h + (n_panels - 1) * margin_between + margin_bottom

    bg = (255, 255, 255)
    axis = (150, 158, 168)
    grid = (235, 238, 242)
    actual_c = (31, 102, 214)
    pred_c = (220, 60, 60)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title_font = _font(22)
    body_font = _font(14)
    small_font = _font(11)

    rotated_to_paste = []
    for idx, panel in enumerate(panels):
        ft = margin_top + idx * (panel_h + margin_between)
        fb = ft + panel_h
        fl = 20
        fr = width - 20
        _draw_panel(draw, (fl, ft, fr, fb), panel,
                    title_font=title_font, body_font=body_font, small_font=small_font,
                    actual_c=actual_c, pred_c=pred_c, axis=axis, grid=grid,
                    text_c=text_c, muted_c=muted_c, autoscale=autoscale)
        for rot, px, py in panel.get("_rotated_labels", []):
            rotated_to_paste.append((rot, px, py))

    # paste delle etichette ruotate
    for rot, px, py in rotated_to_paste:
        image.paste(rot, (px, py), rot)

    image.save(path)


def write_collage_png(path, tiles, *, best_indices=None, worst_indices=None,
                      autoscale=True, columns=2):
    """Layout a griglia (2 colonne di default) di mini-card.

    tiles = [{'title', 'subtitle', 'validation_panel', 'forecast_panel'}, ...]
    best_indices / worst_indices: insiemi di indici con bordo evidenziato
    (verde per best, rosso per worst). Le altre tile hanno bordo neutro.
    """
    best_indices = set(best_indices or [])
    worst_indices = set(worst_indices or [])
    cols = max(1, int(columns))
    n = max(1, len(tiles))
    rows = (n + cols - 1) // cols

    tile_w = 760
    tile_h = 660
    gap_x = 20
    gap_y = 24
    margin = 28
    width = margin * 2 + cols * tile_w + (cols - 1) * gap_x
    height = margin * 2 + rows * tile_h + (rows - 1) * gap_y

    bg = (255, 255, 255)
    axis = (150, 158, 168)
    grid = (235, 238, 242)
    actual_c = (31, 102, 214)
    pred_c = (220, 60, 60)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)
    border_best = (40, 160, 70)
    border_worst = (210, 50, 50)
    border_neutral = (200, 205, 212)

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title_font = _font(18)
    body_font = _font(13)
    small_font = _font(10)

    rotated_to_paste = []
    for i, tile in enumerate(tiles):
        col = i % cols
        row = i // cols
        x0 = margin + col * (tile_w + gap_x)
        y0 = margin + row * (tile_h + gap_y)
        x1 = x0 + tile_w
        y1 = y0 + tile_h

        if i in best_indices:
            border_color = border_best
            border_width = 8
        elif i in worst_indices:
            border_color = border_worst
            border_width = 8
        else:
            border_color = border_neutral
            border_width = 2
        for off in range(border_width):
            draw.rectangle((x0 + off, y0 + off, x1 - off, y1 - off),
                           outline=border_color)

        title_h = 42
        title_text = tile.get("title", "")
        subtitle_text = tile.get("subtitle", "")
        draw.text((x0 + 14, y0 + 8), title_text, fill=text_c, font=title_font)
        if subtitle_text:
            draw.text((x0 + 14, y0 + 26), subtitle_text, fill=muted_c, font=small_font)

        val_panel = tile.get("validation_panel")
        fc_panel = tile.get("forecast_panel")
        inner_top = y0 + title_h
        inner_bottom = y1 - 8
        inner_h = inner_bottom - inner_top
        if val_panel and fc_panel:
            v_top = inner_top
            v_bottom = inner_top + int(inner_h * 0.6) - 4
            f_top = v_bottom + 8
            f_bottom = inner_bottom
        elif val_panel:
            v_top = inner_top
            v_bottom = inner_bottom
            f_top = f_bottom = None
        else:
            v_top = v_bottom = None
            f_top = inner_top
            f_bottom = inner_bottom

        if val_panel and v_top is not None:
            _draw_panel(
                draw, (x0 + 14, v_top, x1 - 14, v_bottom), val_panel,
                title_font=title_font, body_font=body_font, small_font=small_font,
                actual_c=actual_c, pred_c=pred_c, axis=axis, grid=grid,
                text_c=text_c, muted_c=muted_c, autoscale=autoscale,
            )
            for rot, px, py in val_panel.get("_rotated_labels", []):
                rotated_to_paste.append((rot, px, py))
        if fc_panel and f_top is not None:
            _draw_panel(
                draw, (x0 + 14, f_top, x1 - 14, f_bottom), fc_panel,
                title_font=title_font, body_font=body_font, small_font=small_font,
                actual_c=actual_c, pred_c=pred_c, axis=axis, grid=grid,
                text_c=text_c, muted_c=muted_c, autoscale=autoscale,
                compact_x_labels=True,
            )
            for rot, px, py in fc_panel.get("_rotated_labels", []):
                rotated_to_paste.append((rot, px, py))

    for rot, px, py in rotated_to_paste:
        image.paste(rot, (px, py), rot)

    image.save(path)


def write_all_trials_validation_csv(path, rows, csv_meta=None):
    """Scrive un unico CSV accodato di tutti i trial selezionati.

    Ogni elemento in `rows` corrisponde a un (trial, segments). Schema:
      trial_serial, trial_id, rank, bank, readout, seed, kpi_mean, segment,
      date, row_index, actual, predicted, pred_recalibrated, error,
      error_recalibrated
    """
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trial_serial", "trial_id", "rank", "bank", "readout",
                    "seed", "kpi_mean", "segment", "date", "row_index",
                    "actual", "predicted", "pred_recalibrated",
                    "error", "error_recalibrated"])
        for entry in rows or []:
            trial_serial = entry.get("trial_serial", "")
            trial_id = entry.get("trial_id", "")
            rank = entry.get("rank")
            bank = entry.get("bank")
            readout = entry.get("readout")
            seed = entry.get("seed")
            kpi_mean = entry.get("kpi_mean")
            for seg in entry.get("segments", []) or []:
                label = str(seg.get("label", ""))
                indices = seg.get("indices") or []
                contexts = seg.get("context") or [None] * len(indices)
                row_indices = seg.get("row_indices") or [None] * len(indices)
                yt = list(seg.get("y_true") or [])
                yp = list(seg.get("y_pred") or [])
                n_seg = min(len(indices), len(yt), len(yp))
                if n_seg <= 0:
                    continue
                if location_display_meta(csv_meta) is not None:
                    yt_out = decode_location_series(csv_meta, yt[:n_seg], actual=True)
                    yp_out = decode_location_series(csv_meta, yp[:n_seg], actual=False)
                    pred_rescaled = list(yp_out)
                else:
                    yt_out = list(yt[:n_seg])
                    yp_out = list(yp[:n_seg])
                    yt_finite = [float(v) for v in yt_out if v is not None]
                    yp_finite = [float(v) for v in yp_out if v is not None]
                    pred_rescaled = (
                        _autoscale_pred_to_actual(yt_finite, yp_finite)
                        if yt_finite and yp_finite else list(yp_finite)
                    )
                rescaled_iter = iter(pred_rescaled)
                for i in range(n_seg):
                    actual = yt_out[i]
                    pred = yp_out[i]
                    actual_f = float(actual) if actual is not None else None
                    pred_f = float(pred) if pred is not None else None
                    pred_rec = (next(rescaled_iter, pred_f)
                                if pred is not None else None)
                    pred_rec_f = float(pred_rec) if pred_rec is not None else None
                    err = ((pred_f - actual_f)
                           if (pred_f is not None and actual_f is not None) else "")
                    err_rec = ((pred_rec_f - actual_f)
                               if (pred_rec_f is not None and actual_f is not None) else "")
                    w.writerow([
                        trial_serial, trial_id, rank, bank, readout, seed, kpi_mean,
                        label,
                        contexts[i] if i < len(contexts) else "",
                        row_indices[i] if i < len(row_indices) and row_indices[i] is not None
                            else int(indices[i]),
                        actual_f if actual_f is not None else "",
                        pred_f if pred_f is not None else "",
                        pred_rec_f if pred_rec_f is not None else "",
                        err, err_rec,
                    ])


def write_series_png(path, y_true, y_pred, *, context_values=None, indices=None,
                     title="", subtitle=""):
    indexed_context = None
    if context_values is not None and indices is not None:
        try:
            indexed_context = [context_values[int(idx)] for idx in indices]
        except (TypeError, ValueError, IndexError):
            indexed_context = None
    temporal_context = _context_looks_temporal(indexed_context)

    width, height = 1400, 820 if temporal_context else 760
    bg = (255, 255, 255)
    axis = (150, 158, 168)
    grid = (235, 238, 242)
    actual_c = (31, 102, 214)
    pred_c = (220, 60, 60)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title_font = _font(28)
    body_font = _font(18)
    small_font = _font(15)

    left = 90
    right = width - 40
    top = 120
    bottom = height - (175 if temporal_context else 110)
    plot_w = max(1, right - left)
    plot_h = max(1, bottom - top)

    draw.text((left, 28), title or "SERIES", fill=text_c, font=title_font)
    if subtitle:
        if temporal_context and "point dates = period start" not in subtitle:
            subtitle = f"{subtitle} | point dates = period start"
        draw.text((left, 64), subtitle, fill=muted_c, font=body_font)
    elif temporal_context:
        draw.text((left, 64), "point dates = period start", fill=muted_c, font=body_font)

    def _maybe_float(v):
        if v is None or v == "":
            return None
        try:
            out = float(v)
            return out if math.isfinite(out) else None
        except (TypeError, ValueError):
            return None

    y_true = [_maybe_float(v) for v in y_true]
    y_pred = [_maybe_float(v) for v in y_pred]
    n = max(len(y_true), len(y_pred))
    if n == 0:
        draw.rectangle((left, top, right, bottom), outline=axis, width=2)
        draw.text((left + 20, top + 20), "No data", fill=muted_c, font=body_font)
        image.save(path)
        return

    if len(y_true) < n:
        y_true.extend([None] * (n - len(y_true)))
    if len(y_pred) < n:
        y_pred.extend([None] * (n - len(y_pred)))
    y_true = y_true[:n]
    y_pred = y_pred[:n]
    actual_meaningful = len({round(v, 12) for v in y_true if v is not None}) > 1
    values = []
    if actual_meaningful:
        values.extend(v for v in y_true if v is not None)
    values.extend(v for v in y_pred if v is not None)
    if not values:
        values = [0.0]
    vmin, vmax = _series_range(values)

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + int(round((1.0 - frac) * plot_h))
        draw.line((left, y, right, y), fill=grid, width=1)
        value = vmin + frac * (vmax - vmin)
        draw.text((12, y - 9), f"{value:.3f}", fill=muted_c, font=small_font)

    draw.line((left, bottom, right, bottom), fill=axis, width=2)
    draw.line((left, top, left, bottom), fill=axis, width=2)

    def to_xy(i, value):
        if n <= 1:
            x = left + plot_w // 2
        else:
            x = left + int(round(i * plot_w / (n - 1)))
        y_norm = (float(value) - vmin) / max(vmax - vmin, 1e-12)
        y = bottom - int(round(y_norm * plot_h))
        return x, y

    pts_true = [to_xy(i, y_true[i]) for i in range(n) if y_true[i] is not None]
    pts_pred = [to_xy(i, y_pred[i]) for i in range(n) if y_pred[i] is not None]
    if len(pts_true) > 1:
        draw.line(pts_true, fill=actual_c, width=3)
    if len(pts_pred) > 1:
        draw.line(pts_pred, fill=pred_c, width=3)

    marker_r = 6 if n == 1 else 3
    for x, y in pts_true:
        draw.ellipse((x - marker_r, y - marker_r, x + marker_r, y + marker_r),
                     fill=actual_c, outline=actual_c)
    for x, y in pts_pred:
        draw.ellipse((x - marker_r, y - marker_r, x + marker_r, y + marker_r),
                     fill=pred_c, outline=pred_c)

    legend_x = right - 210
    legend_y = 26
    if actual_meaningful:
        draw.line((legend_x, legend_y + 12, legend_x + 36, legend_y + 12), fill=actual_c, width=4)
        draw.text((legend_x + 48, legend_y), "actual", fill=text_c, font=body_font)
    draw.line((legend_x, legend_y + 44, legend_x + 36, legend_y + 44), fill=pred_c, width=4)
    draw.text((legend_x + 48, legend_y + 32), "predicted", fill=text_c, font=body_font)

    if context_values is not None and indices is not None and len(indices) == n:
        label_positions = range(n) if temporal_context else sorted({0, n // 2, n - 1})
        for pos in label_positions:
            anchor_val = y_true[pos] if y_true[pos] is not None else y_pred[pos]
            if anchor_val is None:
                continue
            x, _ = to_xy(pos, anchor_val)
            label = _format_context_label(context_values[int(indices[pos])])
            if not label:
                continue
            if temporal_context:
                txt_img = Image.new("RGBA", (small_font.size * len(label), small_font.size + 4), (0, 0, 0, 0))
                tdraw = ImageDraw.Draw(txt_img)
                tdraw.text((0, 0), label, fill=muted_c + (255,), font=small_font)
                rotated = txt_img.rotate(90, expand=True)
                rw, _ = rotated.size
                image.paste(rotated, (int(x - rw / 2), bottom + 10), rotated)
            else:
                bbox = draw.textbbox((0, 0), label, font=small_font)
                text_w = bbox[2] - bbox[0]
                draw.text((x - text_w / 2, bottom + 18), label, fill=muted_c, font=small_font)
    else:
        for pos, label in ((0, "start"), (n - 1, "end")):
            anchor_val = y_true[pos] if y_true[pos] is not None else y_pred[pos]
            if anchor_val is None:
                continue
            x, _ = to_xy(pos, anchor_val)
            bbox = draw.textbbox((0, 0), label, font=small_font)
            text_w = bbox[2] - bbox[0]
            draw.text((x - text_w / 2, bottom + 18), label, fill=muted_c, font=small_font)

    image.save(path)


def _display_bank_label(bank):
    if bank == "__none__":
        return "(end-to-end)"
    if bank == "__lcs__":
        return "(lcs)"
    if bank == "__hybrid__":
        return "(hybrid)"
    if bank == "__kan__":
        return "(kan)"
    if bank == "__kan_hybrid__":
        return "(kan-hybrid)"
    return str(bank)


def _technique_label(bank):
    if bank == "__none__":
        return "DeepNet"
    if bank == "__lcs__":
        return "LCS"
    if bank == "__hybrid__":
        return "Hybrid LCS"
    if bank == "__kan__":
        return "KAN"
    if bank == "__kan_hybrid__":
        return "Hybrid KAN"
    return "Feature bank"


def _draw_wrapped_text(draw, xy, text, font, fill, max_width, line_gap=4, max_lines=None):
    x, y = xy
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + " ..."
    line_h = draw.textbbox((0, 0), "Ag", font=font)[3] + line_gap
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_h
    return y


def write_ranking_bar_png(path, agg, title="Ranking finale: tutte le varianti", max_items=None):
    rows = list(agg or [])
    if max_items is not None:
        rows = rows[:int(max_items)]
    width = 1500
    row_h = 44
    height = max(420, 150 + row_h * max(1, len(rows)))
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = _font(28)
    body_font = _font(17)
    small_font = _font(14)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)
    bar_c = (39, 116, 204)
    grid_c = (229, 232, 237)

    draw.text((52, 28), title, fill=text_c, font=title_font)
    draw.text((52, 66), "Overall piu' alto = migliore. Ranking aggregato su finestre/semi; prima riga = vincitore globale.",
              fill=muted_c, font=body_font)
    if not rows:
        draw.text((52, 130), "No ranking data", fill=muted_c, font=body_font)
        image.save(path)
        return path

    label_x = 52
    bar_x = 470
    bar_w = 760
    value_x = bar_x + bar_w + 28
    y0 = 120
    max_score = max(float(r.get("kpi_mean", 0.0)) for r in rows) or 1.0
    for tick in (0.25, 0.5, 0.75, 1.0):
        x = bar_x + int(round(bar_w * tick / max_score)) if tick <= max_score else None
        if x is not None and bar_x <= x <= bar_x + bar_w:
            draw.line((x, y0 - 12, x, height - 38), fill=grid_c, width=1)

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        bank = _display_bank_label(row.get("bank"))
        label = f"{i + 1}. {bank}/{row.get('readout', '')}"
        draw.text((label_x, y + 7), label[:54], fill=text_c, font=body_font)
        score = float(row.get("kpi_mean", 0.0))
        fill_w = int(round(bar_w * score / max_score))
        draw.rectangle((bar_x, y + 8, bar_x + bar_w, y + 30), outline=grid_c, width=1)
        draw.rectangle((bar_x, y + 8, bar_x + fill_w, y + 30), fill=bar_c)
        detail = f"{score:.3f}"
        if row.get("target_mode") == "event":
            detail += (f"  F1={float(row.get('event_f1_mean', 0.0)):.3f}"
                       f"  R={float(row.get('event_recall_mean', 0.0)):.3f}"
                       f"  Bal={float(row.get('event_bal_acc_mean', 0.0)):.3f}")
        n_runs = int(row.get("n_seeds", row.get("n_runs", 0)) or 0)
        detail += f"  runs={n_runs}  train={float(row.get('train_s', 0.0)):.1f}s"
        if row.get("weighted_ranking"):
            detail += f"  weight={float(row.get('weight_sum', 0.0)):.1f}"
        draw.text((value_x, y + 5), detail, fill=muted_c, font=small_font)

    image.save(path)
    return path


def write_technique_summary_png(path, agg, title="Riepilogo per tecnica"):
    groups = {}
    for row in agg or []:
        tech = _technique_label(row.get("bank"))
        groups.setdefault(tech, []).append(row)
    rows = []
    for tech, items in groups.items():
        best = max(items, key=lambda r: float(r.get("kpi_mean", 0.0)))
        mean_score = sum(float(r.get("kpi_mean", 0.0)) for r in items) / max(len(items), 1)
        rows.append((tech, best, mean_score, len(items)))
    rows.sort(key=lambda item: -float(item[1].get("kpi_mean", 0.0)))

    width = 1400
    row_h = 78
    height = max(420, 150 + row_h * max(1, len(rows)))
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = _font(28)
    body_font = _font(18)
    small_font = _font(15)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)
    colors = {
        "Hybrid LCS": (58, 125, 87),
        "LCS": (170, 92, 42),
        "DeepNet": (111, 82, 170),
        "Feature bank": (39, 116, 204),
    }

    draw.text((52, 28), title, fill=text_c, font=title_font)
    draw.text((52, 66), "Barra = migliore variante della famiglia; mean = media di tutte le varianti in quella famiglia.",
              fill=muted_c, font=body_font)
    if not rows:
        draw.text((52, 130), "No summary data", fill=muted_c, font=body_font)
        image.save(path)
        return path

    bar_x = 300
    bar_w = 720
    value_x = bar_x + bar_w + 28
    y0 = 125
    max_score = max(float(best.get("kpi_mean", 0.0)) for _, best, _, _ in rows) or 1.0
    for i, (tech, best, mean_score, n_items) in enumerate(rows):
        y = y0 + i * row_h
        score = float(best.get("kpi_mean", 0.0))
        color = colors.get(tech, (80, 120, 160))
        draw.text((52, y + 9), tech, fill=text_c, font=body_font)
        draw.text((52, y + 34), f"varianti={n_items}", fill=muted_c, font=small_font)
        draw.rectangle((bar_x, y + 8, bar_x + bar_w, y + 36), outline=(229, 232, 237), width=1)
        draw.rectangle((bar_x, y + 8, bar_x + int(round(bar_w * score / max_score)), y + 36), fill=color)
        best_label = f"{_display_bank_label(best.get('bank'))}/{best.get('readout', '')}"
        draw.text((value_x, y + 3), f"best={score:.3f}  mean={mean_score:.3f}", fill=text_c, font=body_font)
        draw.text((value_x, y + 31), best_label[:45], fill=muted_c, font=small_font)

    image.save(path)
    return path


def _parse_feature_tokens(feature_name):
    text = str(feature_name)
    body = "global"
    relation = text
    for part in text.split("|"):
        if part.startswith("body:"):
            body = part.split(":", 1)[1]
        elif part.startswith("eph:"):
            relation = part.split(":", 1)[1]
    if text == "moonphase":
        body = "moon"
        relation = "phase"
    return body, relation


def _condition_label(idx, lo, hi, feature_cols):
    idx = int(idx)
    name = feature_cols[idx] if feature_cols and idx < len(feature_cols) else f"x{idx + 1}"
    body, relation = _parse_feature_tokens(name)
    if lo == float("-inf") and hi == float("inf"):
        interval = "*"
    elif lo == float("-inf"):
        interval = f"<= {float(hi):.4g}"
    elif hi == float("inf"):
        interval = f">= {float(lo):.4g}"
    else:
        interval = f"[{float(lo):.4g}, {float(hi):.4g}]"
    return f"{body} / {relation} {interval}"


def write_lcs_rules_map_png(path, result, csv_meta, title="Mappa regole LCS", max_rules=10):
    rules = (result.get("_artifacts", {}) or {}).get("best_rules", [])[:max_rules]
    feature_cols = csv_meta.get("feature_cols") or []
    width = 1600
    row_h = 112
    height = max(520, 155 + row_h * max(1, len(rules)))
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = _font(28)
    body_font = _font(17)
    small_font = _font(14)
    text_c = (35, 39, 45)
    muted_c = (95, 99, 104)
    line_c = (221, 225, 231)
    pos_c = (197, 71, 67)
    neg_c = (62, 121, 196)

    draw.text((52, 28), title, fill=text_c, font=title_font)
    subtitle = (f"{_display_bank_label(result.get('bank'))}/{result.get('readout')}  "
                f"score={float(result.get('overall_kpi', 0.0)):.3f}")
    draw.text((52, 66), subtitle, fill=muted_c, font=body_font)
    draw.text((52, 96), "Ogni riga mostra solo le condizioni attive: body / relazione / intervallo.",
              fill=muted_c, font=small_font)

    if not rules:
        draw.text((52, 145), "Nessuna regola LCS disponibile per questo trial.", fill=muted_c, font=body_font)
        image.save(path)
        return path

    y0 = 140
    for i, rule in enumerate(rules):
        y = y0 + i * row_h
        action = int(rule.get("action", 0))
        color = pos_c if action == 1 else neg_c
        draw.rounded_rectangle((42, y, width - 42, y + row_h - 14), radius=8,
                               outline=line_c, width=1, fill=(250, 251, 253))
        draw.rectangle((42, y, 52, y + row_h - 14), fill=color)
        header = (f"#{int(rule.get('rank', i + 1))}  action={action}  "
                  f"fitness={float(rule.get('fitness', 0.0)):.4g}  "
                  f"acc={float(rule.get('accuracy', 0.0)):.3f}  "
                  f"n={int(rule.get('n_active_conditions', 0) or 0)} active")
        draw.text((70, y + 12), header, fill=text_c, font=body_font)
        raw_conditions = rule.get("conditions") or []
        active = [
            (idx, lo, hi) for idx, lo, hi in raw_conditions
            if not (lo == float("-inf") and hi == float("inf"))
        ]
        if active:
            cond_text = "  |  ".join(_condition_label(idx, lo, hi, feature_cols)
                                     for idx, lo, hi in active[:8])
        else:
            cond_text = " / ".join(rule.get("conditions_human", [])[:8]) or "*"
        _draw_wrapped_text(draw, (70, y + 44), cond_text, small_font, muted_c,
                           max_width=width - 150, max_lines=3)

    image.save(path)
    return path


def write_forecast_csv(path, context_col, context_values, row_indices, test_indices, y_true, y_pred,
                       csv_meta=None):
    test_indices = _as_list(test_indices)
    y_pred = _as_list(y_pred)
    y_true = [None] * len(y_pred) if y_true is None else _as_list(y_true)
    location_meta = location_display_meta(csv_meta)
    if location_meta is not None:
        y_true_out = decode_location_series(csv_meta, y_true, actual=True)
        y_pred_out = decode_location_series(csv_meta, y_pred, actual=False)
        pred_rescaled = list(y_pred_out)
    else:
        y_true_out = list(y_true)
        y_pred_out = list(y_pred)
        has_actual = any(v is not None for v in y_true)
        pred_rescaled = (
            _autoscale_pred_to_actual(
                [v for v in y_true if v is not None],
                [v for v in y_pred if v is not None],
            )
            if has_actual else list(y_pred)
        )
    rescaled_iter = iter(pred_rescaled)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        header = []
        if context_col:
            header.append(context_col)
        header.extend(["row_index", "actual", "predicted", "pred_recalibrated",
                       "error", "error_recalibrated"])
        w.writerow(header)
        for idx, actual, pred in zip(test_indices, y_true_out, y_pred_out):
            row = []
            if context_col:
                row.append(context_values[int(idx)])
            row_id = int(row_indices[int(idx)]) if row_indices is not None else int(idx)
            pred_f = float(pred) if pred is not None else float("nan")
            actual_f = float(actual) if actual is not None else None
            pred_rec = next(rescaled_iter, pred_f) if pred is not None else None
            pred_rec_f = float(pred_rec) if pred_rec is not None else float("nan")
            row.append(row_id)
            row.append(actual_f if actual_f is not None else "")
            row.append(pred_f)
            row.append(pred_rec_f)
            row.append((pred_f - actual_f) if actual_f is not None else "")
            row.append((pred_rec_f - actual_f) if actual_f is not None else "")
            w.writerow(row)


def write_validation_combined_csv(path, context_col, context_values, row_indices,
                                  segments, csv_meta=None):
    """Scrive un CSV con tutti i segmenti di validation concatenati.

    segments = [{label, indices, y_true, y_pred}, ...]
    Ogni segmento riscala pred sul proprio range actual (come il PNG autoscale).
    """
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        header = ["segment"]
        if context_col:
            header.append(context_col)
        header.extend(["row_index", "actual", "predicted", "pred_recalibrated",
                       "error", "error_recalibrated"])
        w.writerow(header)
        for seg in segments or []:
            label = str(seg.get("label", ""))
            indices = _as_list(seg.get("indices"))
            y_pred = _as_list(seg.get("y_pred"))
            y_true_raw = seg.get("y_true")
            y_true = [None] * len(y_pred) if y_true_raw is None else _as_list(y_true_raw)
            n = min(len(indices), len(y_true), len(y_pred))
            if n <= 0:
                continue
            if location_display_meta(csv_meta) is not None:
                y_true_out = decode_location_series(csv_meta, y_true[:n], actual=True)
                y_pred_out = decode_location_series(csv_meta, y_pred[:n], actual=False)
                pred_rescaled = list(y_pred_out)
            else:
                y_true_out = list(y_true[:n])
                y_pred_out = list(y_pred[:n])
                yt = [float(v) for v in y_true_out if v is not None]
                yp = [float(v) for v in y_pred_out if v is not None]
                pred_rescaled = _autoscale_pred_to_actual(yt, yp)
            rescaled_iter = iter(pred_rescaled)
            for i in range(n):
                idx = int(indices[i])
                actual = y_true_out[i]
                pred = y_pred_out[i]
                row = [label]
                if context_col:
                    row.append(context_values[idx] if context_values is not None else "")
                row_id = int(row_indices[idx]) if row_indices is not None else idx
                actual_f = float(actual) if actual is not None else None
                pred_f = float(pred) if pred is not None else float("nan")
                pred_rec = next(rescaled_iter, pred_f) if pred is not None else None
                pred_rec_f = float(pred_rec) if pred_rec is not None else float("nan")
                row.append(row_id)
                row.append(actual_f if actual_f is not None else "")
                row.append(pred_f)
                row.append(pred_rec_f)
                row.append((pred_f - actual_f) if actual_f is not None else "")
                row.append((pred_rec_f - actual_f) if actual_f is not None else "")
                w.writerow(row)


def _artifact_stem(result, artifact_type, rank_idx=None):
    if result["bank"] == "__none__":
        bank = "end_to_end"
    elif result["bank"] == "__lcs__":
        bank = "lcs"
    elif result["bank"] == "__hybrid__":
        bank = "hybrid"
    else:
        bank = result["bank"]
    readout = result["readout"]
    score_prefix = _format_score(result.get("overall_kpi", 0.0))
    rank_prefix = f"R{rank_idx:03d}_" if rank_idx is not None else ""
    serial = (result.get("extra", {}) or {}).get("trial_serial")
    try:
        serial_prefix = f"T{int(serial):05d}_" if serial is not None else ""
    except (TypeError, ValueError):
        serial_prefix = ""
    return (
        f"{serial_prefix}{rank_prefix}{score_prefix}__{safe_slug(bank)}__{safe_slug(readout)}"
        f"__seed{result['seed']}__{artifact_type}"
    )


def _format_lcs_condition(idx, lo, hi, feature_cols):
    idx = int(idx)
    base = f"x{idx + 1}"
    if feature_cols and idx < len(feature_cols):
        base += f" ({feature_cols[idx]})"
    if lo == float("-inf") and hi == float("inf"):
        return f"{base} is *"
    if lo == float("-inf"):
        return f"{base} <= {float(hi):.6g}"
    if hi == float("inf"):
        return f"{base} >= {float(lo):.6g}"
    return f"{base} in [{float(lo):.6g}, {float(hi):.6g}]"


def _format_lcs_rules_for_export(rules, csv_meta):
    feature_cols = csv_meta.get("feature_cols") or []
    out = []
    for rank, rule in enumerate(rules, start=1):
        raw_conditions = rule.get("conditions")
        active_conditions_human = rule.get("active_conditions_human")
        n_active = rule.get("n_active_conditions")
        n_wildcards = rule.get("n_wildcard_conditions")
        if raw_conditions is not None:
            active_conditions = [
                (idx, lo, hi) for idx, lo, hi in raw_conditions
                if not (lo == float("-inf") and hi == float("inf"))
            ]
            active_conditions_human = [
                _format_lcs_condition(idx, lo, hi, feature_cols)
                for idx, lo, hi in active_conditions
            ]
            n_active = len(active_conditions)
            n_wildcards = max(0, len(raw_conditions) - len(active_conditions))
        if active_conditions_human is None:
            active_conditions_human = [
                c for c in rule.get("conditions_human", [])
                if " is *" not in str(c)
            ]
        if not active_conditions_human:
            active_conditions_human = ["*"]
        item = {
            "rank": int(rule.get("rank", rank)),
            "conditions_human": active_conditions_human,
            "active_conditions_human": active_conditions_human,
            "n_active_conditions": int(n_active if n_active is not None else len(active_conditions_human)),
            "n_wildcard_conditions": int(n_wildcards if n_wildcards is not None else 0),
            "action": int(rule.get("action", 0)),
            "fitness": float(rule.get("fitness", 0.0)),
            "numerosity": int(rule.get("numerosity", 1)),
            "experience": int(rule.get("experience", 0)),
            "accuracy": float(rule.get("accuracy", 0.0)),
        }
        for key in ("tp", "tn", "fp", "fn", "rule_f1", "rule_recall", "rule_bal_acc",
                    "rule_action_correctness"):
            if key in rule:
                item[key] = float(rule.get(key, 0.0))
        out.append(item)
    return out


def _slice_context(context_values, indices):
    if context_values is None or indices is None:
        return None
    out = []
    for i in indices:
        try:
            out.append(context_values[int(i)])
        except (IndexError, TypeError, ValueError):
            out.append(None)
    return out


def export_best_trial(run_dir, task_label, result, csv_meta,
                      paired_recent_result=None, plot_autoscale=True,
                      validation_segments=None, rank_idx=None,
                      title_prefix=None):
    """Esporta un trial come PNG combinato (validation panel + forecast panel).

    validation_segments (opzionale): lista di dict {label, trial} che descrivono i
    segmenti del pannello superiore in ordine cronologico. Ogni trial contribuisce
    con i propri test_indices, y_true_test, y_pred_test. Se omesso, si costruisce
    automaticamente dal `result` (e da `paired_recent_result` per back-compat).
    rank_idx (opzionale): intero 1-based. Se fornito, aggiunge prefisso R{NNN}_ al filename.
    """
    task_dir = run_dir if task_label in (None, "") else os.path.join(run_dir, safe_slug(task_label))
    os.makedirs(task_dir, exist_ok=True)

    test_stem = _artifact_stem(result, "test", rank_idx=rank_idx)
    csv_path = os.path.join(task_dir, test_stem + ".csv")
    signature_path = os.path.join(task_dir, test_stem + ".json")
    combined_png_path = os.path.join(task_dir, test_stem + "__combined.png")

    artifacts = result.get("_artifacts", {})
    test_idx = artifacts.get("test_indices", [])
    y_true = artifacts.get("y_true_test", [])
    y_pred = artifacts.get("y_pred_test", [])
    write_forecast_csv(
        csv_path,
        csv_meta.get("context_col"),
        csv_meta.get("context_values"),
        csv_meta.get("row_indices"),
        test_idx,
        y_true,
        y_pred,
        csv_meta=csv_meta,
    )

    val_segments = []
    val_segments_full = []  # paralleli a val_segments, includono "indices" per il CSV combinato
    decode_for_location = is_location_analog_display(csv_meta)
    display_note = location_display_subtitle(csv_meta)
    if validation_segments:
        for spec in validation_segments:
            tr = spec.get("trial") if isinstance(spec, dict) else None
            if tr is None:
                continue
            seg_art = tr.get("_artifacts", {}) or {}
            seg_idx = seg_art.get("test_indices", [])
            if seg_idx is None or len(seg_idx) == 0:
                continue
            label = str(spec.get("label", ""))
            yt_seg = list(seg_art.get("y_true_test", []))
            yp_seg = list(seg_art.get("y_pred_test", []))
            yt_plot = decode_location_series(csv_meta, yt_seg, actual=True) if decode_for_location else yt_seg
            yp_plot = decode_location_series(csv_meta, yp_seg, actual=False) if decode_for_location else yp_seg
            val_segments.append({
                "label": label,
                "y_true": yt_plot,
                "y_pred": yp_plot,
                "context": _slice_context(csv_meta.get("context_values"), seg_idx),
            })
            val_segments_full.append({
                "label": label,
                "indices": list(seg_idx),
                "y_true": yt_seg,
                "y_pred": yp_seg,
            })
    else:
        if paired_recent_result is not None:
            rec_art = paired_recent_result.get("_artifacts", {}) or {}
            rec_idx = rec_art.get("test_indices", [])
            if rec_idx is not None and len(rec_idx) > 0:
                rec_yt = list(rec_art.get("y_true_test", []))
                rec_yp = list(rec_art.get("y_pred_test", []))
                rec_yt_plot = decode_location_series(csv_meta, rec_yt, actual=True) if decode_for_location else rec_yt
                rec_yp_plot = decode_location_series(csv_meta, rec_yp, actual=False) if decode_for_location else rec_yp
                val_segments.append({
                    "label": "past_validation",
                    "y_true": rec_yt_plot,
                    "y_pred": rec_yp_plot,
                    "context": _slice_context(csv_meta.get("context_values"), rec_idx),
                })
                val_segments_full.append({
                    "label": "past_validation",
                    "indices": list(rec_idx),
                    "y_true": rec_yt,
                    "y_pred": rec_yp,
                })
        y_true_plot = decode_location_series(csv_meta, y_true, actual=True) if decode_for_location else list(y_true)
        y_pred_plot = decode_location_series(csv_meta, y_pred, actual=False) if decode_for_location else list(y_pred)
        val_segments.append({
            "label": "test_validation",
            "y_true": y_true_plot,
            "y_pred": y_pred_plot,
            "context": _slice_context(csv_meta.get("context_values"), test_idx),
        })
        val_segments_full.append({
            "label": "test_validation",
            "indices": list(test_idx),
            "y_true": list(y_true),
            "y_pred": list(y_pred),
        })
    title, subtitle = _plot_title(result, "test", test_idx, csv_meta)
    if display_note:
        subtitle = f"{subtitle} | {display_note}" if subtitle else display_note
    if validation_segments:
        labels = " + ".join(s.get("label", "") for s in validation_segments if s.get("label"))
        panel_title = f"VALIDATION  [{labels}]" if labels else title
    else:
        panel_title = ("VALIDATION (past + test)"
                       if paired_recent_result is not None else title)
    panels = [{
        "title": panel_title,
        "subtitle": subtitle,
        "segments": val_segments,
    }]

    forecast_idx = artifacts.get("forecast_indices")
    y_true_forecast = artifacts.get("y_true_forecast")
    y_pred_forecast = artifacts.get("y_pred_forecast")
    forecast_csv_path = None
    if forecast_idx is not None and y_pred_forecast is not None:
        forecast_stem = _artifact_stem(result, "forecast")
        forecast_csv_path = os.path.join(task_dir, forecast_stem + ".csv")
        write_forecast_csv(
            forecast_csv_path,
            csv_meta.get("context_col"),
            csv_meta.get("context_values"),
            csv_meta.get("row_indices"),
            forecast_idx,
            y_true_forecast if y_true_forecast is not None else [None] * len(forecast_idx),
            y_pred_forecast,
            csv_meta=csv_meta,
        )
        ftitle, fsubtitle = _plot_title(result, "forecast", forecast_idx, csv_meta)
        if display_note:
            fsubtitle = f"{fsubtitle} | {display_note}" if fsubtitle else display_note
        forecast_title = "FORECAST"
        if title_prefix:
            forecast_title = f"{title_prefix} | {forecast_title}"
        fc_y_true_plot = (
            decode_location_series(csv_meta, y_true_forecast, actual=True)
            if decode_for_location and y_true_forecast is not None else
            ([] if y_true_forecast is None else list(y_true_forecast))
        )
        fc_y_pred_plot = (
            decode_location_series(csv_meta, y_pred_forecast, actual=False)
            if decode_for_location else list(y_pred_forecast)
        )
        panels.append({
            "title": forecast_title,
            "subtitle": fsubtitle,
            "segments": [{
                "label": "forecast",
                "y_true": fc_y_true_plot,
                "y_pred": fc_y_pred_plot,
                "context": _slice_context(csv_meta.get("context_values"), forecast_idx),
            }],
        })

    if title_prefix and panels:
        panels[0]["title"] = f"{title_prefix} | {panels[0].get('title', '')}"

    write_combined_panels_png(
        combined_png_path,
        panels,
        autoscale=(False if decode_for_location else plot_autoscale),
    )

    validation_combined_csv_path = None
    if val_segments_full:
        validation_combined_csv_path = os.path.join(
            task_dir, test_stem + "__validation_combined.csv"
        )
        write_validation_combined_csv(
            validation_combined_csv_path,
            csv_meta.get("context_col"),
            csv_meta.get("context_values"),
            csv_meta.get("row_indices"),
            val_segments_full,
            csv_meta=csv_meta,
        )

    exported = {
        "csv": csv_path,
        "png": combined_png_path,
        "test_csv": csv_path,
        "test_png": combined_png_path,
        "combined_png": combined_png_path,
        "json": signature_path,
        "task_dir": task_dir,
    }
    if validation_combined_csv_path is not None:
        exported["validation_combined_csv"] = validation_combined_csv_path
    if forecast_csv_path is not None:
        exported["forecast_csv"] = forecast_csv_path
        exported["forecast_png"] = combined_png_path

    if result.get("bank") in ("__lcs__", "__hybrid__") and artifacts.get("best_rules"):
        rules_path = os.path.join(task_dir, "best_rules.json")
        write_json(
            rules_path,
            _format_lcs_rules_for_export(artifacts.get("best_rules", []), csv_meta),
        )
        exported["best_rules_json"] = rules_path
    return exported
