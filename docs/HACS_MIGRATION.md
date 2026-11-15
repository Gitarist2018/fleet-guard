# Wechsel einer manuellen Fleet-Guard-Installation zu HACS

Stand: 2026-11-15. Die in GitHub importierte Home-Assistant-Integration hat **Version 0.3.0** und entspricht den geprüften lokalen Quelldateien. HACS installiert nur die Dateien unter `custom_components/fleet_guard/`; es installiert **nicht** die optionalen `homeassistant/packages/`-YAML-Dateien.

## Vorbereitung – nichts löschen

1. Prüfe, ob unter **Einstellungen → Geräte & Dienste → Fleet Guard** alle Host-Einträge erreichbar sind (Synology, Debian, Proxmox).
2. Erstelle ein **vollständiges Home-Assistant-Backup**.
3. Behalte das bereits erzeugte Archiv `fleet_guard_ha.tar.gz` als separate Datei, etwa auf dem Mac. Es enthält ausschließlich die Integration, nicht die in `.storage/` gespeicherten Host-Konfigurationseinträge.
4. **Keine Fleet-Guard-Einträge unter Geräte & Dienste entfernen.** Auch die Python-Dateien vorerst nicht manuell löschen.

## HACS-Repository hinzufügen

1. Öffne **HACS** in Home Assistant.
2. Oben rechts auf `⋮` → **Benutzerdefinierte Repositories / Custom repositories**.
3. URL: `https://github.com/Gitarist2018/fleet-guard`, Kategorie **Integration**.
4. Repository hinzufügen und `Fleet Guard` in HACS öffnen.
5. **Download / Herunterladen** wählen. HACS verwaltet danach den Ordner `/config/custom_components/fleet_guard/`.

Wenn das Repository **privat** ist und HACS den Zugriff verweigert, nicht ohne Abwägung öffentlich machen. Zunächst GitHub-Berechtigungen der HACS-Integration kontrollieren oder auf eine geeignete authentifizierte Downloadmethode ausweichen.

Wenn HACS eine bereits vorhandene manuelle Installation meldet, **nicht** den Home-Assistant-Integrations-Eintrag löschen. Zuerst prüfen, welche Dateien HACS verwaltet; bei Fehlermeldungen mit Backup stoppen und den Fehler gezielt beheben.

## Neustart und Funktionstest

1. **Entwicklerwerkzeuge → YAML → Konfiguration prüfen**.
2. Home Assistant **neu starten**.
3. Unter **Einstellungen → Geräte & Dienste → Fleet Guard** prüfen, ob alle bisherigen Hosts noch existieren.
4. Unter **Entwicklerwerkzeuge → Zustände** die bisherigen `update.*`- und `sensor.*`-Entitäten prüfen. Identische Unique IDs sollen vorhandene Entitäts-IDs beibehalten, aber die tatsächliche Migration muss überprüft werden.
5. Eine **Updateprüfung** über den vorhandenen Fleet-Guard-Button auslösen. Keine Container-Installation nur zum Testen starten.

## Im Fehlerfall

Bevor Hosts oder Einträge aus Home Assistant gelöscht werden: HA-Logs auf Integrationsfehler prüfen. Für das Zurücksetzen die **vorher gesicherte Version** der Dateien nach `/config/custom_components/fleet_guard/` zurückkopieren und HA neu starten. Wenn Konfigurationseinträge betroffen sein sollten, die vollständige HA-Sicherung verwenden.

## Begrenzungen

Die HA-Integration (v0.3.0) wartet bei `update.install` auf den jeweiligen Agent-Job. **Echte Parallelität auf einem Host ist noch nicht umgesetzt** und gehört in den Linux-/Synology-Agent mit projektbezogenem Locking. Das zuvor in GitHub veröffentlichte `script.fleet_guard_container_batch_update` ist separat als HA-Package einzurichten.
