# File Uploader Script für Localmind
Dieses Skript ermöglicht die Synchronisierung von Dokumenten (PDF, DOCX, TXT, PPTX, XLSX) zwischen lokalen Verzeichnissen und Localmind über eine Upload API mit konfigurierbaren Ordnerzuordnungen. Es erkennt automatisch hinzugefügte, aktualisierte und gelöschte Dateien und führt die entsprechenden Operationen aus.

## Funktionen

- Vollständige Synchronisierung zwischen lokalen Verzeichnissen und Remote-Ordnern
- Automatische Erkennung von hinzugefügten, aktualisierten und gelöschten Dateien
- Tracking-Datei zur Überwachung von Dateiänderungen über Programmausführungen hinweg
- Unterstützung mehrerer Dateitypen (PDF, DOCX, TXT, PPTX, XLSX)
- Konfigurierbare Zuordnung zwischen lokalen Verzeichnissen und Remote-Ordner-IDs
- Mehrere Zuordnungsmethoden (JSON-Datei, Kommandozeilen-Parameter)
- Detaillierte Protokollierung des Synchronisationsvorgangs
- Automatische Auswahl der geeigneten Parser-Engine basierend auf dem Dateityp

## Voraussetzungen

- Python 3.6 oder höher
- Folgende Python-Pakete:
  - requests
  - typing

## Installation

1. Klonen Sie dieses Repository oder laden Sie die Datei herunter
2. Installieren Sie die erforderlichen Abhängigkeiten:

```

### Regelmäßige Synchronisierung mit Cron-Job

Verwenden Sie einen Cron-Job, um das Skript regelmäßig auszuführen und die Synchronisierung automatisch durchzuführen:

```bash
# Beispiel für einen Cron-Job, der stündlich ausgeführt wird
0 * * * * /usr/bin/python3 /pfad/zum/file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL --mapping-file /pfad/zur/zuordnungen.json >> /var/log/file_sync.log 2>&1
```

## Fehlerbehebung

### Tracking-Datei zurücksetzen

Wenn Sie die Synchronisierung komplett neu starten möchten, können Sie einfach die Tracking-Datei löschen:

```bash
rm file_tracking.json
```

### Häufige Probleme

1. **Datei-Upload schlägt fehl**: 
   - Überprüfen Sie die API-Verbindung
   - Bestätigen Sie, dass der Dateityp unterstützt wird
   - Überprüfen Sie, dass die Datei nicht zu groß ist

2. **Fehlende Datei-IDs in der Tracking-Datei**:
   - Dies kann passieren, wenn ein früherer Upload fehlgeschlagen ist
   - Löschen Sie die Tracking-Datei, um einen vollständigen Neustart zu erzwingen

3. **SSL-Zertifikat-Probleme**:
   - Verwenden Sie die Option `--verify-ssl`, wenn Sie mit einer vertrauenswürdigen Verbindung arbeiten
   - Für Testzwecke können Sie auf die SSL-Verifizierung verzichten (Standardverhalten)

## Technische Details

### Änderungserkennung

Das Skript verwendet mehrere Methoden, um Dateiänderungen zu erkennen:

1. Zuerst wird die Dateigröße und der Änderungszeitstempel überprüft
2. Wenn diese unverändert sind, wird ein MD5-Hash der Datei berechnet und mit dem gespeicherten Hash verglichen
3. Nur wenn alle drei Überprüfungen identisch sind, wird die Datei als unverändert betrachtet

### Remote API-Interaktionen

Das Skript interagiert mit der Localmind API über folgende Endpunkte:

- `POST /localmind/public-upload/file`: Hochladen neuer Dateien
- `DELETE /localmind/public-upload/files`: Löschen von Dateien nach ID
- `GET /localmind/public-upload/folders/{folder_id}/files`: Auflisten von Dateien in einem Ordnerbash
pip install requests
```

## Verwendung

Das Skript kann auf verschiedene Weise konfiguriert werden, um lokale Verzeichnisse mit Remote-Ordnern zu synchronisieren:

### 1. Verwendung einer JSON-Zuordnungsdatei

Erstellen Sie eine JSON-Datei mit Zuordnungen zwischen lokalen Pfaden und Remote-Ordner-IDs:

```json
{
    "/pfad/zu/berichte_2023": "aaa44348-f11f-4829-bafc-e68bfeaa8003",
    "/pfad/zu/rechnungen_2024": "9cf46791-dc7a-4d0c-b3ef-5a6259aa1975"
}
```

Führen Sie das Skript mit dieser Zuordnungsdatei aus:

```bash
python file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL --mapping-file zuordnungen.json --tracking-file meine_tracking_datei.json
```

### 2. Zuordnungen über Kommandozeile

Definieren Sie Zuordnungen direkt über die Kommandozeile:

```bash
python file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /daten/präsentationen b8e941e5-a3e0-43a8-8c8f-778fb92ba4bb /pfad/zu/berichte_2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /pfad/zu/rechnungen_2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### 3. Einzelne Verzeichniszuordnung

Für ein einzelnes Verzeichnis:

```bash
python file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --directory /pfad/zu/finanzberichte --folder-id aaa44348-f11f-4829-bafc-e68bfeaa8003
```

## Zusätzliche Parameter

- `--tracking-file`: Pfad zur JSON-Datei für das Tracking von Dateiänderungen (Standard: file_tracking.json)
- `--verbose`: Aktiviert ausführliche Protokollierung
- `--verify-ssl`: Überprüft SSL-Zertifikate (standardmäßig deaktiviert)

## Protokollierung und Tracking

Das Skript erstellt folgende Dateien im aktuellen Verzeichnis:
- `file_upload.log`: Enthält detaillierte Informationen über den Synchronisationsvorgang
- `file_tracking.json` (oder angegebene Tracking-Datei): Speichert Informationen über synchronisierte Dateien zur Erkennung von Änderungen

## Parser-Engines

- `ultraparse`: Wird für PDF, DOCX und PPTX verwendet
- `tika`: Wird für andere unterstützte Formate verwendet

## Fehlerbehebung

Bei Problemen überprüfen Sie:
1. Ob die API-Basis-URL und der API-Schlüssel korrekt sind
2. Ob die angegebenen lokalen Verzeichnisse existieren
3. Die Protokolldatei für detaillierte Fehlermeldungen

## Wie die Synchronisierung funktioniert

1. **Tracking-Datei**: Das Skript verwendet eine JSON-Datei, um den Zustand aller synchronisierten Dateien zu speichern
2. **Änderungserkennung**: Bei jedem Lauf werden folgende Überprüfungen durchgeführt:
   - Dateigröße
   - Änderungszeitstempel
   - MD5-Hash des Dateiinhalts
3. **Synchronisierungsprozess**:
   - **Neue Dateien**: Werden hochgeladen und zur Tracking-Datei hinzugefügt
   - **Geänderte Dateien**: Die alte Version wird gelöscht und die neue hochgeladen
   - **Gelöschte Dateien**: Werden auch aus dem Remote-Ordner gelöscht
   - **Unveränderte Dateien**: Werden übersprungen, um Bandbreite zu sparen

## Beispiele für typische Anwendungsfälle

### Synchronisierung von Jahresberichten

```bash
python file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /daten/berichte/2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /daten/berichte/2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### Synchronisierung verschiedener Dokumententypen in unterschiedliche Ordner

```bash
python file-uploader.py --base-url https://ihre-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /daten/rechnungen f8c47ef2-b0e4-4f0b-bda6-725a263b2509 \
    --mapping /daten/verträge d837154b-4513-4f67-81c3-99c4409e1d18 \
    --mapping
