# Changelog

## 0.3.1 — Home-Assistant-Integration (2026-11-15)

### Fixed
- Serialize simultaneous mutating Fleet Guard API requests **per monitored host** using an asynchronous lock, held until the current maintenance job completes. This prevents losing all but one selected update when Home Assistant sends a multi-entity `update.install` request while the agent accepts only one active mutating job.
- Update the separately installed Home Assistant batch script: iterate through the chosen Docker image update entities with `repeat.for_each` and send one `update.install` per entity. Errors in an individual operation no longer prevent attempting the remaining entities; users must still inspect per-item job status.
- Restrict the Docker image notification counter to Fleet Guard update entity IDs ending in `_image`, excluding apt/proxmox packages.

### Notes
- **One user confirmation**, not necessarily simultaneous execution on the same Docker host.
- Separate monitored hosts may be updated concurrently using the integration; each host serializes mutating jobs.
- No changes to the Linux/Synology agent. `allowed_actions` and `compose_projects` are unchanged.
- Genuine parallel updates on a single host require a separately tested agent implementation with per-project locks and resource limits.
- The batch YAML package is **not included** in HACS integration downloads.

## 0.3.0 — Imported existing Home Assistant integration

- Current working Home Assistant integration sources imported without changing runtime behavior.
