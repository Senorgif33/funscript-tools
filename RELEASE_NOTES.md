## What's New in v2.5.5

### New Features

1. **Beat-sync extract (3P)** — New event `mcb_extract_beat`: same pulse/amp shell and hub–spoke geometry as `mcb_extract`, but pole dwells advance every 2nd L0 beat (base `{name}.funscript` or `L0`/`l0` axis).
2. **Beat-sync extract (4P)** — New event `mcb_extract_4p_beat`: same shell as `mcb_extract_4p`, with pad dwells on every 2nd L0 beat.
3. **Manual switch offsets** — Optional `params.switch_offsets_ms` in the events file overrides L0-derived switch times (list or comma-separated ms offsets from event start).
4. **Sparse-L0 fallback** — If there is no L0 / base stroke and no `switch_offsets_ms` (or beats are too sparse), dwells fall back to the original SCD `~dur` schedule. Apply warns when that happens.

### Improvements

1. **No-repeat spokes** — Hub (N / E1) still alternates every other dwell; consecutive spoke picks avoid repeating the previous spoke (applies to all extract variants, including the original SCD-timed events).

### Unchanged

1. Existing `mcb_extract` / `mcb_extract_4p` keep SCD absolute `~dur` dwell timing; only the new `*_beat` siblings use L0 beat sync.
