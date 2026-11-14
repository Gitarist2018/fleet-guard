# Fleet Guard – current deployment status

This repository currently contains **a Home Assistant dashboard and notification package only**. It is **not yet** a fully installable Fleet Guard agent / custom integration distribution. Never treat the contents as a tested release of the agent.

## Prerequisites

The HA integration must already expose per-container `update.*` entities, otherwise the template sensor cannot detect those missing update entities. Agent-reported image updates alone do not automatically make an `update.*` entity available.

Install `homeassistant/packages/fleet_guard_updates.yaml` under `/config/packages/` if your `configuration.yaml` includes `homeassistant: packages: !include_dir_named packages`. Validate Home Assistant configuration before restart. The dashboard card needs `custom:auto-entities`.

## Synology

Seven configured Compose projects and image scanning were verified; Sonarr and Radarr each reported an update on 2026-11-14. Keep `allowed_actions: []` until Portainer Compose project directories, .env, and bind mounts are validated for the agent execution context. The container's `/host-volume1` path is not inherently a valid path for bind mounts on the Synology Docker daemon.

## Debian

The existing systemd agent and its actual Compose project path configuration require inspection before enabling any update actions. Never apply `compose_update` to a stack until mounts and environment resolution are validated.

## Release and secrets policy

Do not commit agent tokens, certificates, backups, credentials, `.env` files, or host-specific `config.json`. Releases and auto-updaters will be added **after** the live sources have been reviewed and tested. Updates should remain human-approved, with explicit per-container confirmation and status checks.

## Next steps

1. Review and import installed `custom_components/fleet_guard` source without secrets.
2. Review installed Linux agent source, existing test coverage and API compatibility.
3. Add install/update scripts with version pinning, SHA-256/signature verification, atomic installs and rollback.
4. Validate Compose and standalone updates separately on Debian and Synology.
5. Add HACS metadata and GHCR publishing only when integration/agent are releasable.
