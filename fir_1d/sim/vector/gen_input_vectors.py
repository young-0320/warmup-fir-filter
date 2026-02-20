# File: gen_input_vectors.py
# Role: 원본 이미지를 grayscale uint8 입력 벡터(.npy)와 매니페스트로 변환한다.
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np


THIS_FILE = Path(__file__).resolve()
DEFAULT_IMAGE_DIR = THIS_FILE.parent.parent / "img"
DEFAULT_OUTPUT_DIR = THIS_FILE.parent / "input"
SUPPORTED_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}


def _load_image_gray_u8(image_path: Path) -> np.ndarray:
    """
    Read image as grayscale uint8 matrix (H x W).
    """
    try:
        from PIL import Image  # type: ignore

        with Image.open(image_path) as img:
            gray = img.convert("L")
            arr = np.asarray(gray, dtype=np.uint8)
        if arr.ndim != 2:
            raise ValueError(f"Expected 2D grayscale image, got shape={arr.shape}.")
        return arr
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required. Install with: `uv add pillow`.") from exc


def _iter_image_files(image_dir: Path) -> list[Path]:
    files = [p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    return sorted(files, key=lambda p: p.name.lower())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_preview_json_compact_rows(path: Path, payload: dict) -> None:
    """
    Write preview JSON so each preview row is a single line:
      [1,2,3],
      [4,5,6]
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if "preview_rows_u8" not in payload:
        _write_json(path, payload)
        return

    rows = payload["preview_rows_u8"]
    meta_keys = [k for k in payload.keys() if k != "preview_rows_u8"]

    lines: list[str] = ["{"]
    for key in meta_keys:
        key_s = json.dumps(key, ensure_ascii=False)
        val_s = json.dumps(payload[key], ensure_ascii=False)
        lines.append(f"  {key_s}: {val_s},")

    lines.append('  "preview_rows_u8": [')
    for idx, row in enumerate(rows):
        suffix = "," if idx < (len(rows) - 1) else ""
        row_s = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
        lines.append(f"    {row_s}{suffix}")
    lines.append("  ]")
    lines.append("}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_preview(gray_u8: np.ndarray, *, max_rows: int = 8, max_cols: int = 16) -> dict:
    h, w = gray_u8.shape
    pr = min(h, max_rows)
    pc = min(w, max_cols)
    patch = gray_u8[:pr, :pc].tolist()
    return {
        "preview_kind": "top_left_patch",
        "preview_shape": [pr, pc],
        "preview_rows_u8": patch,
        "stats": {
            "min": int(gray_u8.min()),
            "max": int(gray_u8.max()),
            "mean": float(gray_u8.mean()),
            "std": float(gray_u8.std()),
        },
    }


def generate_input_vector_jsons(
    image_dir: Path = DEFAULT_IMAGE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    overwrite: bool = False,
) -> dict:
    """
    Generate per-image preview JSON and per-image NumPy .npy data files.
    """
    image_dir = image_dir.resolve()
    output_dir = output_dir.resolve()

    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    image_files = _iter_image_files(image_dir)
    if not image_files:
        raise FileNotFoundError(f"No image files found in: {image_dir}")

    cases: list[dict] = []
    generated_cases = 0
    skipped_cases = 0
    for idx, image_path in enumerate(image_files):
        gray_u8 = _load_image_gray_u8(image_path)
        h, w = gray_u8.shape

        case_name = f"case_{idx:03d}_{image_path.stem}"
        data_file = output_dir / f"{case_name}_x_u8.npy"
        preview_file = output_dir / f"{case_name}_preview.json"

        # overwrite=False에서 기존 벡터/프리뷰가 모두 있으면 중복 생성하지 않는다.
        if (data_file.exists() and preview_file.exists()) and not overwrite:
            skipped_cases += 1
        else:
            np.save(data_file, gray_u8)

            payload = {
                "case_name": case_name,
                "image_name": image_path.name,
                "source_path": str(image_path),
                "width": w,
                "height": h,
                "dtype": "uint8",
                "layout": "row_major_2d",
                "data_file": data_file.name,
                **_make_preview(gray_u8),
            }
            _write_preview_json_compact_rows(preview_file, payload)
            generated_cases += 1

        cases.append(
            {
                "case_name": case_name,
                "image_name": image_path.name,
                "width": w,
                "height": h,
                "dtype": "uint8",
                "data_npy": data_file.name,
                "preview_json": preview_file.name,
            }
        )

    manifest = {
        "note": "FIR 1D input vectors: pixel data in .npy, small previews in .json.",
        "source_image_dir": str(image_dir),
        "output_dir": str(output_dir),
        "num_images": len(cases),
        "overwrite": bool(overwrite),
        "generated_cases": generated_cases,
        "skipped_cases": skipped_cases,
        "cases": cases,
    }
    _write_json(output_dir / "input_vector_manifest.json", manifest)
    return manifest


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate FIR 1D input vectors (.npy) and preview/manifest JSON files."
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help=f"Directory containing source images (default: {DEFAULT_IMAGE_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write input vectors and manifest (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing case files instead of skipping duplicates.",
    )
    return parser


if __name__ == "__main__":
    _t0 = perf_counter()
    try:
        _args = _build_argparser().parse_args()
        m = generate_input_vector_jsons(
            image_dir=_args.image_dir,
            output_dir=_args.output_dir,
            overwrite=_args.overwrite,
        )
        _elapsed = perf_counter() - _t0
        print(
            "[OK] gen_input_vectors "
            "file=gen_input_vectors.py "
            f"generated={m['generated_cases']} skipped={m['skipped_cases']} failed=0 "
            f"elapsed={_elapsed:.2f}s out={m['output_dir']}"
        )
    except Exception as exc:
        _elapsed = perf_counter() - _t0
        print(
            "[FAIL] gen_input_vectors "
            "file=gen_input_vectors.py "
            f"generated=0 skipped=0 failed=1 "
            f"elapsed={_elapsed:.2f}s out={DEFAULT_OUTPUT_DIR.resolve()} "
            f'error="{exc}"'
        )
        raise
