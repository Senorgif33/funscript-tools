## What's New in v2.5.6

### New Features

1. **Save validation warning** — Saving an events file warns (Save anyway?) when timeline events would fail Apply — e.g. extract min duration, orgasm-countdown too short, bad `step_ratio`, unknown event names, missing tokens.
2. **Write Chapters** — Write OFS chapters to the base `.funscript` without applying event effects (Custom Event Builder button).
3. **Apply to All** — Copy the open event's parameters onto every timeline event of the same type. Each event keeps its own start time and duration.

### Improvements

1. **Beat extract min duration** — `*_beat` events allow `duration_ms` ≥ 25s (SCD extract stays 60s).
2. **Dense linear overwrite** — `apply_linear_change` densifies timestamps (like modulation); single-point windows use the end value so short pad softs/holds clear correctly.
3. **Per-event duration** — Save as Default does not store `duration_ms` or start time as the type default. Reset to Defaults restores effect parameters but keeps this event's duration.

### Unchanged

1. Existing `mcb_extract` / `mcb_extract_4p` / `*_beat` hub–spoke behavior.
2. Overlap warning on Save (still separate from Apply validation).
