"""
DLVS-Wave v2.0: Super-Fusion Publication Dossier & PDF Consolidator Engine
Compiles all multi-level charts, validation timelines, energy spectra,
composition tables, and internal watermarked diagnostic maps for the
Hierarchical Super-Fusion (Main + Minor Bodies) into:
`AUTORUN_japan_megathrust_m77_aug2026_jan2027_production/07_super_fusion_main_minor/`.
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

logger = logging.getLogger("uncompressed_pipeline.compile_super_dossier")


def compile_super_fusion_report(
    main_study_dir: Path,
    minor_branch_dir: Path,
    super_fusion_dir: Path,
) -> Path:
    main_study_dir = Path(main_study_dir)
    minor_branch_dir = Path(minor_branch_dir)
    super_fusion_dir = Path(super_fusion_dir)
    super_fusion_dir.mkdir(parents=True, exist_ok=True)

    # 1. Re-render Super-Fusion Validation Report with updated human-readable training timeline & wave envelope
    master_df = pd.read_csv(main_study_dir / "01_data/master_7d_lean_uncompressed_normalized.csv")
    master_df["date"] = pd.to_datetime(master_df["date"])
    
    val_csv = super_fusion_dir / "final_validation_predictions.csv"
    if not val_csv.exists():
        val_csv = super_fusion_dir / "compound_validation_predictions.csv"
    val_df = pd.read_csv(val_csv)
    val_df["date"] = pd.to_datetime(val_df["date"])

    fc_csv = super_fusion_dir / "final_prospective_forecast.csv"
    if not fc_csv.exists():
        fc_csv = super_fusion_dir / "compound_prospective_forecast.csv"
    fc_df = pd.read_csv(fc_csv)
    fc_df["date"] = pd.to_datetime(fc_df["date"])

    plot_prospective_forecast(
        forecast_df=fc_df,
        title_meta="Hierarchical Super-Fusion Prospective Forecast (Main + Minor Bodies)",
        output_png=super_fusion_dir / "compound_prospective_forecast.png",
        output_pdf=super_fusion_dir / "compound_prospective_forecast.pdf",
    )

    val_png = super_fusion_dir / "compound_validation_report.png"
    val_pdf = super_fusion_dir / "compound_validation_report.pdf"
    plot_clean_validation_report(
        val_pred_df=val_df,
        master_df=master_df,
        title_meta="Hierarchical Super-Fusion (Main + Minor Bodies) Validation",
        output_png=val_png,
        output_pdf=val_pdf,
    )

    # 2. Re-render Internal Experimental Triangulation Map with English watermark
    generate_internal_experimental_triangulation_map(
        study_dir=super_fusion_dir,
        output_dir=super_fusion_dir,
    )

    # 3. Generate Multi-Paradigm Feature, Hyperparameter & Temporal Ablation Audit Table (Best vs Worst)
    ablation_pdf = super_fusion_dir / "ablation_best_worst_composition_table.pdf"
    l1_trials_csv = minor_branch_dir / "02_level1/trials_all_models.csv"
    stage_label = "Deep Minor Bodies Multi-Paradigm Screening (KAN, Deep Learning, LCS)"
    if not l1_trials_csv.exists():
        l1_trials_csv = main_study_dir / "02_level1/trials_all_models.csv"
        stage_label = "Main Bodies Multi-Paradigm Screening (KAN, Deep Learning, LCS)"
    if l1_trials_csv.exists():
        from uncompressed_pipeline.ablation_table_report import generate_ablation_inspection_report
        generate_ablation_inspection_report(
            l1_trials_csv=l1_trials_csv,
            output_dir=super_fusion_dir,
            stage_name=stage_label,
        )

    # 4. Generate Consultative Scientific Appendix Pages (KAN, Deep Learning, LCS Feature & Ephemerides Breakdown)
    from uncompressed_pipeline.trial_appendix_dossier import generate_trial_appendix_pages
    appendix_pdfs = generate_trial_appendix_pages(
        study_dir=minor_branch_dir,
        output_dir=super_fusion_dir,
        trials_csv_path=l1_trials_csv,
    )

    # 5. Export Standalone Dedicated Triangulation Map Document (Separate from Summary Dossier)
    standalone_map_src = super_fusion_dir / "internal_experimental_triangulated_map.pdf"
    standalone_map_dst = super_fusion_dir / "DLVS_WAVE_V2_STANDALONE_EXPERIMENTAL_TRIANGULATED_MAP.pdf"
    if standalone_map_src.exists():
        import shutil
        shutil.copy(standalone_map_src, standalone_map_dst)
        print(f"Created Dedicated Standalone Map Document: {standalone_map_dst.name}")

    # Comprehensive Consolidated Master PDF Structure (Summary & Diagnostic Dossier - Map Excluded):
    # Core Report:
    # Page 1: Super-Fusion Prospective Forecast Trajectory
    # Page 2: Continuous Energy & Deduced Magnitude Spectrum
    # Page 3: Multi-Level Benchmark Comparison Matrix
    # Fusion Tables:
    # Page 4: Level 1 Screening Fusion Trial Composition Table
    # Page 5: Level 2 Deep Meta-Optimizer Trial Composition Table
    # Page 6: Level 3 Main Bodies Synthesis Composition Table
    # Page 7: Level 3 Minor Bodies Synthesis Composition Table
    # Diagnostics & Corridors:
    # Page 8: Multi-Paradigm Global Ablation Audit (Selected Best vs Discarded Worst)
    # Page 9: Sliced Validation Corridors & Historical Training Timeline
    # Consultative Appendix:
    # Page 10: Appendix A - KAN Feature & Ephemerides Inventory (Best 1-3 vs Worst 1-3)
    # Page 11: Appendix B - Deep Learning Feature & Ephemerides Inventory (Best 1-3 vs Worst 1-3)
    # Page 12: Appendix C - LCS Feature & Ephemerides Inventory (Best 1-3 vs Worst 1-3)
    
    # Locate all available fusion tables across the hierarchical pipeline
    l1_table = minor_branch_dir / "03_level1_fusion/fusion_trials_composition_table.pdf"
    if not l1_table.exists():
        l1_table = main_study_dir / "03_level1_fusion/fusion_trials_composition_table.pdf"

    l2_table = minor_branch_dir / "04_level2_deep_meta_optimizer/level2_fusion/fusion_trials_composition_table.pdf"
    if not l2_table.exists():
        l2_table = main_study_dir / "04_level2_deep_meta_optimizer/level2_fusion/fusion_trials_composition_table.pdf"

    l3_main_table = main_study_dir / "05_level3_final_fusion/fusion_trials_composition_table.pdf"
    l3_minor_table = minor_branch_dir / "05_level3_final_fusion/fusion_trials_composition_table.pdf"

    benchmark_pdf = super_fusion_dir / "multilevel_fusion_benchmark_comparison.pdf"
    if not benchmark_pdf.exists():
        benchmark_pdf = main_study_dir / "05_level3_final_fusion/multilevel_fusion_benchmark_comparison.pdf"

    pages_to_stitch = [
        super_fusion_dir / "compound_prospective_forecast.pdf",
        super_fusion_dir / "prospective_energy_magnitude_spectrum.pdf",
        benchmark_pdf,
        l1_table,
        l2_table,
        l3_main_table,
        l3_minor_table,
        ablation_pdf,
        super_fusion_dir / "compound_validation_report.pdf",
    ]
    # Append the 3 consultative appendix pages
    for app_pdf in appendix_pdfs:
        if app_pdf.exists():
            pages_to_stitch.append(app_pdf)

    master_pdf_path = super_fusion_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.pdf"
    raw_pages = []

    for pdf_file in pages_to_stitch:
        if pdf_file.exists():
            reader = PdfReader(str(pdf_file))
            for page in reader.pages:
                raw_pages.append((pdf_file.name, page))
            print(f"Appended to Super-Fusion Master PDF: {pdf_file.name} ({len(reader.pages)} pages)")
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
            0.985, 0.022,
            f"Page {i} of {total_pages}",
            ha="right", va="bottom",
            fontsize=9.5, fontweight="bold",
            color="#1E293B",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#FFFFFF", edgecolor="#64748B", alpha=0.95, linewidth=1.0),
        )
        fig.savefig(buf, format="pdf", transparent=True)
        plt.close(fig)
        buf.seek(0)
        
        overlay = PdfReader(buf)
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with master_pdf_path.open("wb") as stream:
        writer.write(stream)
    print(f"Successfully compiled Super-Fusion Master PDF ({len(writer.pages)} Pages with visible Page Numbers) -> {master_pdf_path}")
    return master_pdf_path
