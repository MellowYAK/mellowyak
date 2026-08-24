#!/usr/bin/env python3
"""Split and normalize the canonical eight-frame MellowYak loading sheet."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image

BACKGROUND_MIN_CHANNEL = 110
BACKGROUND_MAX_CHROMA = 40
EDGE_MATTE_MIN_CHANNEL = 120
EDGE_MATTE_MAX_CHROMA = 70


def is_baked_background(pixel: tuple[int, int, int]) -> bool:
    """Match the connected neutral checkerboard and its baked gray shadow."""

    return (
        min(pixel) >= BACKGROUND_MIN_CHANNEL
        and max(pixel) - min(pixel) <= BACKGROUND_MAX_CHROMA
    )


def remove_neutral_edge_matte(image: Image.Image) -> None:
    """Drop one contaminated boundary pixel without eroding colored artwork."""

    width, height = image.size
    pixels = image.load()
    alpha = image.getchannel("A")
    alpha_pixels = alpha.load()
    contaminated: list[tuple[int, int]] = []

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if not alpha_pixels[x, y]:
                continue
            touches_transparency = any(
                not alpha_pixels[x + offset_x, y + offset_y]
                for offset_x in (-1, 0, 1)
                for offset_y in (-1, 0, 1)
                if offset_x or offset_y
            )
            if not touches_transparency:
                continue
            red, green, blue, _ = pixels[x, y]
            if (
                min(red, green, blue) >= EDGE_MATTE_MIN_CHANNEL
                and max(red, green, blue) - min(red, green, blue)
                <= EDGE_MATTE_MAX_CHROMA
            ):
                contaminated.append((x, y))

    for x, y in contaminated:
        red, green, blue, _ = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)


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
    remove_neutral_edge_matte(rgba)
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
