# Orchestration entrypoint for the FIR 1D end-to-end pipeline (vectors -> outputs -> reports -> images).
from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter
from typing import Any

from fir_1d.sim.vector.gen_3tap_compare_report import generate_3tap_compare_report
from fir_1d.sim.vector.gen_5tap_compare_report import generate_5tap_compare_report
from fir_1d.sim.vector.gen_fixed_output import (
    generate_fixed_3tap_output_vector,
    generate_fixed_5tap_output_vector,
)
from fir_1d.sim.vector.gen_ideal_output import (
    generate_ideal_3tap_output_vector,
    generate_ideal_5tap_output_vector,
)
from fir_1d.sim.vector.gen_input_vectors import generate_input_vector_jsons
from fir_1d.sim.vector.restore_images import restore_images


# Resolve selected taps from CLI value.
def _selected_taps(tap: str) -> list[str]:
    return ["3", "5"] if tap == "all" else [tap]


# Print one-line stage logs for orchestration progress.
def _log_stage(message: str) -> None:
    print(f"[pipeline] {message}")


# Execute the full FIR 1D workflow in a deterministic order.
def run_pipeline(
    *,
    tap: str,
    overwrite_vectors: bool,
    skip_input: bool,
    skip_ideal: bool,
    skip_fixed: bool,
    skip_report: bool,
    skip_restore: bool,
    restore_kind: str,
    ideal_policy: str,
    overwrite_images: bool,
    strict_report: bool,
    strict_restore: bool,
    top_k: int,
) -> dict[str, Any]:
    selected_taps = _selected_taps(tap)
    results: dict[str, Any] = {"selected_taps": selected_taps}

    if not skip_input:
        _log_stage("Generate input vectors")
        results["input_manifest"] = generate_input_vector_jsons(overwrite=overwrite_vectors)

    if not skip_ideal:
        _log_stage("Generate ideal outputs")
        ideal_counts: dict[str, int] = {}
        if "3" in selected_taps:
            ideal_counts["ideal_3tap"] = generate_ideal_3tap_output_vector(overwrite=overwrite_vectors)
        if "5" in selected_taps:
            ideal_counts["ideal_5tap"] = generate_ideal_5tap_output_vector(overwrite=overwrite_vectors)
        results["ideal_counts"] = ideal_counts

    if not skip_fixed:
        _log_stage("Generate fixed outputs")
        fixed_counts: dict[str, int] = {}
        if "3" in selected_taps:
            fixed_counts["fixed_3tap"] = generate_fixed_3tap_output_vector(overwrite=overwrite_vectors)
        if "5" in selected_taps:
            fixed_counts["fixed_5tap"] = generate_fixed_5tap_output_vector(overwrite=overwrite_vectors)
        results["fixed_counts"] = fixed_counts

    if not skip_report:
        _log_stage("Generate compare reports")
        report_results: dict[str, dict[str, Any]] = {}
        if "3" in selected_taps:
            report_results["report_3tap"] = generate_3tap_compare_report(top_k=top_k, strict=strict_report)
        if "5" in selected_taps:
            report_results["report_5tap"] = generate_5tap_compare_report(top_k=top_k, strict=strict_report)
        results["report_results"] = report_results

    if not skip_restore:
        _log_stage("Restore output images")
        restore_summary = restore_images(
            kind=restore_kind,
            tap=tap,
            ideal_policy=ideal_policy,
            overwrite=overwrite_images,
            strict=strict_restore,
        )
        results["restore_summary"] = {
            "num_converted": restore_summary["num_converted"],
            "num_skipped": restore_summary["num_skipped"],
        }

    return results


# Build CLI options for selective pipeline execution.
def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run FIR 1D end-to-end pipeline: vectors, ideal/fixed outputs, compare reports, and image restore."
    )
    parser.add_argument(
        "--tap",
        choices=("all", "3", "5"),
        default="all",
        help="Tap group to process (default: all).",
    )
    parser.add_argument(
        "--overwrite-vectors",
        action="store_true",
        help="Overwrite existing input/ideal/fixed vectors instead of skipping duplicates.",
    )
    parser.add_argument(
        "--skip-input",
        action="store_true",
        help="Skip input vector generation stage.",
    )
    parser.add_argument(
        "--skip-ideal",
        action="store_true",
        help="Skip ideal output generation stage.",
    )
    parser.add_argument(
        "--skip-fixed",
        action="store_true",
        help="Skip fixed output generation stage.",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip compare report generation stage.",
    )
    parser.add_argument(
        "--skip-restore",
        action="store_true",
        help="Skip restored image generation stage.",
    )
    parser.add_argument(
        "--restore-kind",
        choices=("all", "ideal", "fixed"),
        default="all",
        help="Restore kind passed to restore_images (default: all).",
    )
    parser.add_argument(
        "--ideal-policy",
        choices=("clip", "normalize"),
        default="clip",
        help="Ideal image restore policy (default: clip).",
    )
    parser.add_argument(
        "--overwrite-images",
        action="store_true",
        help="Overwrite existing restored images.",
    )
    parser.add_argument(
        "--strict-report",
        action="store_true",
        help="Enable strict validation mode in compare reports.",
    )
    parser.add_argument(
        "--strict-restore",
        action="store_true",
        help="Enable strict mode in restore_images.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k worst cases saved in compare reports (default: 5).",
    )
    return parser


# Run the FIR 1D pipeline from CLI with stage-level controls.
def main() -> None:
    """
    Execute the FIR 1D pipeline in this order:
    1) input vector generation
    2) ideal output generation (3tap/5tap)
    3) fixed output generation (3tap/5tap)
    4) ideal-vs-fixed compare report generation (CSV/JSON)
    5) restored image generation from output vectors

    Use --skip-* options to disable specific stages, --tap to limit to 3tap/5tap,
    and --overwrite-vectors to force regeneration of existing vector files.
    """
    args = _build_argparser().parse_args()

    _t0 = perf_counter()
    skipped_stages = sum(
        int(v)
        for v in (
            args.skip_input,
            args.skip_ideal,
            args.skip_fixed,
            args.skip_report,
            args.skip_restore,
        )
    )
    vector_out = (Path(__file__).resolve().parent / "fir_1d" / "sim" / "vector" / "output").resolve()
    image_out = (Path(__file__).resolve().parent / "fir_1d" / "sim" / "output_img").resolve()

    try:
        summary = run_pipeline(
            tap=args.tap,
            overwrite_vectors=args.overwrite_vectors,
            skip_input=args.skip_input,
            skip_ideal=args.skip_ideal,
            skip_fixed=args.skip_fixed,
            skip_report=args.skip_report,
            skip_restore=args.skip_restore,
            restore_kind=args.restore_kind,
            ideal_policy=args.ideal_policy,
            overwrite_images=args.overwrite_images,
            strict_report=args.strict_report,
            strict_restore=args.strict_restore,
            top_k=args.top_k,
        )

        _elapsed = perf_counter() - _t0
        generated_stages = len([k for k in summary.keys() if k != "selected_taps"])
        print(
            "[OK] pipeline_fir_1d "
            "file=pipeline_fir_1d.py "
            f"generated={generated_stages} skipped={skipped_stages} failed=0 "
            f"elapsed={_elapsed:.2f}s out={vector_out}|{image_out}"
        )
    except Exception as exc:
        _elapsed = perf_counter() - _t0
        print(
            "[FAIL] pipeline_fir_1d "
            "file=pipeline_fir_1d.py "
            f"generated=0 skipped={skipped_stages} failed=1 "
            f"elapsed={_elapsed:.2f}s out={vector_out}|{image_out} "
            f'error="{exc}"'
        )
        raise


# -----------------------------------------------------------------------------
# How to run
# -----------------------------------------------------------------------------
# 1) Direct venv python
#    cd /home/young/dev/10_warmup-fir-filter && \
#    /home/young/dev/10_warmup-fir-filter/.venv/bin/python \
#    pipeline_fir_1d.py --overwrite-vectors --overwrite-images
#
# 2) uv run
#    cd /home/young/dev/10_warmup-fir-filter && \
#    uv run python pipeline_fir_1d.py --overwrite-vectors --overwrite-images
#
# -----------------------------------------------------------------------------
# CLI interface (main options)
# -----------------------------------------------------------------------------
# --tap {all,3,5}
#    Select tap group to run.
# --overwrite-vectors
#    Overwrite existing input/ideal/fixed vector outputs.
# --overwrite-images
#    Overwrite existing restored image outputs.
# --skip-input / --skip-ideal / --skip-fixed / --skip-report / --skip-restore
#    Skip specific pipeline stages.
# --restore-kind {all,ideal,fixed}
#    Select which kind to restore at image stage.
# --ideal-policy {clip,normalize}
#    Policy for converting ideal float vectors to uint8 images.
# --strict-report / --strict-restore
#    Enable strict validation behavior.
# --top-k <int>
#    Number of worst cases stored in compare report summaries.

if __name__ == "__main__":
    main()
