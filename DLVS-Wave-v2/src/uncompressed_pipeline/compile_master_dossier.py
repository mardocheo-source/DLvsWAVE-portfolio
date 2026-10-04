"""
DLVS-Wave v2.0: Master Publication Dossier & PDF Consolidator Engine
Stitches together all multi-level charts, validation timelines, energy spectra,
composition tables, and internal watermarked diagnostic maps into 06_final_report/.
Cleans up obsolete temporary 05_* / 04_* directories.
"""

import json
import logging
import shutil
import sys
from pathlib import Path

# Add src to sys.path
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import pandas as pd
from pypdf import PdfReader, PdfWriter

from uncompressed_pipeline.plotting import plot_clean_validation_report, plot_prospective_forecast
from uncompressed_pipeline.internal_experimental_mapper import generate_internal_experimental_triangulation_map

logger = logging.getLogger("uncompressed_pipeline.compile_master")


def compile_final_master_report(study_dir: Path) -> Path:
    study_dir = Path(study_dir)
    l1_dir = study_dir / "03_level1_fusion"
    l2_dir = study_dir / "04_level2_deep_meta_optimizer/level2_fusion"
    l3_dir = study_dir / "05_level3_final_fusion"
    final_dir = study_dir / "06_final_report"
    final_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean up obsolete folders if they exist
    for stale_name in ["04_final", "05_final_report", "05_report"]:
        stale_p = study_dir / stale_name
        if stale_p.exists() and stale_p.is_dir():
            shutil.rmtree(stale_p)
            print(f"Removed stale folder: {stale_p}")

    # 2. Re-render Level 3 Validation Report with updated human-readable training timeline & wave envelope
    master_df = pd.read_csv(study_dir / "01_data/master_7d_lean_uncompressed_normalized.csv")
    master_df["date"] = pd.to_datetime(master_df["date"])
    l3_val_df = pd.read_csv(l3_dir / "final_validation_predictions.csv")
    l3_val_df["date"] = pd.to_datetime(l3_val_df["date"])

    val_png = l3_dir / "compound_validation_report.png"
    val_pdf = l3_dir / "compound_validation_report.pdf"
    plot_clean_validation_report(
        val_pred_df=l3_val_df,
        master_df=master_df,
        title_meta="Level 3 Final Multi-Horizon Compound Ensemble (Tokachi 2003 & Tohoku 2011)",
        output_png=val_png,
        output_pdf=val_pdf,
    )
    print(f"Re-rendered L3 validation report with updated human timeline: {val_png}")

    # 3. Re-render Internal Experimental Triangulation Map with Italian watermark & disclaimer
    map_png, map_pdf = generate_internal_experimental_triangulation_map(study_dir, output_dir=l3_dir)
    print(f"Re-rendered Internal Triangulation Map (Italian): {map_png}")

    # 3b. Generate Multi-Paradigm Feature, Hyperparameter & Temporal Ablation Audit Table (Best vs Worst)
    ablation_pdf = l3_dir / "ablation_best_worst_composition_table.pdf"
    l1_trials_csv = study_dir / "02_level1/trials_all_models.csv"
    if l1_trials_csv.exists():
        from uncompressed_pipeline.ablation_table_report import generate_ablation_inspection_report
        generate_ablation_inspection_report(
            l1_trials_csv=l1_trials_csv,
            output_dir=l3_dir,
            stage_name="Level 1 Multi-Paradigm Screening (KAN, Deep Learning, LCS)",
        )

    # 4. Assemble Multi-Page Master Consolidated PDF in 06_final_report/
    # Order of Pages:
    # Page 1: Prospective Forecast Trajectory (L3)
    # Page 2: Continuous Energy & Deduced Magnitude Spectrum
    # Page 3: Multi-Level Benchmark Comparison Matrix
    # Page 4: Level 1 Screening Fusion Trial Composition Table
    # Page 5: Level 2 Deep Meta-Optimizer Trial Composition Table
    # Page 6: Multi-Paradigm Ablation Audit: Selected Best vs Discarded Worst (Features, Hypers, Timing)
    # Page 7: Sliced Validation Corridors & Historical Training Timeline (with Energy & Wave Envelope)
    # Page 8: Internal Experimental Analog Epicentral Triangulation Map (Italian Watermarked)
    
    pages_to_stitch = [
        l3_dir / "compound_prospective_forecast.pdf",
        l3_dir / "prospective_energy_magnitude_spectrum.pdf",
        l3_dir / "multilevel_fusion_benchmark_comparison.pdf",
        l1_dir / "fusion_trials_composition_table.pdf",
        l2_dir / "fusion_trials_composition_table.pdf",
        ablation_pdf,
        l3_dir / "compound_validation_report.pdf",
        l3_dir / "internal_experimental_triangulated_map.pdf",
    ]

    master_pdf_path = final_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.pdf"
    raw_pages = []

    for pdf_file in pages_to_stitch:
        if pdf_file.exists():
            reader = PdfReader(str(pdf_file))
            for page in reader.pages:
                raw_pages.append((pdf_file.name, page))
            print(f"Appended to Master PDF: {pdf_file.name} ({len(reader.pages)} pages)")
        else:
            print(f"WARNING: Missing PDF page file: {pdf_file}")

    total_pages = len(raw_pages)
    writer = PdfWriter()
    import io
    import matplotlib.pyplot as plt

    for i, (pname, page) in enumerate(raw_pages, start=1):
        mb = page.mediabox
        width = float(mb.width)
        height = float(mb.height)
        
        buf = io.BytesIO()
        dpi = 72.0
        fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.text(
            0.98, 0.012,
            f"Page {i} of {total_pages}",
            ha="right", va="bottom",
            fontsize=9.0, fontweight="bold",
            color="#334155",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#F8FAFC", edgecolor="#94A3B8", alpha=0.90, linewidth=0.8),
        )
        fig.savefig(buf, format="pdf", transparent=True)
        plt.close(fig)
        buf.seek(0)
        
        overlay = PdfReader(buf)
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with master_pdf_path.open("wb") as stream:
        writer.write(stream)
    print(f"Successfully compiled Master PDF ({len(writer.pages)} Pages with visible Page Numbers) -> {master_pdf_path}")

    # 5. Copy Markdown Dossier, Spectrum CSV, Analog Manifest and Tables to 06_final_report/
    shutil.copy(l3_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.md", final_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.md")
    shutil.copy(l3_dir / "prospective_energy_magnitude_spectrum.csv", final_dir / "prospective_energy_magnitude_spectrum.csv")
    shutil.copy(l3_dir / "prospective_energy_magnitude_spectrum.png", final_dir / "prospective_energy_magnitude_spectrum.png")
    shutil.copy(l3_dir / "multilevel_fusion_benchmark_comparison.png", final_dir / "multilevel_fusion_benchmark_comparison.png")
    shutil.copy(l3_dir / "internal_experimental_triangulated_map.png", final_dir / "internal_experimental_triangulated_map.png")
    shutil.copy(l1_dir / "fusion_trials_composition_table.png", final_dir / "L1_fusion_trials_composition_table.png")
    shutil.copy(l2_dir / "fusion_trials_composition_table.png", final_dir / "L2_fusion_trials_composition_table.png")
    if (l3_dir / "ablation_best_worst_composition_table.png").exists():
        shutil.copy(l3_dir / "ablation_best_worst_composition_table.png", final_dir / "ablation_best_worst_composition_table.png")

    # Also keep a copy in l3_dir for backward compatibility
    shutil.copy(master_pdf_path, l3_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.pdf")

    return master_pdf_path


if __name__ == "__main__":
    study = Path("DLVS-Wave-v2/studies_output/AUTORUN_japan_megathrust_m77_aug2026_jan2027_production")
    compile_final_master_report(study)
