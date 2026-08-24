# MellowYak startup animation assets

The canonical source is `sheet/mellowyak-loading-sheet.png` (SHA-256 `e0851800f5b51764381ec42fb0e63191b6b5b2e81b920dfafd49d76d0fe685c8`). Its measured dimensions are 1536×1024 pixels: four equal columns by two equal rows, producing eight 384×512 cells in strict row-major order.

Although the supplied image was described as transparent, the delivered PNG is RGB and contains a baked light checkerboard plus a light-background shadow matte. `scripts/extract_loading_sprite.py` flood-fills only neutral background pixels connected to each cell edge, then removes one remaining neutral boundary pixel where the light matte contaminated the artwork edge. Colored cyan effects and enclosed light fur and horns are preserved. It computes one union visibility rectangle `(15, 82, 335, 445)` and applies that exact rectangle to every frame. The eight optimized RGBA PNG exports are therefore all 320×363 pixels with identical canvas geometry and character anchors. A dark-background review is required because a light checkerboard preview can hide residual halos.

Reproduce the exports from the repository root:

```bash
python3 scripts/extract_loading_sprite.py \
  assets/mascot/loading/sheet/mellowyak-loading-sheet.png \
  assets/mascot/loading/frames
```

Frame order is fixed: top-left through top-right, then bottom-left through bottom-right. The desktop preloads all eight files, plays the requested variable frame timings only during active startup, pauses while hidden, settles on frame 8 at ready/error, and uses static frame 2 when reduced motion is requested.
