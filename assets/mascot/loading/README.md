# MellowYak startup animation assets

The canonical source is `sheet/mellowyak-loading-sheet.png` (SHA-256 `e0851800f5b51764381ec42fb0e63191b6b5b2e81b920dfafd49d76d0fe685c8`). Its measured dimensions are 1536×1024 pixels: four equal columns by two equal rows, producing eight 384×512 cells in strict row-major order.

Although the supplied image was described as transparent, the delivered PNG is RGB and contains a baked light checkerboard. `scripts/extract_loading_sprite.py` removes only bright, near-neutral pixels connected to each cell edge, preserving enclosed light fur and horns. It then computes one union visibility rectangle `(14, 81, 335, 450)` and applies that exact rectangle to every frame. The eight optimized RGBA PNG exports are therefore all 321×369 pixels with identical canvas geometry and character anchors.

Reproduce the exports from the repository root:

```bash
python3 scripts/extract_loading_sprite.py \
  assets/mascot/loading/sheet/mellowyak-loading-sheet.png \
  assets/mascot/loading/frames
```

Frame order is fixed: top-left through top-right, then bottom-left through bottom-right. The desktop preloads all eight files, plays the requested variable frame timings only during active startup, pauses while hidden, settles on frame 8 at ready/error, and uses static frame 2 when reduced motion is requested.
