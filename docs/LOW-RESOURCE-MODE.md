# Low-resource mode (Phase 1.3)

OpenLPUG targets a **modest older PC** by default (dual-core, 4–8 GB RAM, integrated GPU) while keeping
heavier, mid-range features **available but gated**. Low-resource mode is the single switch other code
consults before turning on anything expensive (motion backgrounds, video-in-video/PiP, richer WebEngine
features, etc.).

## The switch

Setting: **`core/low resource mode`** — a tri-state string, default `'auto'`:

| Value | Meaning |
|-------|---------|
| `'auto'` (default) | Derive from the hardware via `is_low_spec_hardware()` |
| `'on'` / `'true'` / `'1'` | Force low-resource mode on |
| `'off'` / `'false'` / `'0'` | Force it off |

Resolve it anywhere via the accessor — **never read the raw setting**:

```python
if Registry().get('settings').is_low_resource_mode():
    ...  # skip/limit the expensive path
```

`Settings.is_low_resource_mode()` lives in `openlp/core/common/settings.py`.

## Hardware detection

`openlp/core/common/platform.py`:

- `get_installed_memory()` → total physical RAM in bytes (Windows via `GlobalMemoryStatusEx`; Linux/macOS
  via `sysconf`), or `None` if it can't be determined.
- `is_low_spec_hardware()` → `True` when `cpu_count <= LOW_SPEC_CPU_COUNT` **or**
  `memory <= LOW_SPEC_MEMORY_BYTES`. Cached (hardware doesn't change during a run).

Thresholds are named constants so they can be tuned from real measurements without touching logic:

```python
LOW_SPEC_CPU_COUNT = 2
LOW_SPEC_MEMORY_BYTES = 4 * 1024 ** 3   # 4 GiB
```

> **Calibration pending:** the initial thresholds encode the "modest PC" baseline. They'll be reviewed
> against the live OpenLP memory/CPU figures captured on `bmserubi` during the Part C projector test
> (Task Manager: the `OpenLP`/`python.exe` process plus its `QtWebEngineProcess` children while a song is
> live). Adjust the constants — not the branching — once those numbers land.

## How features should use it

New heavy features (the Phase 2 set: video-behind-lyrics generalisation, PiP, stage-display motion) must:

1. Default their enablement through `is_low_resource_mode()` (off on low-spec, on otherwise), and
2. Expose their own explicit on/off setting so a user on capable hardware can still opt out, and a user on
   a modest PC that upgrades can opt in — without needing a rebuild.

This keeps the modest-PC promise while leaving the ceiling open, exactly as the project's perf target
requires.
