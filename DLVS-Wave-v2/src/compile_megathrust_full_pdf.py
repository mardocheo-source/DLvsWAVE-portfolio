"""Compile the completed two-event L1/L2/L3 run into one visually auditable PDF."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PAGE_SIZE = landscape(A3)
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(FONT_REGULAR, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _trial_count(path: Path) -> int:
    return len(_csv_rows(path))


def _format_metric(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


class FullReport:
    def __init__(self, output: Path, run_dir: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        self.output = output
        self.run_dir = run_dir
        self.pdf = canvas.Canvas(str(output), pagesize=PAGE_SIZE, pageCompression=1)
        self.page_number = 0

    def _footer(self, label: str) -> None:
        self.pdf.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.pdf.line(28, 22, PAGE_WIDTH - 28, 22)
        self.pdf.setFillColor(colors.HexColor("#64748b"))
        self.pdf.setFont(FONT_REGULAR, 7.5)
        self.pdf.drawString(30, 10, label[:155])
        self.pdf.drawRightString(PAGE_WIDTH - 30, 10, f"Page {self.page_number}")

    def _finish_page(self, label: str) -> None:
        self._footer(label)
        self.pdf.showPage()

    def cover(self, audit: dict[str, Any], run_manifest: dict[str, Any]) -> None:
        self.page_number += 1
        self.pdf.setFillColor(colors.HexColor("#0f172a"))
        self.pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        self.pdf.setFillColor(colors.HexColor("#38bdf8"))
        self.pdf.setFont(FONT_BOLD, 34)
        self.pdf.drawString(55, PAGE_HEIGHT - 95, "DLVS-Wave v2.0")
        self.pdf.setFillColor(colors.white)
        self.pdf.setFont(FONT_BOLD, 25)
        self.pdf.drawString(55, PAGE_HEIGHT - 138, "Japan M >= 7.7 binary research run")
        self.pdf.setFont(FONT_REGULAR, 15)
        self.pdf.drawString(55, PAGE_HEIGHT - 175, "Complete Level 1, Level 2 and Level 3 visual report")

        created = datetime.now(timezone.utc).isoformat()
        facts = [
            f"Run: {self.run_dir.name}",
            f"Generated UTC: {created}",
            f"Device: {run_manifest.get('device', 'cpu')} (CPU-only contract)",
            f"Cutoff: {audit.get('cutoff_utc', 'n/a')}",
            f"Forecast horizon: {audit.get('forecast_start', 'n/a')} through {audit.get('forecast_end', 'n/a')}",
            "Validation: exactly 2 held-out Japanese events; each corridor is 13 weeks before + event + 13 weeks after",
            "Target: Japan-extended M >= 7.7 is 1; quiet/sub-threshold and large foreign events are 0",
        ]
        y = PAGE_HEIGHT - 245
        self.pdf.setFont(FONT_REGULAR, 12.5)
        for fact in facts:
            self.pdf.setFillColor(colors.HexColor("#bae6fd"))
            self.pdf.circle(63, y + 4, 2.5, fill=1, stroke=0)
            self.pdf.setFillColor(colors.white)
            self.pdf.drawString(78, y, fact)
            y -= 31

        self.pdf.setFillColor(colors.HexColor("#7f1d1d"))
        self.pdf.roundRect(55, 58, PAGE_WIDTH - 110, 78, 8, fill=1, stroke=0)
        self.pdf.setFillColor(colors.white)
        self.pdf.setFont(FONT_BOLD, 12)
        self.pdf.drawString(72, 108, "RESEARCH LIMIT")
        warning = (
            "These are experimental association models. Their scores are not calibrated physical earthquake "
            "probabilities and this report is not an operational warning or a basis for public-safety decisions."
        )
        self.pdf.setFont(FONT_REGULAR, 10.5)
        lines = simpleSplit(warning, FONT_REGULAR, 10.5, PAGE_WIDTH - 150)
        for index, line in enumerate(lines):
            self.pdf.drawString(72, 87 - index * 14, line)
        self._finish_page("Cover and scope")

    def summary(
        self,
        audit: dict[str, Any],
        validation_rows: list[dict[str, str]],
        run_manifest: dict[str, Any],
        specialists: list[dict[str, str]],
        level3_rows: list[dict[str, str]],
    ) -> None:
        self.page_number += 1
        self.pdf.setFillColor(colors.HexColor("#0f172a"))
        self.pdf.setFont(FONT_BOLD, 22)
        self.pdf.drawString(38, PAGE_HEIGHT - 48, "Run audit and selected-result summary")
        self.pdf.setFont(FONT_REGULAR, 10)
        self.pdf.setFillColor(colors.HexColor("#334155"))
        data_line = (
            f"Rows {audit.get('rows', 'n/a')} | packed features {audit.get('feature_count', 'n/a')} | "
            f"Japan positive weeks {audit.get('japan_positive_weeks', 'n/a')} | foreign hard-negative weeks "
            f"{audit.get('foreign_hard_negative_weeks', 'n/a')} | forecast rows {audit.get('forecast_rows', 'n/a')}"
        )
        self.pdf.drawString(38, PAGE_HEIGHT - 70, data_line)

        unique_events: dict[str, dict[str, str]] = {}
        for row in validation_rows:
            unique_events.setdefault(row.get("event_number", ""), row)
        y = PAGE_HEIGHT - 104
        self.pdf.setFont(FONT_BOLD, 12)
        self.pdf.setFillColor(colors.HexColor("#0369a1"))
        self.pdf.drawString(38, y, "Fixed validation episodes")
        y -= 22
        self.pdf.setFont(FONT_REGULAR, 10.5)
        self.pdf.setFillColor(colors.black)
        for number in sorted(unique_events):
            event = unique_events[number]
            self.pdf.drawString(
                48,
                y,
                f"Event {number}: master week {event.get('event_date')} | M {event.get('event_magnitude')} | "
                f"corridor {event.get('window_start')} to {event.get('window_end')} | 27 rows",
            )
            y -= 18

        y -= 8
        self.pdf.setFont(FONT_BOLD, 12)
        self.pdf.setFillColor(colors.HexColor("#0369a1"))
        self.pdf.drawString(38, y, "Trial inventory")
        y -= 22
        self.pdf.setFont(FONT_REGULAR, 10.5)
        self.pdf.setFillColor(colors.black)
        inventory = []
        for model in ("kan", "deep_learning", "lcs"):
            l1 = _trial_count(self.run_dir / "02_level1" / f"study_{model}" / f"optuna_trials_{model}.csv")
            l2 = _trial_count(self.run_dir / "03_level2" / f"study_{model}" / f"meta_trials_{model}.csv")
            inventory.append(f"{model}: L1={l1}, L2={l2}")
        self.pdf.drawString(48, y, " | ".join(inventory))
        y -= 30

        ensemble = run_manifest.get("ensemble", {})
        ensemble_metrics = ensemble.get("metrics") or {}
        self.pdf.setFont(FONT_BOLD, 12)
        self.pdf.setFillColor(colors.HexColor("#0369a1"))
        self.pdf.drawString(38, y, "Level 2 validation-weighted ensemble")
        y -= 20
        self.pdf.setFillColor(colors.black)
        self.pdf.setFont(FONT_REGULAR, 10.5)
        self.pdf.drawString(
            48,
            y,
            f"P {_format_metric(ensemble_metrics.get('precision'))} | R {_format_metric(ensemble_metrics.get('recall'))} | "
            f"F1 {_format_metric(ensemble_metrics.get('f1'))} | FP {ensemble_metrics.get('fp', 'n/a')} | "
            f"FN {ensemble_metrics.get('fn', 'n/a')} | peak MAE "
            f"{_format_metric(ensemble_metrics.get('event_peak_mae_weeks'), 2)} weeks | "
            f"internal gate passed {ensemble.get('certified', False)} | untouched outer certification NO",
        )
        y -= 30

        if specialists:
            self.pdf.setFont(FONT_BOLD, 12)
            self.pdf.setFillColor(colors.HexColor("#0369a1"))
            self.pdf.drawString(38, y, "Peak-timing specialists (timing and threshold metrics remain separate)")
            y -= 19
            columns = [38, 102, 185, 240, 304, 359, 414, 463, 510, 562]
            headers = ["Stage", "Model", "Trial", "Train R", "Val P", "Val R", "F1", "FP", "Peak MAE", "Peak max"]
            self.pdf.setFont(FONT_BOLD, 8.4)
            self.pdf.setFillColor(colors.black)
            for x, header in zip(columns, headers):
                self.pdf.drawString(x, y, header)
            y -= 14
            self.pdf.setFont(FONT_REGULAR, 8.2)
            for row in specialists:
                values = [
                    row.get("stage", ""), row.get("model", ""), row.get("trial_number", ""),
                    _format_metric(row.get("train_recall")), _format_metric(row.get("precision")),
                    _format_metric(row.get("recall")), _format_metric(row.get("f1")), row.get("fp", ""),
                    _format_metric(row.get("event_peak_mae_weeks"), 2), row.get("event_peak_max_error_weeks", ""),
                ]
                for x, value in zip(columns, values):
                    self.pdf.drawString(x, y, str(value)[:13])
                y -= 13

        if level3_rows and y > 100:
            y -= 7
            self.pdf.setFont(FONT_BOLD, 12)
            self.pdf.setFillColor(colors.HexColor("#0369a1"))
            self.pdf.drawString(38, y, "Level 3 ECHN ablations")
            y -= 18
            self.pdf.setFont(FONT_REGULAR, 8.5)
            self.pdf.setFillColor(colors.black)
            for row in level3_rows:
                self.pdf.drawString(
                    48,
                    y,
                    f"{row.get('variant')}: P {_format_metric(row.get('precision'))}, R {_format_metric(row.get('recall'))}, "
                    f"F1 {_format_metric(row.get('f1'))}, FP {row.get('fp')}, FN {row.get('fn')}, "
                    f"peak MAE {_format_metric(row.get('event_peak_mae_weeks'), 2)}w",
                )
                y -= 13
        self._finish_page("Audited inputs, validation contract and metric summary")

    def image_page(self, image_path: Path, section: str) -> None:
        self.page_number += 1
        image = ImageReader(str(image_path))
        image_width, image_height = image.getSize()
        max_width = PAGE_WIDTH - 36
        max_height = PAGE_HEIGHT - 42
        scale = min(max_width / image_width, max_height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        x = (PAGE_WIDTH - draw_width) / 2
        y = 27 + (max_height - draw_height) / 2
        self.pdf.setFillColor(colors.white)
        self.pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        self.pdf.drawImage(
            image,
            x,
            y,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        relative = image_path.relative_to(self.run_dir)
        self._finish_page(f"{section} | {relative}")

    def save(self) -> None:
        self.pdf.save()


def _images(run_dir: Path) -> list[tuple[str, Path]]:
    groups: list[tuple[str, Iterable[Path]]] = [
        ("Level 1 selected", run_dir.glob("02_level1/study_*/best_output/*.png")),
        ("Level 1 peak-timing specialist", run_dir.glob("02_level1/study_*/best_peak_timing_output/*.png")),
        ("Level 2 selected", run_dir.glob("03_level2/study_*/best_output/*.png")),
        ("Level 2 peak-timing specialist", run_dir.glob("03_level2/study_*/best_peak_timing_output/*.png")),
        ("Level 2 weighted ensemble", run_dir.glob("05_report/japan_megathrust_binary_forecast*.png")),
        ("Level 3 ECHN variants", run_dir.glob("06_level3_episodic_hazard/variant_*/*.png")),
        ("Level 3 ECHN ensemble", run_dir.glob("06_level3_episodic_hazard/echn_ensemble*.png")),
    ]
    result: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for section, paths in groups:
        for path in sorted(paths):
            if path not in seen:
                seen.add(path)
                result.append((section, path))
    return result


def run(run_dir: Path, output: Path) -> dict[str, Any]:
    root = run_dir.resolve()
    audit = _json(root / "01_data" / "dataset_audit.json")
    run_manifest = _json(root / "run_manifest.json")
    validation_rows = _csv_rows(root / "01_data" / "validation_corridor_index.csv")
    specialists = _csv_rows(root / "04_final" / "peak_timing_specialists.csv")
    level3_rows = _csv_rows(root / "06_level3_episodic_hazard" / "level3_variant_comparison.csv")
    images = _images(root)
    if not images:
        raise ValueError("No completed validation/forecast PNGs were found")
    report = FullReport(output.resolve(), root)
    report.cover(audit, run_manifest)
    report.summary(audit, validation_rows, run_manifest, specialists, level3_rows)
    for section, image_path in images:
        report.image_page(image_path, section)
    report.save()
    index_path = root / "05_report" / "FULL_REPORT_INDEX.md"
    lines = [
        "# Full L1/L2/L3 report index", "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`", "",
        f"PDF: `{output.resolve()}`", "",
        "The first two pages contain the contract and metric summary. The remaining pages reproduce every selected",
        "validation and pure-forecast graph generated programmatically for L1, L2, timing specialists and L3.", "",
    ]
    for page, (section, image_path) in enumerate(images, start=3):
        lines.append(f"- Page {page}: {section} - `{image_path.relative_to(root)}`")
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"pdf": str(output.resolve()), "pages": len(images) + 2, "images": len(images), "index": str(index_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-pdf", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(run(args.run_dir, args.output_pdf), indent=2))
