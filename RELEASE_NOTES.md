## What's New in v2.5.4

### New Features

1. **MCB extract composite (3P)** — `mcb_extract` rebuilt from SCD Relentless→pleasure-overload: hub–spoke poles (N hub, L/R spokes), proportional pulse/amp schedule, absolute ~dur dwells, soft transitions, depth 0.75–0.95, pulse width 65. Default ~265s; min duration 60s.
2. **MCB extract composite (4P)** — `mcb_extract_4p` uses the same shell with E1 hub ↔ E2/E3/E4 one-hot spokes.
3. **Apply-time spoke RNG** — Spoke order is randomized once when the event is applied; optional `seed` param for reproducibility.
4. **Extract derive path** — Event processor derives pulse/amp segment params and bakes motion steps via `processing/extract_composite.py`.

### Breaking / Removals

1. Removed `mcb_extract_additive` and `mcb_extract_4p_additive` (replaced by the composite overwrite events above).
