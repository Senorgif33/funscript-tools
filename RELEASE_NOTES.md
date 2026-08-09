## What's New in v2.5.0

### Features

1. **Favorite events in Custom Event Builder** — Right-click or use the Favorite button to pin events; a Favorites category appears at the top of the Event Library. Favorites persist in `config.json` (`ui.favorite_events`).

2. **Embedded video in Custom Event Builder** — Video preview is no longer a floating window. The middle pane is a **Video | Parameters** notebook. Loading a video expands the window toward the work area (large videos maximize), while library, event list, timeline (~200px), and options/action bars keep their default absolute sizes. The window is a normal resizable window with minimize/maximize/close.

### Bug Fixes

1. **Config path and frozen builds** — `config.json` is resolved next to the executable when frozen (cwd-independent). Settings use deep copies so nested defaults are not shared/mutated incorrectly. Validation warnings no longer discard a user's loaded config file.

2. **Starter config packaging** — Windows builds no longer bundle `config.json` into the exe datas; release packages still ship a starter `config.json` for fresh installs so upgrades do not overwrite user settings.

3. **Timeline hit-testing** — Block hit-test rectangles stay in sync with the events list (deferred redraw race), so overlapping/stacked events remain selectable.
