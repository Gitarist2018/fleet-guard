# Docker-Compose-Autodiscovery für Fleet Guard (Debian / Linux)

**Stand: experimenteller Discovery-Baustein, noch kein neuer Fleet-Guard-Agent-Release.**

Docker kennt die Container und normalerweise die Compose-Labels `com.docker.compose.project`, `com.docker.compose.service`, `com.docker.compose.project.working_dir` und `com.docker.compose.project.config_files`. Die Labels sind nicht immer die aktuellen Host-Pfade; bei Portainer liegen sie oft innerhalb des Portainer-Containers.

Das Skript [`scripts/discover_compose_projects.py`](../scripts/discover_compose_projects.py) ermittelt alle Container (auch gestoppte), gruppiert Compose-Projekte, zeigt Standalone-Container und kann **geprüfte, bisher nicht registrierte Projekte** in der vorhandenen Agent-Konfiguration ergänzen.

Es führt **keine Docker-Updates** aus, aktiviert **keine Wartungsaktionen**, verändert **keine existierenden Compose-Zuordnungen** und löscht keine Projekte. Im Zweifel wird ein Projekt als `REVIEW` statt `AUTO-READY` markiert.

## Installation auf dem Debian-Docker-Host

Auf Debian 12, auf dem `fleet-agent` bereits als systemd-Dienst installiert ist und Docker samt Compose v2 vorhanden sind:

```bash
curl -fsSL https://raw.githubusercontent.com/Gitarist2018/fleet-guard/main/scripts/discover_compose_projects.py \
  -o /tmp/discover_compose_projects.py
python3 -m py_compile /tmp/discover_compose_projects.py
sudo install -m 0755 /tmp/discover_compose_projects.py /usr/local/lib/fleet-agent/discover_compose_projects.py

# Schritt 1: Nur anzeigen, KEINE Änderungen:
sudo python3 /usr/local/lib/fleet-agent/discover_compose_projects.py
```

Die Ausgabe unterscheidet:
- `AUTO-READY`: Compose-Quellen existieren, das Modell lässt sich laden und Image- sowie Bind-Mount-Konfiguration stimmen mit den bestehenden Containern überein
- `REVIEW`: Die Pfade, ENV-Dateien, die Docker-/Compose-Definition oder die aus Portainer abgeleitete Zuordnung kann nicht ausreichend sicher reproduziert werden
- `Standalone`: Docker-Container ohne Compose-Labels (werden weiterhin von der bestehenden Agent-Standalone-Erkennung behandelt)

**Keinen Secrets-Dump versenden.** Die Ausgabe des Discovery-Skripts enthält nur Namen, Pfade und Prüfgründe, nicht den Inhalt der Agent-`config.json` oder `.env`-Dateien.

## Freigegebene Compose-Projekte übernehmen

Wenn die gemeldeten `AUTO-READY`-Projekte plausibel sind:

```bash
# NUR geprüfte, neue Projekte ergänzen, bestehende Einstellungen behalten:
sudo python3 /usr/local/lib/fleet-agent/discover_compose_projects.py \
  --apply --approve-new-projects

# Agent-Konfiguration vor der Aktivierung validieren:
sudo /usr/local/lib/fleet-agent/fleet_agent.py \
  --config /etc/fleet-agent/config.json --check

# Nur bei fehlerfreier Validierung und ohne laufende Wartungsjobs:
sudo systemctl restart fleet-agent
sudo systemctl status fleet-agent --no-pager
```

`--approve-new-projects` bestätigt, dass bei bereits aktivierter Aktion `compose_update` zusätzlich entdeckte Projekte künftig manuell aktualisiert werden können. Ohne diesen Parameter verweigert das Skript die Änderung. Wenn keine neuen `AUTO-READY`-Projekte vorhanden sind, bleibt die Konfiguration unverändert.

Bei Änderungen erstellt das Skript eine geheime Sicherung wie `/etc/fleet-agent/config.json.bak-20261115T...` (Dateirechte 0600) und schreibt `config.json` atomar. `allowed_actions` und `standalone_containers` bleiben unverändert. Der Agent muss danach neu gestartet werden; bei aktiven Wartungsjobs nicht neu starten.

## Einzelcontainer / Standalone

Eigenständige Container müssen **nicht** einem Compose-Stack zugeordnet werden. Der bestehende Agent erkennt sie bereits über Docker. Für deren Updatefähigkeit sind die jeweiligen Agent-Berechtigungen `standalone_update` und die Positivliste `standalone_containers` entscheidend. Diese Konfiguration nicht pauschal auf `*` setzen, wenn du nicht wirklich alle Container zur manuellen Wartung freigeben möchtest.

## Home Assistant

Die vorhandene Fleet-Guard-Integration erzeugt Update-Entitäten für erkannte Compose-Services automatisch, **sofern** der Agent im Status die jeweilige `compose_updates`-Information liefert und `compose_update` erlaubt ist. Nach dem Agent-Neustart ggf. den Fleet-Guard-`Check updates`-Button verwenden (eine neue Registry-Prüfung ist asynchron) und die Integration neu laden.

Wichtig: Automatisches **Entdecken** ist nicht dasselbe wie automatische **Ausführung**. Keine Container werden durch das Discovery-Skript aktualisiert.

## Grenzen und weitere Entwicklung

- Das Skript ist eine einmalig oder manuell wiederholbare **Discovery-/Konfigurations-Erweiterung**; eine dauerhaft integrierte Inventarisierung im Agenten samt sichere automatische Synchronisierung kommt mit einer späteren Agent-Version.
- Portainer-/Dockhand-Verzeichnisse können automatisch gefunden und auf den Host umgerechnet werden, bleiben aber `REVIEW`, weil zusätzlich `stack.env`, andere ENV-Quellen, Profile und relative Pfade die produktive Ausführung verändern können.
- Compose arbeitet mit mehreren `-f`-Dateien und `--project-directory`. Auch wenn Dateipfade existieren, kann die heutige Datei von der ursprünglich gestarteten Konfiguration abweichen. Deshalb prüfen wir Images und Bind-Mounts vor der Übernahme.
- Docker liefert ohne passende Labels keine verlässlichen Compose-Quellen für per `docker run` gestartete Container.
- Keine automatische Installation, kein periodischer Task und kein Self-Update des Agenten sind in dieser Zwischenlösung aktiviert.
- Auf Synology den Discovery-Baustein **zunächst nicht mit `--apply` ausführen**: Die Agent-Konfiguration hat Container-interne Pfade wie `/host-volume1`, die nicht den Host-Pfaden entsprechen. Das erfordert eine eigene Pfadvalidierung und Release-Version.
- Für eine Agent-Aktualisierung müssen wir die **tatsächlich laufende Debian-Version** vergleichen; das bisherige GitHub-Repository enthält noch keine geprüfte installierbare Linux-Agent-Version.

## Rückweg

Die vor dem Schreiben gesicherte `config.json.bak-...` kann bei Bedarf mit 0600-Rechten wieder nach `/etc/fleet-agent/config.json` kopiert werden; danach Agent-Konfigurationsprüfung und Dienstneustart. Kein Container wird vom Discovery-Skript angefasst.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
