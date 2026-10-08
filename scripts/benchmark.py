"""Measures plate reading accuracy on a labeled set of photos.

Usage:
    uv run python scripts/benchmark.py path/to/labels.csv [--detector-model ...] [--ocr-model ...]

labels.csv has two columns: image_path (relative to the CSV) and plate_text (exactly as
printed on the plate, e.g. ABC1234 or BRA2E19; dashes and spaces are ignored).
"""

import argparse
import csv
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from plate_reader_api.brazilian_plate import BrazilianPlate
from plate_reader_api.reader import DEFAULT_DETECTOR_MODEL, DEFAULT_OCR_MODEL, PlateReader

CONFIDENCE_THRESHOLDS = (0.5, 0.7, 0.8, 0.9, 0.95)


@dataclass(frozen=True)
class Sample:
    image_path: str
    expected: str
    read: BrazilianPlate | None
    seconds: float

    @property
    def correct(self) -> bool:
        return self.read is not None and self.read.text == self.expected

    @property
    def expected_format(self) -> str:
        return "old" if self.expected[4].isdigit() else "mercosul"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--detector-model", default=DEFAULT_DETECTOR_MODEL)
    parser.add_argument("--ocr-model", default=DEFAULT_OCR_MODEL)
    args = parser.parse_args()

    reader = PlateReader(detector_model=args.detector_model, ocr_model=args.ocr_model)
    with args.labels.open(newline="") as labels_file:
        rows = list(csv.DictReader(labels_file))

    samples = [run_sample(reader, args.labels.parent, row) for row in rows]
    print_report(samples, args.detector_model, args.ocr_model)


def run_sample(reader: PlateReader, base_dir: Path, row: dict[str, str]) -> Sample:
    path = base_dir / row["image_path"]
    image = cv2.imread(str(path))
    if image is None:
        raise SystemExit(f"Could not open image: {path}")

    start = time.perf_counter()
    readings = reader.read(image)
    seconds = time.perf_counter() - start

    return Sample(
        image_path=row["image_path"],
        expected=row["plate_text"].upper().replace("-", "").replace(" ", ""),
        read=readings[0].plate if readings else None,
        seconds=seconds,
    )


def print_report(samples: list[Sample], detector_model: str, ocr_model: str) -> None:
    print(f"Models: {detector_model} + {ocr_model}")
    print(f"Images: {len(samples)}")
    print(f"No plate found: {format_ratio(sum(s.read is None for s in samples), len(samples))}")
    print(f"Exact reads (7/7): {format_ratio(sum(s.correct for s in samples), len(samples))}")
    for plate_format in ("old", "mercosul"):
        group = [s for s in samples if s.expected_format == plate_format]
        print(f"  {plate_format}: {format_ratio(sum(s.correct for s in group), len(group))}")

    latencies_ms = sorted(s.seconds * 1000 for s in samples)
    p95_ms = latencies_ms[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.95))]
    print(f"Latency: mean {statistics.mean(latencies_ms):.0f} ms, p95 {p95_ms:.0f} ms")

    print("\nMin confidence | accepted | exact reads among accepted")
    for threshold in CONFIDENCE_THRESHOLDS:
        accepted = [s for s in samples if s.read is not None and s.read.confidence >= threshold]
        print(
            f"  {threshold:.2f}         | {format_ratio(len(accepted), len(samples))} "
            f"| {format_ratio(sum(s.correct for s in accepted), len(accepted))}"
        )

    errors = [s for s in samples if not s.correct]
    if errors:
        print("\nErrors:")
        for sample in errors:
            read = f"{sample.read.text} ({sample.read.confidence:.2f})" if sample.read else "no plate"
            print(f"  {sample.image_path}: expected {sample.expected}, read {read}")


def format_ratio(count: int, total: int) -> str:
    return f"{count / total:.1%} ({count}/{total})" if total else "n/a"


if __name__ == "__main__":
    main()
