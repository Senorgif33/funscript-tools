## What's New in v2.5.7

### New Features

1. **Dual extract** — `mcb_extract_dual` writes 3P hub–spoke (alpha/beta, including prostate twins) and 4P hub–spoke (e1–e4) from one SCD `~dur` schedule. Pulse, width, and volume are written once.
2. **Dual extract beat** — `mcb_extract_beat_dual` does the same on the L0 beat clock (every 2nd beat, or `switch_offsets_ms`, else SCD `~dur`).
3. **Linux AppImage config** — Frozen builds save `config.json` and `config.event_definitions.yml` under `$XDG_CONFIG_HOME/RestimFunscriptProcessor` (usually `~/.config/...`). **Open Config Folder** opens that directory.
4. **App icon** — Restim mark with red wrench for AppImage / desktop launcher (and Windows `.ico`). The running window sets the panel/taskbar icon (not the generic AppImage gear).

### Improvements

1. **One event per rig** — Missing alpha/beta or e1–e4 axes are skipped, so the same event plays on a 3P box, a 4P box, or both. Two 3P boxes share the prostate copy. Two 4P boxes share one e1–e4 stream.

### Unchanged

1. `corrupt_4p`.
2. No alias from `mcb_extract`, `mcb_extract_4p`, `mcb_extract_beat`, or `mcb_extract_4p_beat`. Those names fail Apply until the events file is updated.
