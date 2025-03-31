# Erweiterter Datei-Uploader

Dieses Skript ermöglicht das Hochladen von Dokumenten (PDF, DOCX, TXT, PPTX, XLSX) aus lokalen Verzeichnissen in die Localmind API mit konfigurierbaren Ordnerzuordnungen.

## Funktionen

- Hochladen von unterstützten Dateien (PDF, DOCX, TXT, PPTX, XLSX) 
- Konfigurierbare Zuordnung zwischen lokalen Verzeichnissen und Localmind-Ordner-IDs
- Mehrere Zuordnungsmethoden (JSON-Datei, Kommandozeilen-Parameter)
- Detaillierte Protokollierung des Hochladevorgangs
- Automatische Auswahl der geeigneten Parser-Engine basierend auf dem Dateityp

## Voraussetzungen

- Python 3.6 oder höher
- Folgende Python-Pakete:
  - requests
  - typing

## Installation

1. Klonen Sie dieses Repository oder laden Sie die Datei herunter
2. Installieren Sie die erforderlichen Abhängigkeiten:

```bash
pip install requests
```

## Verwendung

Das Skript kann auf verschiedene Weise konfiguriert werden, um lokale Verzeichnisse Localmind-Ordner-IDs zuzuordnen:

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
python file_uploader.py --base-url https://meine-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL --mapping-file zuordnungen.json
```

### 2. Zuordnungen über Kommandozeile

Definieren Sie Zuordnungen direkt über die Kommandozeile:

```bash
python file_uploader.py --base-url https://meine-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /pfad/zu/berichte_2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /pfad/zu/rechnungen_2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### 3. Einzelne Verzeichniszuordnung

Für ein einzelnes Verzeichnis:

```bash
python file_uploader.py --base-url https://meine-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --directory /pfad/zu/finanzberichte --folder-id aaa44348-f11f-4829-bafc-e68bfeaa8003
```

## Zusätzliche Parameter

- `--verbose`: Aktiviert ausführliche Protokollierung
- `--verify-ssl`: Überprüft SSL-Zertifikate (standardmäßig deaktiviert)

## Protokollierung

Das Skript erstellt Protokolldateien im aktuellen Verzeichnis:
- `file_upload.log`: Enthält detaillierte Informationen über den Hochladevorgang

## Parser-Engines

- `ultraparse`: Wird für PDF, DOCX und PPTX verwendet
- `tika`: Wird für andere unterstützte Formate verwendet

## Fehlerbehebung

Bei Problemen überprüfen Sie:
1. Ob die API-Basis-URL und der API-Schlüssel korrekt sind
2. Ob die angegebenen lokalen Verzeichnisse existieren
3. Die Protokolldatei für detaillierte Fehlermeldungen

## Beispiele für typische Anwendungsfälle

### Hochladen von Jahresberichten

```bash
python file_uploader.py --base-url https://meine-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /daten/berichte/2023 aaa44348-f11f-4829-bafc-e68bfeaa8003 \
    --mapping /daten/berichte/2024 9cf46791-dc7a-4d0c-b3ef-5a6259aa1975
```

### Hochladen verschiedener Dokumententypen in unterschiedliche Ordner

```bash
python file_uploader.py --base-url https://meine-instanz.localmind.url --api-key IHR_API_SCHLÜSSEL \
    --mapping /daten/rechnungen f8c47ef2-b0e4-4f0b-bda6-725a263b2509 \
    --mapping /daten/verträge d837154b-4513-4f67-81c3-99c4409e1d18 \
    --mapping /daten/präsentationen b8e941e5-a3e0-43a8-8c8f-778fb92ba4bb
```
