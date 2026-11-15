# Fleet Guard – Deploymentstand

## Home Assistant

Die vollständige, zuvor manuell installierte **Home-Assistant-Integration v0.3.0** befindet sich nun unter `custom_components/fleet_guard/` und hat ein `hacs.json`. Der Quelltext wurde aus dem bereitgestellten Archiv übernommen und für HACS nur um die erforderlichen `manifest.json`-Links erweitert.

- [Sichere HACS-Migration](HACS_MIGRATION.md) – bestehende Geräte-/Host-Einträge **nicht** löschen.
- [Sammelupdate-Skript](BATCH_UPDATES.md) – **separat** über `homeassistant/packages/fleet_guard_updates.yaml` installieren.
- Die Integration wurde syntaktisch geprüft; ein tatsächlicher Home-Assistant-Laufzeittest steht aus.
- HACS verwaltet **nur** die HA-Integration. Agenten sind weiterhin extern zu installieren und zu aktualisieren.

## Synology

Bei der Prüfung am 2026-11-14 wurden sieben Compose-Projekte und 28 Compose-Dienste erkannt. Sonarr und Radarr waren aktualisierbar. Ob sie weiterhin aktualisierbar sind, hängt von den seitdem ausgeführten Updates ab.

**Wichtig:** In der Agent-Container-Konfiguration können Compose-Dateien über `/host-volume1/` lesbar sein. Docker-Bind-Mounts werden auf dem Host aufgelöst; relative Verzeichnisse und Portainer-`.env`-Dateien brauchen vor produktiven `compose_update`-Aktionen einen expliziten Test. Eine freigegebene Updateberechtigung ersetzt diesen Test nicht.

## Debian

Der installierte systemd-Agent muss vor einer Verteilung über GitHub Releases mit der tatsächlich auf dem Debian-Host laufenden Version abgeglichen werden. Compose-Projektverzeichnisse und Umgebungsdateien sind zu validieren.

## Proxmox

Host-Updates und Neustarts bleiben explizit freigegebene Wartungsaktionen. Keine automatischen Major-Upgrades.

## GitHub-Distribution

Noch offen: versionierte Releases, signierte oder per Hash geprüfte Agent-Installer, GHCR-Synology-Image, Rollback-Tests und projektbezogene Job-Parallelität. Keine stillen Updates.

## Zugangsdaten

Keine API-Tokens, Zertifikat-Privatschlüssel, Backups, Agent-`config.json`, `.env` oder Host-Credentials ins Repository committen.
