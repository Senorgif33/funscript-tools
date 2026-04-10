# What's New in v2.3.4

## Video Playback Performance Improvements

1. **No more audio blip on seek** — player is muted during the brief decode window when seeking while paused; volume restores cleanly on resume or play
2. **Faster frame rendering** — canvas image item is reused each frame (`itemconfig`) instead of deleted and recreated, reducing per-frame overhead
3. **Cached canvas dimensions & metadata** — canvas size is cached via a `<Configure>` binding; video duration and FPS are read from metadata only once after the first successful decode
4. **Throttled UI updates** — time label and seek bar update at ~5 fps during playback (still update immediately on seek/pause); timeline canvas redraws throttled to ~15 fps during playback while the playhead continues to update every tick

## Bug Fixes

1. **Video open error shown in UI** — errors when opening a video file are caught and displayed in the status label instead of crashing silently
2. **Events auto-load no longer crashes on empty YAML** — loading an events file that has no `events` key or is completely empty no longer raises an `AttributeError`; event file path and dirty state are also now correctly set even when the events list is empty
