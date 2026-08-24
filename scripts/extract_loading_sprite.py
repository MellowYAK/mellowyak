#!/usr/bin/env python3
"""Split and normalize the canonical eight-frame MellowYak loading sheet."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def is_baked_background(pixel: tuple[int, int, int]) -> bool:
    """Match only the bright, near-neutral checkerboard baked into the source."""

    return min(pixel) >= 228 and max(pixel) - min(pixel) <= 14


def remove_connected_background(frame: Image.Image) -> Image.Image:
    rgb = frame.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        offset = y * width + x
        if not background[offset] and is_baked_background(pixels[x, y]):
            background[offset] = 1
            queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    rgba = rgb.convert("RGBA")
    output = rgba.load()
    for y in range(height):
        for x in range(width):
            if background[y * width + x]:
                red, green, blue, _ = output[x, y]
                output[x, y] = (red, green, blue, 0)
    return rgba


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()

    sheet = Image.open(arguments.source)
    width, height = sheet.size
    if width % 4 or height % 2:
        raise SystemExit(
            f"sprite dimensions must divide into 4x2 equal cells: {width}x{height}"
        )

    frame_width = width // 4
    frame_height = height // 2
    frames: list[Image.Image] = []
    for row in range(2):
        for column in range(4):
            left = column * frame_width
            top = row * frame_height
            cell = sheet.crop((left, top, left + frame_width, top + frame_height))
            frames.append(remove_connected_background(cell))

    visible_boxes = [frame.getchannel("A").getbbox() for frame in frames]
    if any(box is None for box in visible_boxes):
        raise SystemExit("one or more sprite cells contain no visible pixels")
    boxes = [box for box in visible_boxes if box is not None]
    shared_box = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )

    arguments.output.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames, start=1):
        target = arguments.output / f"mellowyak-loading-{index:02d}.png"
        frame.crop(shared_box).save(target, optimize=True)

    print(f"source={width}x{height}")
    print(f"cell={frame_width}x{frame_height}")
    print(f"shared_crop={shared_box}")
    print(f"output={shared_box[2] - shared_box[0]}x{shared_box[3] - shared_box[1]}")


if __name__ == "__main__":
    main()
