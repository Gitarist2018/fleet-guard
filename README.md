# Fleet Guard

Fleet Guard ist eine Home-Assistant-Integration zur Überwachung von Linux-Hosts, Docker-Containern und Proxmox. Die Integration kommuniziert über HTTPS mit einem Fleet-Guard-Agent auf jedem Host.

## Home-Assistant-Integration: v0.3.0

**Die im November 2026 hochgeladene, funktionsfähige HA-Integration v0.3.0 wurde vollständig und unverändert aus dem lokalen Archiv importiert**, ausgenommen zwei zusätzliche Dokumentationsfelder im `manifest.json`. Vor dem Import wurden Python-Syntax, JSON-Struktur und der Quelltextabgleich geprüft. Das ist noch keine Laufzeitprüfung unter Home Assistant.

HACS-Struktur:
- [Integration unter `custom_components/fleet_guard/`](custom_components/fleet_guard/)
- [HACS-Metadaten](hacs.json)
- [Anleitung zum Wechsel von lokaler Installation auf HACS](docs/HACS_MIGRATION.md)

**Keine bestehende Fleet-Guard-Integration unter `Einstellungen → Geräte & Dienste` löschen.** Vor der HACS-Installation eine Home-Assistant-Sicherung erstellen; die GitHub-Dateien liegen unter demselben Integrations-Domainnamen und behalten ihre Unique IDs bei.

HACS kann die HA-Integration aus `main` installieren. Derzeit gibt es noch keinen GitHub Release; Branch-Updates sind möglich, für produktive Releases sollen später versionierte GitHub Releases folgen.

## Weitere Home-Assistant-Bausteine

- [Updateübersicht und Benachrichtigungen](homeassistant/packages/fleet_guard_updates.yaml) einschließlich **manuell bestätigtem Sammelupdate-Skript**
- [Simon42-Dashboard-Karte](homeassistant/cards/fleet_guard_simon42_auto_entities.yaml)
- [Anleitung Sammelupdates](docs/BATCH_UPDATES.md)

Die `homeassistant/packages/`-Dateien sind **nicht Teil des HACS-Downloads**. Sie müssen momentan separat in die HA-Paketkonfiguration übernommen werden.

## Sicherheitsstatus

- HACS aktualisiert nur die HA-Integration, nicht die Linux-/Synology-Agenten.
- Fleet Guard führt Docker-Updates nur durch, sofern der jeweilige Agent seine Aktionen freigegeben hat; **es gibt keine automatischen Container-Updates durch einen HACS-Download**.
- Mehrere `update.install`-Aufrufe garantieren noch keine Parallelität. Die Agent-Warteschlange verarbeitet Jobs weiterhin kontrolliert nacheinander.
- **Synology:** Portainer-Compose-Pfade und Host-Mounts sind vor der Nutzung von `compose_update` zu validieren; siehe [Deployment-Hinweise](docs/DEPLOYMENT.md).
- Keine Tokens, TLS-Privatschlüssel, `.env` oder lokale Host-Konfiguration in GitHub committen.

## Noch offen

Die installierten Agent-Versionen für Debian, Synology und Proxmox liegen **noch nicht als überprüfte GitHub-Installationspakete** vor. Dazu fehlen die Agent-Quellstände und Tests für verlässliche Releases, Rollback und parallele Aktualisierung unterschiedlicher Docker-Stacks.

## Docker-Compose-Projekte automatisch erkennen (Debian)

Der [Discovery-Baustein](scripts/discover_compose_projects.py) erkennt vorhandene Compose-Projekte und Standalone-Container aus Docker-Metadaten. Er kann **eindeutig validierte** Compose-Projekte in die vorhandene Fleet-Guard-Agent-Konfiguration übernehmen, ohne Container auszuführen oder `allowed_actions` zu ändern. Portainer-/Dockhand-Quellen mit nicht eindeutig reproduzierbarer Umgebung werden nur zur Prüfung gemeldet.

[Anleitung für Debian, Sicherheit und Rückweg](docs/DOCKER_DISCOVERY.md). Der Baustein ist noch **kein selbstaktualisierender Agent-Release**; auf Synology vorerst nicht zur automatischen Konfigurationsänderung verwenden.
