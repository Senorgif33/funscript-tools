## What's New in v2.5.3

### New Features

1. **MCB goodBoy event** — `mcb_goodboy` (27 Hz / pulse width 50 / 5s) beside `mcb_submit`; pulse + small volume boost only (no α/β).
2. **MCB orgasm countdown** — `mcb_orgasm_countdown` (pulse/amp/goodBoy; base stroke untouched) and `mcb_orgasm_countdown_stroke_override` (same + overwrite α/β/e1–e4). Place on countdown "5"; orgasm peak at +21s.
3. **Timeline cue ticks** — Optional `timeline_cues` on event definitions drawn as ticks on timeline bars (orgasm cue); display-only.
4. **Orgasm countdown stretch** — On apply, climax (`seg_orgasm_ms`) grows/shrinks with `duration_ms` while lead-in and fade stay fixed; `goodboy_duration_ms = max(5000, 5000 × seg_orgasm_ms / 25867)`.

### Improvements

1. **Custom Event Builder single instance** — Reopening the builder focuses the existing window instead of spawning another.
2. **Apply Effects lock** — Prevents closing/restoring while apply is in progress; Apply button disabled during processing.
3. **Library vs timeline edit clarity** — Selecting a library event no longer silently edits a placed event; status/label make Add-to-Timeline explicit.
4. **Chapter export** — Writing chapters to the base funscript replaces existing chapters instead of merging.
