"""Per-node joint dossiers using the authoritative production visual family."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from pypdf import PdfReader, PdfWriter

from uncompressed_pipeline.section_cover_generator import generate_executive_title_cover_page, generate_section_divider_page, A4_WIDTH, A4_HEIGHT
from uncompressed_pipeline.nested_data import atomic_json, timestamp, assign_zones, scope_catalog


def page(title):
    fig, ax = plt.subplots(figsize=(A4_WIDTH, A4_HEIGHT))
    fig.subplots_adjust(left=.09, right=.94, bottom=.18, top=.85)
    fig.suptitle(title, fontsize=15, fontweight="bold", color="#0F172A", y=.95)
    fig.text(.09, .06, "DLVS-WAVE | Joint nested research | Scores are not calibrated event probabilities", fontsize=8, color="#64748B")
    return fig, ax


def text_pages(pdf, title, lines):
    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), width=108) or [""])
    for start in range(0, len(wrapped), 27):
        fig, ax = page(title); ax.axis("off")
        ax.text(0, 1, "\n".join(wrapped[start:start+27]), transform=ax.transAxes, va="top", fontsize=10, linespacing=1.5)
        pdf.savefig(fig); plt.close(fig)


def draw_map(node, events, report_dir):
    fig, ax = page(f"{node['id']} | Geographic zones and validation events")
    try:
        from mpl_toolkits.basemap import Basemap
        world = Basemap(projection="cyl", llcrnrlon=-180, urcrnrlon=180, llcrnrlat=-90, urcrnrlat=90, resolution="c", ax=ax)
        world.drawcoastlines(color="#94A3B8", linewidth=.4)
    except ImportError:
        ax.grid(alpha=.2)
    zones = node.get("zones")
    if zones:
        xx, yy = np.meshgrid(np.arange(-179, 180, 2), np.arange(-89, 90, 2))
        grid = pd.DataFrame({"longitude": xx.ravel(), "latitude": yy.ravel()})
        inside = scope_catalog(grid, node["path"])
        if len(inside):
            colors = assign_zones(inside, zones["centers"])
            ax.scatter(inside.longitude, inside.latitude, c=colors, cmap="tab10", vmin=0, vmax=9, s=9, marker="s", alpha=.25, linewidths=0)
    if len(events):
        ax.scatter(events.longitude, events.latitude, s=4, c="#334155", alpha=.35, label="Catalog events")
    ids = set(node.get("location_split", {}).get("validation_ids", []))
    validation = events.loc[events.id.astype(str).isin(ids)] if len(events) else events
    if len(validation):
        ax.scatter(validation.longitude, validation.latitude, s=35, marker="^", color="#DC2626", edgecolors="white", linewidths=.4, label="Spatial validation events")
    if zones:
        for i, center in enumerate(zones["centers"]):
            lon, lat = np.degrees(np.arctan2(center[1], center[0])), np.degrees(np.arcsin(center[2]))
            ax.text(lon, lat, str(i), fontsize=11, weight="bold", bbox={"facecolor": "white", "alpha": .8, "edgecolor": "none"})
    bounds = node["geometry"].get("bounds")
    if node["level"] > 0 and bounds:
        south, north, west, east = bounds
        if west <= east:
            ax.set_xlim(max(-180, west - 5), min(180, east + 5))
        ax.set_ylim(max(-90, south - 5), min(90, north + 5))
    else:
        ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    if len(events): ax.legend(fontsize=8, loc="lower left")
    fig.text(.09, .095, "Zones are learned geographic partitions; they are not verified fault boundaries.", fontsize=9, color="#64748B")
    fig.savefig(report_dir / "map.png", dpi=160)
    fig.savefig(report_dir / "map.pdf")
    plt.close(fig)


def draw_windows(node, events, config, report_dir):
    fig, ax = page(f"{node['id']} | Training and recent validation windows")
    reference = timestamp(config["reference_date"])
    left = reference - pd.DateOffset(months=config["validation"]["maximum_months"] + 12)
    right = reference + pd.Timedelta(days=config["horizon_days"])
    for y, component in enumerate(["energy", "location"]):
        split = node.get(f"{component}_split", {})
        if split.get("status") != "sufficient":
            ax.text(left, y, f"{component}: insufficient recent data", color="#B91C1C", va="center")
            continue
        start = timestamp(split["validation_start"])
        ax.plot([left, start], [y, y], color="#64748B", linewidth=18, solid_capstyle="butt")
        ax.plot([start, reference], [y, y], color="#F59E0B", linewidth=18, solid_capstyle="butt")
        ax.plot([reference, right], [y, y], color="#38BDF8", linewidth=18, solid_capstyle="butt")
        selected = events.loc[events.id.astype(str).isin(split["validation_ids"])]
        ax.scatter(selected.time, np.full(len(selected), y), color="#B91C1C", marker="|", s=150, zorder=4)
        label = f"M >= {split['threshold']:.1f} | {split['validation_events']} events / {split['validation_event_slots']} slots\n{start.date()} to {reference.date()} (exclusive)"
        ax.text(start, y + .17, label, fontsize=9)
    ax.axvline(reference, color="#0F172A", linestyle="--", label="Forecast reference")
    ax.set_yticks([0, 1], ["Energy", "Location"]); ax.set_ylim(-.5, 1.65); ax.set_xlim(left, right)
    ax.set_xlabel("UTC date | gray: training context; amber: validation; blue: forecast")
    fig.text(.09, .095, f"Full training may start at {config['training_start'][:10]}; the plot shows recent context only.", fontsize=9)
    fig.savefig(report_dir / "validation_windows.png", dpi=160)
    fig.savefig(report_dir / "validation_windows.pdf")
    plt.close(fig)


def result_pages(pdf, node_dir, component, branch, node):
    folder = node_dir / ("01_energy_forecast" if component == "energy" else "02_spatial_zones_forecast") / branch
    if not (folder / "summary.json").exists():
        text_pages(pdf, f"{component.title()} | {branch.replace('_', ' ')}", ["This component did not complete. See node status and stop reason."])
        return
    summary = json.loads((folder / "summary.json").read_text())
    metrics = summary["metrics"]
    text_pages(pdf, f"{component.title()} | Model and validation audit", [f"Branch: {branch}",
        *[f"{key}: {value}" for key, value in metrics.items()],
        f"Score: {summary.get('score_semantics', 'Uncalibrated model output')}"])
    history = folder / "trial_history.json"
    if history.exists():
        records = json.loads(history.read_text())
        completed = [r for r in records if r.get('status', 'completed') == 'completed']
        displayed = []
        for stage in ['model_L1', 'model_L2']:
            subset = sorted([r for r in completed if r['stage'] == stage], key=lambda r:r['inner_loss'])
            displayed += subset[:5] + subset[-2:]
        text_pages(pdf, f"{component.title()} | L1 screening and L2 refinement", [
            f"{len(records)} actual trials; full parameters and feature masks are in trials.csv.",
            "Trial | Family | Stage | Inner selection loss",
            *[f"{r['trial']:4d} | {r['family']:14s} | {r['stage']:10s} | {r['inner_loss']:.6f}" for r in displayed],
            "Outer validation was not used to select these trials or fusion settings."])
    validation = pd.read_csv(folder / "validation_predictions.csv", parse_dates=["date"])
    future = pd.read_csv(folder / "forecast_predictions.csv", parse_dates=["date"])
    fig, ax = page(f"{component.title()} | {branch.replace('_', ' ')} | Validation")
    if component == "energy":
        ax.plot(validation.date, validation.score, color="#DC2626", label="Event score")
        ax.scatter(validation.loc[validation.target == 1, "date"], validation.loc[validation.target == 1, "score"], marker="^", color="#0F172A", label="Observed target slots")
        ax.axhline(metrics["threshold"], color="#64748B", linestyle="--", label="Fixed decision threshold")
    else:
        cols = [c for c in validation if c.startswith("zone_score_")]
        actual = validation.target.to_numpy(int)
        probability = validation[cols].to_numpy()
        ax.scatter(validation.date, probability[np.arange(len(actual)), actual], c=actual, cmap="tab10", vmin=0, vmax=9, label="Score assigned to observed zone")
        ax.set_title("Event records only; no Calm examples", fontsize=10)
    ax.set_ylim(-.03, 1.03); ax.set_ylabel("Uncalibrated score"); ax.set_xlabel("UTC date"); ax.legend(fontsize=8)
    pdf.savefig(fig); fig.savefig(folder / "validation_report.png", dpi=140); plt.close(fig)
    fig, ax = page(f"{component.title()} | {branch.replace('_', ' ')} | Forecast")
    cols = ["score"] if component == "energy" else [c for c in future if c.startswith("zone_score_")]
    for col in cols: ax.plot(future.date, future[col], label=col.replace("_", " "))
    ax.set_ylim(-.03, 1.03); ax.set_ylabel("Uncalibrated score"); ax.set_xlabel("UTC date"); ax.legend(fontsize=8)
    pdf.savefig(fig); fig.savefig(folder / "forecast_report.png", dpi=140); plt.close(fig)
    spectrum_path = folder / "prospective_energy_magnitude_spectrum.csv"
    if component == 'energy' and spectrum_path.exists():
        spectrum = pd.read_csv(spectrum_path, parse_dates=['date'])
        fig, axes = plt.subplots(2, 1, figsize=(A4_WIDTH, A4_HEIGHT), sharex=True)
        fig.subplots_adjust(left=.1, right=.94, bottom=.2, top=.87, hspace=.25)
        fig.suptitle('Joint production | Multi-level activation and potential ceiling', fontsize=14, weight='bold', y=.95)
        for name,color in [('score_l1','#0284C7'),('score_l2','#8B5CF6'),('score_l3','#DC2626')]:
            axes[0].plot(spectrum.date, spectrum[name], label=name, color=color)
        axes[0].legend(fontsize=8); axes[0].set_ylabel('Model score'); axes[0].set_ylim(-.03, 1.03)
        axes[1].plot(spectrum.date, spectrum.potential_magnitude_ceiling_up_to, color='#DC2626')
        axes[1].set_ylabel("Potential class ('up to M')")
        axes[1].set_xlabel('UTC date'); axes[1].set_ylim(4.5, 8.5)
        fig.text(.1,.09,"Same transfer function as the reference dossier: a heuristic potential class,\nnot an independently calibrated magnitude prediction.",fontsize=9,color='#64748B')
        pdf.savefig(fig); fig.savefig(folder/'prospective_energy_magnitude_spectrum.png',dpi=160); plt.close(fig)


def compile_node_report(directory, node, events, config):
    directory = Path(directory); report_dir = directory / "06_report"; report_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(report_dir / "node_report.json", node)
    lines = [f"# {node['id']} - geographic level {node['level']}", "", f"Status: {node['status']}",
             f"Parent: {node.get('parent')}", f"Bounds: {node['geometry'].get('bounds')}",
             f"Stop reason: {node.get('stop_reason', 'none')}", f"Reference: {config['reference_date']}", ""]
    for component in ["energy", "location"]:
        split = node.get(f"{component}_split", {})
        lines += [f"## {component.title()}", "", *[f"- {key}: {value}" for key, value in split.items() if key not in ["audit", "validation_ids"]], ""]
        if split.get("reduction", 0) > 0:
            lines += [f"Magnitude adaptation: {split['initial_threshold']:.1f} -> {split['threshold']:.1f} to meet recent validation and training retention. These metrics concern the lower threshold.", ""]
    selection = node.get("selection", {})
    lines += ["## Selection and limitations", "", f"Rule: {selection.get('rule', 'No selection completed')}",
              f"Selected zones: {selection.get('selected_zones', [])}", f"Stop reasons: {selection.get('stop_reasons', [])}",
              f"Quality observations (not stop rules in best-available mode): {selection.get('quality_notes', [])}",
              f"Parent divergence: {selection.get('parent_divergence')}",
              *[f"Candidate zone {c['zone']}: score {c['score']:.4f}, area ratio {c['area_ratio']:.3f}, geometric eligibility {c['admissible_geometry']}" for c in selection.get('candidates', [])], "",
              "Energy validation contains non-event intervals. Spatial training and validation contain events only.",
              "Independent events sharing an astronomical slot are grouped in chronological splits.",
              "Changing magnitude thresholds or learned zones limits direct comparison between levels.",
              "Astronomical inputs are observationally available ephemerides; no future seismic predictors are used.",
              "The potential ceiling uses the exact reference transfer function. It is a heuristic potential class, not an independently calibrated magnitude prediction.",
              "Catalog coverage is bounded by the frozen cutoff; historical magnitude completeness is not assumed."]
    (report_dir / "node_report.md").write_text("\n".join(lines) + "\n")
    draw_map(node, events, report_dir); draw_windows(node, events, config, report_dir)
    energy = node.get("energy_split", {}).get("threshold", config["energy"]["magnitude"])
    spatial = node.get("location_split", {}).get("threshold", config["location"]["magnitude"])
    cover = report_dir / "cover.pdf"
    generate_executive_title_cover_page(
        title="DLVS-WAVE: JOINT NESTED FORECAST DOSSIER",
        subtitle=f"{'SYNTHETIC TEST | ' if config['study_id'] == 'SYNTHETIC_SMOKE' else ''}{node['id']} | Geographic level {node['level']} | {node['status']}",
        metadata={"Reference UTC": config["reference_date"], "Forecast horizon": f"{config['horizon_days']} days | {config['interval_days']}-day cadence",
                  "Energy validation": f"{node.get('energy_split', {}).get('validation_events', 0)} events | recent chronological holdout",
                  "Spatial validation": f"{node.get('location_split', {}).get('validation_events', 0)} events | event records only",
                  "Model family": "KAN / Tabular ResNet / LCS",
                  "Fusion": "85% main bodies / 15% minor bodies",
                  "Run state": node["status"]}, output_pdf=cover, mini_map_png=report_dir / "map.png",
        energy_callout=f"EVENTS M >= {energy:.1f}", spatial_callout=f"EVENTS M >= {spatial:.1f}")
    narrative = report_dir / "audit.pdf"
    with PdfPages(narrative) as pdf:
        text_pages(pdf, "Node configuration, selection and limits", lines)
        for component in ["energy", "location"]:
            split = node.get(f"{component}_split", {})
            text_pages(pdf, f"{component.title()} | Threshold and recent-window attempts", [
                "Magnitude | Months | Train slots | Validation slots | Withheld fraction | Admissible",
                *[f"{r['threshold']:.1f} | {r['months']} | {r['training_event_slots']} | {r['validation_event_slots']} | {r['withheld_fraction']:.3f} | {r['admissible']}" for r in split.get("audit", [])]])
            selected_events = events.loc[events.id.astype(str).isin(split.get('validation_ids', []))]
            text_pages(pdf, f"{component.title()} | Actual validation events", ["Event ID | UTC time | Magnitude | Latitude | Longitude",
                *[f"{r.id} | {r.time} | {r.mag:.1f} | {r.latitude:.3f} | {r.longitude:.3f}" for r in selected_events.itertuples()]])
    parts = [cover, narrative, report_dir / "map.pdf", report_dir / "validation_windows.pdf"]
    for number, branch in enumerate(["main_bodies_branch", "minor_bodies_branch", "fusion_main_minor"], 1):
        divider = report_dir / f"section_{number}.pdf"
        generate_section_divider_page(f"SECTION {number}", branch.replace("_", " ").title(),
            "Joint production model family with explicit chronological splits",
            ["Energy: regular grid with event and non-event examples", "Location: eligible events only, K geographic classes", "Recent outer validation separate from inner model selection"], divider)
        results = report_dir / f"results_{number}.pdf"
        with PdfPages(results) as pdf:
            for component in ["energy", "location"]:
                result_pages(pdf, directory, component, branch, node)
        parts += [divider, results]
    writer = PdfWriter()
    for part in parts: writer.append(str(part))
    target = report_dir / "JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf"
    temporary = target.with_suffix(".pdf.tmp")
    with temporary.open("wb") as stream: writer.write(stream)
    with temporary.open("rb") as stream:
        if len(PdfReader(stream).pages) < 4: raise RuntimeError("incomplete_node_report")
    temporary.replace(target)
    return target
