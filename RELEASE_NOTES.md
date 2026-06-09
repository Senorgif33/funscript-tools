## What's New in v2.4.5

### New Features

1. **MCB extract / Relentless mode events** — new custom event definitions replicating SC Extract pole-switching:
   - `mcb_extract` and `mcb_extract_additive` (3P alpha/beta)
   - `mcb_extract_4p` and `mcb_extract_4p_additive` (4P e4→e1 upward pull, configurable `step_ratio`)
   - `mcb_extract_4p_smooth` and `mcb_extract_4p_smooth_additive` (smooth triangle climb on e4–e2)
   - `corrupt_4p` (4P inharmonic sawtooth drift)

### Improvements

1. **Modulation waveform accuracy** — `_ensure_dense_timestamps()` inserts interpolated points before applying modulation so triangle/sawtooth events render faithfully on sparse axes.
2. **Custom Event Builder** — Funscript snap mode (default), proportional event blocks at any zoom, stable lane layout, waveform downsampling for performance, debounced zoom/pan redraw, VLC seek-bar fixes when switching videos.
3. **Dark mode** — blue info labels use a lighter accent color for readability.
4. **Windows build** — PyInstaller onefile spec; release package assembles a versioned folder with exe and documentation.

---

## What's New in v2.4.4

### Bug Fixes

1. **Tear-shaped prostate algorithm — complete rewrite** — replaced the segment-based polar arc algorithm with a simpler, provably correct formula:
   - **Alpha** tracks the funscript position directly (0→1 maps to left→right).
   - **Beta** traces a sine arc above or below 0.5 for each stroke:
     - Upstrokes arc **above** β=0.5 (wide side of the tear).
     - Downstrokes arc **below** β=0.5 using `min_distance_from_center` as the narrow/wide ratio.
     - Arc height scales with stroke range: `bulge = stroke_range / 2`, capped at 0.5.
   - Because `sin(0) = sin(π) = 0`, beta is **exactly 0.5 at every stroke extremum** — consecutive strokes connect with zero discontinuity and the tear shape never resets mid-oscillation.
   - Strokes shorter than 25% of the full range produce no arc (beta stays at 0.5), so small oscillations glide smoothly along the alpha axis without generating tiny restart loops.

---
