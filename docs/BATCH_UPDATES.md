# Fleet Guard – Sammelupdates (Fehlerbehebung v0.3.1)

## Ursache der verlorenen Mehrfach-Updates

Der alte Home-Assistant-Sammelaufruf verwendete einmalig `update.install` mit **allen** ausgewählten Entitäten. Home Assistant kann dabei mehrere `async_install`-Methoden gleichzeitig aufrufen. Der aktuelle Fleet-Guard-Agent akzeptiert aber nur **einen wartenden oder laufenden mutierenden Job pro Host**. Andere parallele Anfragen wurden abgewiesen, sodass oft nur ein Container aktualisiert wurde.

## Zwei ergänzende Korrekturen

1. **Home-Assistant-Integration v0.3.1**: `FleetCoordinator.perform` verwendet ein `asyncio.Lock` **pro Host** für mutierende Wartungsoperationen und hält die Sperre bis zum Ende des Jobs. Mehrfachaufrufe aus der normalen Home-Assistant-Updateoberfläche werden auf demselben Host nacheinander abgearbeitet. Andere Hosts haben unabhängige Sperren, können also parallel aktualisieren.
2. **Optionales Sammel-Skript**: `homeassistant/packages/fleet_guard_updates.yaml` ruft für jede ausgewählte Entität **separat und nacheinander** `update.install` auf (`repeat.for_each`). Nur eine Auswahl und Bestätigung sind notwendig. `continue_on_error: true` verhindert, dass ein einzelner Fehler den Versuch bei den anderen ausgewählten Containern unterdrückt. **Es bestätigt nicht den Erfolg!** In den Skript-Traces und Fleet-Guard-Jobs sind etwaige Fehler zu prüfen.

Es gibt **keine echte Parallelität innerhalb eines einzelnen Hosts**. Sie würde getrennte Workers, Compose-Projekt-Sperren, Ressourcenlimits und Healthcheck-/Rollback-Strategien im Linux-Agent voraussetzen.

## Installation

### HACS-Version aktualisieren

1. Home Assistant vollständig sichern.
2. HACS → Fleet Guard → aktualisierte `main`-Version **erneut herunterladen** (Version in `manifest.json`: `0.3.1`). Falls HACS keine Updatebenachrichtigung anzeigt, manuell die neueste Version herunterladen.
3. Home Assistant neu starten.
4. Unter Einstellungen → Geräte & Dienste → Fleet Guard vorhandene Hosts und Update-Entitäten prüfen. **Keine** Host-Einträge löschen.

### Optional: Sammel-Skript aktualisieren

1. Inhalt von [`homeassistant/packages/fleet_guard_updates.yaml`](../homeassistant/packages/fleet_guard_updates.yaml) in `/config/packages/fleet_guard_updates.yaml` ersetzen (vorhandene Datei vorher sichern).
2. Unter Entwicklerwerkzeuge → YAML die Konfiguration prüfen und HA danach neu starten.
3. Einstellungen → Automatisierungen & Szenen → Skripte → **Fleet Guard: ausgewählte Docker-Container aktualisieren** öffnen.
4. Zwei **unkritische** Container mit gültigen Backups auswählen, **Updates jetzt installieren** aktivieren und den Sammelauftrag einmal starten.
5. Nach Ende Skript-Traces unter dem Skript, Agent-Jobstatus, Docker-Zustand und App-Funktion prüfen. Die Update-Entitäten können wegen des Registry-Scan-Caches bis zum nächsten Scan weiterhin `on` anzeigen.

## Schutzmaßnahmen

- Keine automatischen oder geplanten Updates durch diese Änderung.
- Agent-seitige `allowed_actions` und `compose_projects` bleiben unverändert.
- Fehler einzelner Container können in der Sammelaktion übersprungen werden; **nicht** aus einem beendeten Skript auf erfolgreichen Abschluss aller Updates schließen.
- Bei Portainer-Compose-Projekten vor produktiven Updates Bind-Mounts, ENV-Dateien und Projektverzeichnisse validieren. Die HA-Sperre löst keine Compose-Pfadprobleme.
- Das Sammel-Skript startet keine zweite Ausführung, solange eine erste läuft (`mode: single`).
- Vor Datenbank- und Mehrcontainer-Upgrades Sicherungen anlegen und Abhängigkeiten berücksichtigen.

## Rückweg

Bei Problemen die vorherige Integration aus der Home-Assistant-Sicherung bzw. dem archivierten `fleet_guard_ha.tar.gz` wiederherstellen und Home Assistant neu starten. Falls nur das Sammel-Skript Probleme verursacht, die gesicherte YAML-Datei zurückkopieren und Skripte neu laden.
