#!/usr/bin/env python3
"""Build a single, provenance-preserving Japan August forecast report.

The document adds a cover and an explicitly conditional joint summary, then
embeds every page of the temporal Phase 2 ensemble report and the three
location-report pages without altering their plotted content.
"""

from __future__ import annotations

import argparse
import io
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


PAGE_WIDTH = 1000.0
PAGE_HEIGHT = 750.0
NAVY = colors.HexColor("#0B1F33")
BLUE = colors.HexColor("#1F5A94")
TEAL = colors.HexColor("#178D8D")
RED = colors.HexColor("#D63B36")
GOLD = colors.HexColor("#F0B44D")
INK = colors.HexColor("#152332")
MUTED = colors.HexColor("#5C6D7D")
LIGHT = colors.HexColor("#EAF1F6")
FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
pdfmetrics.registerFont(TTFont(FONT, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fuse temporal and location PDF reports")
    parser.add_argument("--temporal-report", required=True)
    parser.add_argument("--location-validation", required=True)
    parser.add_argument("--location-forecast", required=True)
    parser.add_argument("--location-map", required=True)
    parser.add_argument(
        "--location-map-image",
        default=None,
        help="PNG map for the decision page; defaults to the location-map PDF stem plus .png",
    )
    parser.add_argument("--output-pdf", required=True)
    parser.add_argument(
        "--updated-at",
        default=None,
        help="ISO timestamp; defaults to current Asia/Tokyo time",
    )
    return parser


def _timestamp(value: str | None) -> datetime:
    tokyo = ZoneInfo("Asia/Tokyo")
    if value is None:
        return datetime.now(tokyo)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tokyo)
    return parsed.astimezone(tokyo)


def _page_from_canvas(draw) -> PageObject:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    draw(pdf)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _paragraph(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    *,
    font_size: float = 16,
    leading: float | None = None,
    color=INK,
    align: int = TA_LEFT,
    font_name: str = FONT,
) -> float:
    style = ParagraphStyle(
        name="inline",
        fontName=font_name,
        fontSize=font_size,
        leading=leading or font_size * 1.3,
        textColor=color,
        alignment=align,
        spaceAfter=0,
    )
    block = Paragraph(text, style)
    _, height = block.wrap(width, PAGE_HEIGHT)
    block.drawOn(pdf, x, y_top - height)
    return height


def _cover(updated_at: datetime) -> PageObject:
    creation_label = updated_at.strftime("%d %B %Y - %H:%M JST")

    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColor(NAVY)
        pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

        # Restrained signal/location motif.
        pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.12))
        pdf.setLineWidth(1)
        for x in range(70, 960, 70):
            pdf.line(x, 110, x, 650)
        for y in range(120, 660, 70):
            pdf.line(60, y, 950, y)
        points = [(70, 292), (170, 300), (250, 284), (330, 305), (410, 292), (500, 470), (590, 286), (690, 298), (790, 288), (930, 302)]
        pdf.setStrokeColor(RED)
        pdf.setLineWidth(4)
        path = pdf.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        pdf.drawPath(path, stroke=1, fill=0)
        pdf.setFillColor(TEAL)
        for radius, alpha in ((74, 0.10), (45, 0.18), (18, 0.85)):
            pdf.setFillColor(colors.Color(0.09, 0.55, 0.55, alpha=alpha))
            pdf.circle(744, 470, radius, fill=1, stroke=0)

        pdf.setFillColor(GOLD)
        pdf.setFont(FONT_BOLD, 15)
        pdf.drawString(64, 684, "DLVS-WAVE | INTEGRATED REPORT")
        pdf.setFillColor(colors.white)
        pdf.setFont(FONT_BOLD, 42)
        pdf.drawCentredString(PAGE_WIDTH / 2, 588, "JAPAN SEISMIC FORECAST")
        pdf.drawCentredString(PAGE_WIDTH / 2, 536, "FOR AUGUST")
        pdf.setFont(FONT, 20)
        pdf.setFillColor(colors.HexColor("#C9D8E6"))
        pdf.drawCentredString(PAGE_WIDTH / 2, 490, "Microrun temporal ensemble + conditional localization")

        pdf.setFillColor(colors.Color(1, 1, 1, alpha=0.08))
        pdf.roundRect(198, 164, 604, 108, 14, fill=1, stroke=0)
        _paragraph(
            pdf,
            "Fusion of the Phase 2 weekly signal and the conditional geographic "
            "distribution for Japan. Every original page from both reports is "
            "reproduced in full in the following sections.",
            230,
            245,
            540,
            font_size=15,
            leading=21,
            color=colors.white,
            align=TA_CENTER,
        )
        pdf.setFont(FONT_BOLD, 17)
        pdf.setFillColor(GOLD)
        pdf.drawCentredString(PAGE_WIDTH / 2, 124, "FOR SCIENTIFIC RESEARCH ONLY")
        pdf.setFont(FONT, 13)
        pdf.setFillColor(colors.HexColor("#B8C8D6"))
        pdf.drawCentredString(
            PAGE_WIDTH / 2,
            82,
            f"Forecast updated 28 August 2026 | Report generated {creation_label}",
        )

    return _page_from_canvas(draw)


def _metric_card(pdf: canvas.Canvas, x: float, y: float, width: float, label: str, value: str, accent) -> None:
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#D7E1E9"))
    pdf.roundRect(x, y, width, 88, 9, fill=1, stroke=1)
    pdf.setFillColor(accent)
    pdf.rect(x, y, 7, 88, fill=1, stroke=0)
    pdf.setFillColor(MUTED)
    pdf.setFont(FONT_BOLD, 10)
    pdf.drawString(x + 20, y + 61, label.upper())
    pdf.setFillColor(INK)
    pdf.setFont(FONT_BOLD, 24)
    pdf.drawString(x + 20, y + 25, value)


def _summary(updated_at: datetime) -> PageObject:
    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColor(colors.HexColor("#F6F9FB"))
        pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        pdf.setFillColor(NAVY)
        pdf.rect(0, 690, PAGE_WIDTH, 60, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont(FONT_BOLD, 23)
        pdf.drawString(45, 711, "Combined summary: when + where (conditional)")

        _metric_card(pdf, 46, 572, 205, "UTC week start", "24 AUG 2026", RED)
        _metric_card(pdf, 271, 572, 205, "Staged signal", "6.876", GOLD)
        _metric_card(pdf, 496, 572, 205, "Leading zone", "Z3", TEAL)
        _metric_card(pdf, 721, 572, 233, "Relative mass for Z3", "36.34%", BLUE)

        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#D7E1E9"))
        pdf.roundRect(46, 238, 438, 307, 12, fill=1, stroke=1)
        pdf.roundRect(516, 238, 438, 307, 12, fill=1, stroke=1)

        pdf.setFillColor(RED)
        pdf.setFont(FONT_BOLD, 18)
        pdf.drawString(70, 510, "1. Phase 2 temporal ensemble")
        temporal = (
            "<b>Equivalent signal for the UTC week starting 24 August:</b> 6.876.<br/>"
            "<b>Stage 1 horizon:</b> supported in the equivalent backtest through 19 October 2026.<br/>"
            "<b>Stage 1 weights:</b> LCS 99.65%; KAN 0.18%; Deep 0.17%.<br/>"
            "<b>Fragility check:</b> the classic ensemble is 4.216 and misses all 3 M6.9+ peaks "
            "in the overall validation set (0% recall).<br/><br/>"
            "The value 6.876 is a staged-model output. It is not an observed magnitude or a "
            "guarantee that an event will occur."
        )
        _paragraph(pdf, temporal, 70, 478, 390, font_size=13, leading=19)

        pdf.setFillColor(TEAL)
        pdf.setFont(FONT_BOLD, 18)
        pdf.drawString(540, 510, "2. Conditional localization")
        location = (
            "<b>Highest-mass zone:</b> Z3 - Pacific Tohoku-Sanriku.<br/>"
            "<b>Historical centroid:</b> 38.377 N; 142.609 E.<br/>"
            "<b>Distribution:</b> Z3 36.34%; Z2 28.35%; Z4 19.98%; Z1 10.85%; Z5 4.48%.<br/>"
            "<b>Data:</b> 184 M6.9+ training events, 24 validation events, and zero non-seismic "
            "filler rows in either split.<br/><br/>"
            "The map expresses P(zone | assumed event), not an occurrence probability or a "
            "precise epicenter."
        )
        _paragraph(pdf, location, 540, 478, 390, font_size=13, leading=19)

        pdf.setFillColor(NAVY)
        pdf.roundRect(46, 91, 908, 119, 12, fill=1, stroke=0)
        pdf.setFillColor(GOLD)
        pdf.setFont(FONT_BOLD, 16)
        pdf.drawString(70, 176, "Combined interpretation")
        _paragraph(
            pdf,
            "The staged temporal signal identifies the week; the spatial model assigns a zone "
            "distribution only if an event is assumed. The two outputs are not multiplied because "
            "they are not calibrated probabilities on the same scale. This is research evidence, "
            "not an operational forecast, alert, or risk assessment.",
            70,
            157,
            860,
            font_size=13,
            leading=18,
            color=colors.white,
        )
        pdf.setFillColor(MUTED)
        pdf.setFont(FONT, 10)
        pdf.drawRightString(954, 38, updated_at.strftime("Updated %d %b %Y %H:%M JST | Page 2"))

    return _page_from_canvas(draw)


def _decision_page(updated_at: datetime, map_image: Path) -> PageObject:
    probabilities = (("Z1", 10.85), ("Z2", 28.35), ("Z3", 36.34), ("Z4", 19.98), ("Z5", 4.48))

    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColor(colors.HexColor("#F6F9FB"))
        pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        pdf.setFillColor(NAVY)
        pdf.rect(0, 684, PAGE_WIDTH, 66, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont(FONT_BOLD, 23)
        pdf.drawString(42, 708, "FORECAST WINDOW AND CONDITIONAL LOCATION")
        pdf.setFillColor(GOLD)
        pdf.setFont(FONT_BOLD, 10)
        pdf.drawRightString(
            958,
            712,
            updated_at.strftime("REPORT CREATED %d %b %Y | %H:%M JST"),
        )

        # Exact weekly interval.
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#D7E1E9"))
        pdf.roundRect(42, 500, 430, 154, 12, fill=1, stroke=1)
        pdf.setFillColor(RED)
        pdf.setFont(FONT_BOLD, 13)
        pdf.drawString(68, 625, "EXACT 7-DAY FORECAST SLOT - UTC ANCHORED")
        pdf.setFillColor(INK)
        pdf.setFont(FONT_BOLD, 25)
        pdf.drawString(68, 584, "24 AUG 2026 00:00 UTC")
        pdf.setFillColor(MUTED)
        pdf.setFont(FONT_BOLD, 12)
        pdf.drawString(68, 556, "TO")
        pdf.setFillColor(INK)
        pdf.setFont(FONT_BOLD, 19)
        pdf.drawString(103, 550, "31 AUG 2026 00:00 UTC")
        pdf.setFillColor(RED)
        pdf.setFont(FONT_BOLD, 10)
        pdf.drawRightString(448, 554, "END EXCLUSIVE")
        pdf.setFillColor(MUTED)
        pdf.setFont(FONT, 11)
        pdf.drawString(68, 522, "Japan local time: 24 Aug 09:00 JST to 31 Aug 09:00 JST (UTC+9).")

        # Verbal location statement.
        pdf.setFillColor(colors.white)
        pdf.roundRect(42, 206, 430, 270, 12, fill=1, stroke=1)
        pdf.setFillColor(TEAL)
        pdf.setFont(FONT_BOLD, 13)
        pdf.drawString(68, 447, "LEADING CONDITIONAL LOCATION")
        pdf.setFillColor(INK)
        pdf.setFont(FONT_BOLD, 37)
        pdf.drawString(68, 395, "ZONE Z3")
        pdf.setFillColor(TEAL)
        pdf.setFont(FONT_BOLD, 17)
        pdf.drawString(68, 361, "PACIFIC TOHOKU-SANRIKU OFFSHORE BAND")
        location_text = (
            "Most of the assigned mass lies in the offshore Pacific band east of northern "
            "Honshu, along Tohoku and Sanriku. The learned historical centroid is "
            "<b>38.377 N, 142.609 E</b>. The broad historical 5th-95th percentile envelope is "
            "33.975-41.842 N and 141.392-143.919 E. This is a zone, not a point epicenter."
        )
        _paragraph(pdf, location_text, 68, 334, 376, font_size=12, leading=17)

        # Source map with an explicit Z3 callout.
        map_x, map_y, map_w, map_h = 500.0, 310.0, 458.0, 338.0
        pdf.setFillColor(colors.white)
        pdf.roundRect(490, 298, 478, 360, 12, fill=1, stroke=1)
        pdf.drawImage(
            str(map_image),
            map_x,
            map_y,
            width=map_w,
            height=map_h,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        # Approximate plotted location of the learned Z3 centroid on the source map.
        focus_x = map_x + map_w * 0.677
        focus_y = map_y + map_h * 0.637
        pdf.setStrokeColor(RED)
        pdf.setLineWidth(5)
        pdf.circle(focus_x, focus_y, 27, fill=0, stroke=1)
        pdf.setFillColor(RED)
        pdf.roundRect(focus_x - 72, focus_y + 34, 144, 31, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont(FONT_BOLD, 12)
        pdf.drawCentredString(focus_x, focus_y + 44, "Z3 - 36.34%")

        # Probability bars make the leading zone unmistakable.
        pdf.setFillColor(colors.white)
        pdf.roundRect(490, 206, 478, 78, 12, fill=1, stroke=1)
        pdf.setFont(FONT_BOLD, 10)
        pdf.setFillColor(MUTED)
        pdf.drawString(510, 261, "RELATIVE ZONE MASS")
        bar_x = 510.0
        for zone, probability in probabilities:
            width = probability * 2.25
            pdf.setFillColor(RED if zone == "Z3" else colors.HexColor("#A9BBC8"))
            pdf.rect(bar_x, 225, width, 18, fill=1, stroke=0)
            pdf.setFillColor(INK)
            pdf.setFont(FONT_BOLD, 8)
            pdf.drawCentredString(bar_x + width / 2, 211, zone)
            bar_x += width + 8

        pdf.setFillColor(NAVY)
        pdf.roundRect(42, 73, 926, 106, 12, fill=1, stroke=0)
        pdf.setFillColor(GOLD)
        pdf.setFont(FONT_BOLD, 15)
        pdf.drawString(67, 147, "CONDITIONAL RESEARCH STATEMENT")
        _paragraph(
            pdf,
            "If an M6.9+ event is assumed in the UTC slot from 24 Aug 00:00 to 31 Aug 00:00 "
            "(24 Aug 09:00 to 31 Aug 09:00 JST), Z3 is the highest-mass location class. The "
            "model does not estimate occurrence probability and must not be used as an alert "
            "or hazard forecast.",
            67,
            130,
            870,
            font_size=12,
            leading=17,
            color=colors.white,
        )
        pdf.setFillColor(MUTED)
        pdf.setFont(FONT, 9)
        pdf.drawRightString(958, 35, "DLVS-Wave | For scientific research only | Page 3")

    return _page_from_canvas(draw)


def _overlay(section: str, page_number: int, total_pages: int) -> PageObject:
    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColor(NAVY)
        pdf.rect(0, 710, PAGE_WIDTH, 40, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont(FONT_BOLD, 12)
        pdf.drawString(35, 725, section)
        pdf.setStrokeColor(colors.HexColor("#D3DEE7"))
        pdf.line(35, 38, PAGE_WIDTH - 35, 38)
        pdf.setFillColor(MUTED)
        pdf.setFont(FONT, 9)
        pdf.drawString(35, 22, "DLVS-Wave | For scientific research only")
        label = f"Page {page_number} of {total_pages}"
        pdf.drawRightString(PAGE_WIDTH - 35, 22, label)

    return _page_from_canvas(draw)


def _wrapped_source_page(
    source: PageObject,
    section: str,
    page_number: int,
    total_pages: int,
) -> PageObject:
    page = PageObject.create_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    source_width = float(source.mediabox.width)
    source_height = float(source.mediabox.height)
    content_left = 35.0
    content_bottom = 50.0
    content_width = PAGE_WIDTH - 2 * content_left
    content_height = 650.0
    scale = min(content_width / source_width, content_height / source_height)
    x = content_left + (content_width - source_width * scale) / 2.0
    y = content_bottom + (content_height - source_height * scale) / 2.0
    source.add_transformation(Transformation().scale(scale).translate(x, y))
    page.merge_page(source)
    page.merge_page(_overlay(section, page_number, total_pages))
    return page


def build_report(args: argparse.Namespace) -> Path:
    updated_at = _timestamp(args.updated_at)
    temporal_path = Path(args.temporal_report).resolve()
    location_paths = [
        Path(args.location_validation).resolve(),
        Path(args.location_forecast).resolve(),
        Path(args.location_map).resolve(),
    ]
    for path in [temporal_path, *location_paths]:
        if not path.is_file():
            raise FileNotFoundError(path)

    temporal_reader = PdfReader(temporal_path)
    location_readers = [PdfReader(path) for path in location_paths]
    map_image = (
        Path(args.location_map_image).resolve()
        if args.location_map_image
        else location_paths[2].with_suffix(".png")
    )
    if not map_image.is_file():
        raise FileNotFoundError(map_image)
    total_pages = 3 + len(temporal_reader.pages) + sum(len(reader.pages) for reader in location_readers)

    writer = PdfWriter()
    writer.add_page(_cover(updated_at))
    writer.add_page(_summary(updated_at))
    writer.add_page(_decision_page(updated_at, map_image))
    temporal_start = len(writer.pages)
    for index, source in enumerate(temporal_reader.pages, start=1):
        writer.add_page(
            _wrapped_source_page(
                source,
                f"REPORT 1 | PHASE 2 TEMPORAL ENSEMBLE | PAGE {index}/{len(temporal_reader.pages)}",
                len(writer.pages) + 1,
                total_pages,
            )
        )
    location_start = len(writer.pages)
    labels = ("VALIDATION", "FORECAST AUG-OCT 2026", "ZONE MAP")
    source_index = 0
    for label, reader in zip(labels, location_readers, strict=True):
        for source in reader.pages:
            source_index += 1
            writer.add_page(
                _wrapped_source_page(
                    source,
                    f"REPORT 2 | CONDITIONAL LOCALIZATION | {label}",
                    len(writer.pages) + 1,
                    total_pages,
                )
            )

    writer.add_metadata(
        {
            "/Title": "Japan Seismic Forecast for August - Temporal and Location Report",
            "/Subject": "Research-only fusion of temporal ensemble and conditional localization",
            "/Author": "DLVS-Wave research pipeline",
            "/Keywords": "Japan, seismic research, temporal ensemble, conditional location",
            "/CreationDate": updated_at.strftime("D:%Y%m%d%H%M%S+09'00'"),
        }
    )
    writer.add_outline_item("Cover", 0)
    writer.add_outline_item("Combined summary", 1)
    writer.add_outline_item("Forecast window and conditional location", 2)
    writer.add_outline_item("Report 1 - Phase 2 temporal ensemble", temporal_start)
    writer.add_outline_item("Report 2 - Conditional localization", location_start)

    output = Path(args.output_pdf).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fused-japan-report-", dir=output.parent) as temp_dir:
        temporary = Path(temp_dir) / output.name
        with temporary.open("wb") as stream:
            writer.write(stream)
        temporary.replace(output)
    return output


def main() -> None:
    output = build_report(build_parser().parse_args())
    print(output)


if __name__ == "__main__":
    main()
