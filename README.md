# Fleet Guard

Fleet Guard is an experimental Home Assistant and Linux/Docker fleet-management project.

> **Current repository state:** This repository contains only an initial Home Assistant notification/dashboard package and deployment notes. **It is not yet a complete, tested, or installable Fleet Guard agent / custom integration release.** No automatic host or container update is enabled by committing these files.

## Included

- [Home Assistant notification package](homeassistant/packages/fleet_guard_updates.yaml) — counts existing `fleet_guard` `update.*` entities with state `on`, raises a persistent notification, and dismisses it when the count reaches zero. Unknown/unavailable states should be checked separately and **must not** be treated as verified current.
- [Simon42 dashboard card](homeassistant/cards/fleet_guard_simon42_auto_entities.yaml) — requires `custom:auto-entities` and existing per-container `update.*` entities from the Fleet Guard integration.
- [Deployment and security notes](docs/DEPLOYMENT.md).

## Safety

- No Compose or standalone updates are run by the files currently in this repository.
- On Synology, **keep `allowed_actions: []`** until Portainer-specific Compose paths, environment files, and volume mounts have been verified in the execution context.
- Review the Debian agent's installed Compose project configuration and container mount paths before enabling updates.
- Tokens, TLS private keys, `.env` files, backups and host-specific `config.json` files must never be committed.

## Roadmap

Import and review the exact deployed sources for the Home Assistant integration and Debian/Synology agents; add tests, explicit per-container update confirmation, job status and health checks, and reliable notification clearing; then implement signed/version-pinned agent installers and rollback, GitHub Releases, HACS installation and GHCR images.

See [deployment notes](docs/DEPLOYMENT.md) for prerequisites and the current limitations.
