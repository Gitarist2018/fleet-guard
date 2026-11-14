# Fleet Guard – Sammelupdates in Home Assistant

Das Home-Assistant-Paket `homeassistant/packages/fleet_guard_updates.yaml` enthält das Skript **Fleet Guard: ausgewählte Docker-Container aktualisieren** (`script.fleet_guard_container_batch_update`).

## Einrichtung

1. Öffne die Paketdatei in GitHub und ersetze den Inhalt der bereits eingerichteten Datei `/config/packages/fleet_guard_updates.yaml` durch die neue Version.
2. Stelle sicher, dass in `/config/configuration.yaml` die Pakete eingebunden sind: `homeassistant: packages: !include_dir_named packages` (mit korrekter YAML-Einrückung).
3. Home Assistant: Entwicklerwerkzeuge > YAML > Konfiguration prüfen. Danach Home Assistant neu starten.
4. Öffne Einstellungen > Automatisierungen & Szenen > Skripte > **Fleet Guard: ausgewählte Docker-Container aktualisieren**.
5. Drei-Punkte-Menü > **Skript ausführen**. Wähle mehrere Docker-Update-Entitäten (zuerst möglichst nur zwei unkritische), aktiviere das Kontrollfeld **Updates jetzt installieren** und starte das Skript. Das ist die einzige ausdrückliche Bestätigung für alle ausgewählten Updates.
6. Unter Entwicklerwerkzeuge > Zustände und Fleet-Guard-Jobstatus prüfen, ob die einzelnen Updates durchgeführt wurden und ob die Anwendungen erreichbar sind.

## Schutzmechanismen

- Kein Update läuft automatisch; ausschließlich ein manueller Skriptaufruf.
- Zugelassen werden nur Update-Entitäten, die von der Integration `fleet_guard` stammen, mit `update.` beginnen, auf `_image` enden und aktuell den Zustand `on` haben.
- Bei fehlender Bestätigung, leerer Auswahl, Doppelung oder ungültigen Entitäten wird der gesamte Auftrag vor Ausführung abgebrochen.
- Die Berechtigung des Agents (`allowed_actions`), sein Compose-Projekt-Allowlisting und alle übrigen Host-Sicherheitsregeln gelten unverändert. Ein Home-Assistant-Skript umgeht sie nicht.
- Ein Aufruf von `update.install` mit mehreren Entitäten verteilt Updateanfragen; er **garantiert keine gleichzeitige Ausführung** auf einem Host. Fleet-Guard-Agenten mit nur einem Job-Worker verarbeiten die Aktionen nacheinander. Für echte hostinterne Parallelität braucht der Agent eine getrennte, projektbezogene Job- und Lock-Verwaltung.
- Datenbank-Container, abhängige Services und produktive Anwendungen nach gesondertem Backup und in geplanter Reihenfolge aktualisieren. Nach einem erfolgreichen Job noch Gesundheit der Anwendung und die nächste Updateprüfung abwarten.

## Nächster Schritt

Für echtes paralleles Aktualisieren unterschiedlicher Compose-Projekte und eine vollwertige Mehrfachauswahl direkt in einer Dashboard-Karte die tatsächlich installierten Agent-/Integrationsquellen importieren, Locking pro Host/Compose-Projekt und maximale Workerzahl ergänzen, anschließende Healthchecks testen und versioniert veröffentlichen. Keine ungetestete parallele Compose-Ausführung in derselben Projektgruppe.
