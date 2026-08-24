#!/usr/bin/env python3
"""Extract the 4x4 MellowYak mascot sheet without changing source pixels."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from PIL import Image

POSE_NAMES = (
    "yak-neutral",
    "yak-wave",
    "yak-thinking",
    "yak-peek-laptop",
    "yak-wink-thumbsup",
    "yak-warning-stop",
    "yak-teaching-map",
    "yak-security-shield",
    "yak-working-laptop",
    "yak-search-inspect",
    "yak-alert-point",
    "yak-success-check",
    "yak-confused",
    "yak-sleeping",
    "yak-celebrate",
    "yak-relaxed-chair",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


ALPHA_NOISE_FLOOR = 2


def transparent_occupancy(alpha: Image.Image, axis: str) -> list[int]:
    width, height = alpha.size
    if axis == "x":
        return [
            sum(alpha.getpixel((x, y)) > ALPHA_NOISE_FLOOR for y in range(height))
            for x in range(width)
        ]
    return [
        sum(alpha.getpixel((x, y)) > ALPHA_NOISE_FLOOR for x in range(width))
        for y in range(height)
    ]


def separator(occupancy: list[int], expected: int, radius: int) -> int:
    start = max(0, expected - radius)
    end = min(len(occupancy), expected + radius + 1)
    runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for position in range(start, end):
        if occupancy[position] == 0 and run_start is None:
            run_start = position
        if occupancy[position] != 0 and run_start is not None:
            runs.append((run_start, position))
            run_start = None
    if run_start is not None:
        runs.append((run_start, end))
    if not runs:
        raise RuntimeError(f"No transparent separator found near pixel {expected}")
    left, right = max(runs, key=lambda run: run[1] - run[0])
    return (left + right) // 2


def grid_boundaries(alpha: Image.Image) -> tuple[list[int], list[int]]:
    width, height = alpha.size
    x_occupancy = transparent_occupancy(alpha, "x")
    y_occupancy = transparent_occupancy(alpha, "y")
    x = (
        [0]
        + [
            separator(x_occupancy, width * index // 4, width // 12)
            for index in range(1, 4)
        ]
        + [width]
    )
    y = (
        [0]
        + [
            separator(y_occupancy, height * index // 4, height // 12)
            for index in range(1, 4)
        ]
        + [height]
    )
    return x, y


def extract(source: Path, output_root: Path, padding: int) -> None:
    image = Image.open(source).convert("RGBA")
    alpha = image.getchannel("A")
    x_boundaries, y_boundaries = grid_boundaries(alpha)

    sheet_path = output_root / "sheet" / "mellowyak-sheet.png"
    poses_path = output_root / "poses"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    poses_path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, sheet_path)
    if sha256(source) != sha256(sheet_path):
        raise RuntimeError("The preserved sheet differs from the source")

    for index, name in enumerate(POSE_NAMES):
        row, column = divmod(index, 4)
        cell = image.crop(
            (
                x_boundaries[column],
                y_boundaries[row],
                x_boundaries[column + 1],
                y_boundaries[row + 1],
            )
        )
        content_mask = cell.getchannel("A").point(
            lambda value: 255 if value > ALPHA_NOISE_FLOOR else 0
        )
        content_box = content_mask.getbbox()
        if content_box is None:
            raise RuntimeError(f"No visible pixels detected for {name}")
        content = cell.crop(content_box)
        pose = Image.new(
            "RGBA",
            (content.width + padding * 2, content.height + padding * 2),
            (0, 0, 0, 0),
        )
        pose.alpha_composite(content, (padding, padding))
        destination = poses_path / f"{name}.png"
        pose.save(destination, format="PNG", optimize=True)
        if pose.getchannel("A").getbbox() != (
            padding,
            padding,
            pose.width - padding,
            pose.height - padding,
        ):
            raise RuntimeError(f"Unexpected transparent bounds for {name}")
        print(f"{name}: {pose.width}x{pose.height} -> {destination}")

    print(f"sheet_sha256={sha256(sheet_path)}")
    print(f"detected_columns={x_boundaries}")
    print(f"detected_rows={y_boundaries}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--padding", type=int, default=16)
    args = parser.parse_args()
    if args.padding < 1:
        raise SystemExit("Padding must be positive")
    extract(args.source.resolve(), args.output_root.resolve(), args.padding)


if __name__ == "__main__":
    main()
