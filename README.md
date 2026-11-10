# PdfSnapOCR

**PdfSnapOCR** erstellt aus Bildschirm-Screenshots einer PDF automatisch eine neue, durchsuchbare PDF.

Das Tool ist unabhängig vom verwendeten PDF-Reader und funktioniert beispielsweise mit Adobe Acrobat Reader, Microsoft Edge, Google Chrome, Firefox oder SumatraPDF.

> **Wichtig:** PdfSnapOCR ist für selbst erstellte oder frei verfügbare PDFs gedacht. Beachte bei fremden Inhalten Urheberrecht, Lizenzbedingungen und lokale Regelungen.

## Funktionen

- Moderne dunkle GUI
- Automatische Installation der Python-Abhängigkeiten
- Freie Auswahl des PDF-Seitenbereichs auf dem Bildschirm
- Einzelseitenmodus
- Doppelseitenmodus mit automatischer Teilung in linke und rechte Seite
- Automatisches Weiterblättern
- Automatischer Stopp bei unveränderter Seite
- Automatische PDF-Erstellung aus allen Screenshots
- Optionale OCR-Textebene mit OCRmyPDF und Tesseract
- Sitzungsordner mit Zeitstempel
- Lokale Speicherung der Einstellungen

## Richtige Seitenansicht einstellen

Bevor du den Seitenbereich auswählst, stelle den PDF-Reader auf die passende Seitenansicht ein.

### Adobe Acrobat Reader

Öffne in Adobe Acrobat Reader:

```text
Ansicht → Seitenanzeige
```

Wähle dort:

- **Einzelansicht** für den Einzelseitenmodus
- **Zweiseitenansicht** für den Doppelseitenmodus
- Optional: **Bildlauf aktivieren** deaktivieren, damit jeweils eine vollständige Seite bzw. ein vollständiges Doppelseitenpaar sichtbar ist

In manchen Acrobat-Versionen heißt der Menüpunkt auch **„Seitenanzeige“** oder **„Seitenlayout“**.

### Andere PDF-Reader

Suche in deinem PDF-Reader nach einer ähnlichen Einstellung:

| Reader | Empfohlene Einstellung |
|---|---|
| Microsoft Edge | Seitenlayout: **Einzelseite** oder **Zwei Seiten** |
| Google Chrome | Seitenansicht: **Einzelseite** oder **Zwei Seiten** |
| Firefox | Seitenlayout: **Einzelseite** oder **Zwei Seiten** |
| SumatraPDF | Ansicht: **Einzel Seite** oder **Buchansicht** |
| Foxit Reader | Ansicht: **Einzelseite** oder **Doppelseite** |

Wichtig: Die Bezeichnungen können sich je nach Programmversion leicht unterscheiden.

## Doppelseitenmodus

Für den Doppelseitenmodus:

1. Stelle den PDF-Reader auf **Zweiseitenansicht** bzw. **Zwei Seiten**.
2. Stelle sicher, dass **beide Seiten vollständig sichtbar** sind.
3. Wähle in PdfSnapOCR den Bereich aus, der **beide Seiten gemeinsam** enthält.
4. Das Tool teilt den Screenshot automatisch in der horizontalen Mitte.

So sollte der Auswahlbereich aussehen:

```text
+------------+------------+
|   Seite 1  |   Seite 2  |
+------------+------------+
```

Die Ausgabereihenfolge ist:

```text
Seite 1
Seite 2
Seite 3
Seite 4
```

## Installation

1. Python 3.10 oder neuer installieren
2. Während der Installation **Add Python to PATH** aktivieren
3. Repository klonen:

```bat
git clone https://github.com/basecore/PdfSnapOCR.git
cd PdfSnapOCR
```

4. Doppelklick auf:

```bat
Start_PdfSnapOCR.bat
```

Die Startdatei erstellt automatisch eine virtuelle Umgebung und installiert:

```text
mss
Pillow
PyMuPDF
keyboard
ocrmypdf
```

## Tesseract OCR

Für die OCR-Textebene wird Tesseract benötigt.

Im Programm auf **„Tesseract prüfen / installieren“** klicken. Das Tool versucht die Installation automatisch über `winget`:

```bat
winget install --id UB-Mannheim.TesseractOCR --exact --silent
```

Falls das nicht funktioniert:

https://github.com/UB-Mannheim/tesseract/wiki

## Bedienung

1. PDF im gewünschten Reader öffnen
2. Seitenansicht auf **Einzelansicht** oder **Zweiseitenansicht** stellen
3. In PdfSnapOCR den Seitenbereich auswählen
4. Erste PDF-Seite bzw. erstes Doppelseitenpaar anzeigen
5. **„Automatische Aufnahme starten“** klicken
6. Das Tool erstellt automatisch Screenshots und blättert weiter
7. Am Dokumentende stoppt es automatisch
8. PDF und optionale OCR-PDF werden erstellt

## OCR und Design

Das sichtbare Design bleibt als Screenshot-Bild erhalten. OCRmyPDF ergänzt eine unsichtbare Textebene, wodurch die PDF durchsuchbar wird und Text kopiert werden kann.

## Ausgabe

```text
Documents/PdfSnapOCR/
└─ 2026-11-10_09-30-00/
   ├─ page_0001.png
   ├─ page_0002.png
   ├─ PDF_Screenshot_2026-11-10_09-30-00_image.pdf
   └─ PDF_Screenshot_2026-11-10_09-30-00_ocr.pdf
```

## Tipps für beste Qualität

- PDF-Reader in den Vollbildmodus versetzen
- Zoomfaktor während der gesamten Aufnahme nicht ändern
- Fenster nicht verschieben
- Taskleiste, Menüs und Scrollbalken möglichst aus dem Aufnahmebereich ausschließen
- Möglichst hohe, aber noch scharfe Zoomstufe verwenden
- PNG-Screenshots werden automatisch verwendet
- Für deutsche Dokumente `deu+eng` empfehlen

## Problemlösung

| Problem | Lösung |
|---|---|
| Python wird nicht gefunden | Python installieren und **Add Python to PATH** aktivieren |
| Tkinter fehlt | Python erneut installieren und Option **tcl/tk and IDLE** aktivieren |
| Blättern funktioniert nicht | Programm als Administrator starten oder eine andere Blättertaste wählen |
| OCR wird übersprungen | Tesseract installieren und erneut prüfen |
| OCR erkennt schlecht | Zoom erhöhen, Screenshotbereich vergrößern und PDF-Reader scharf darstellen |
| Falsche Seitenreihenfolge bei Doppelseiten | Sicherstellen, dass beide Seiten vollständig und symmetrisch im Auswahlrahmen liegen |

## Datenschutz

Screenshots, OCR und PDF-Erstellung erfolgen lokal auf deinem Computer. Es werden keine Daten automatisch an einen Cloud-Dienst gesendet.

Für die OCR wird lokal Tesseract verwendet. Eine Internetverbindung ist normalerweise nur für die erstmalige Installation von Python-Paketen und Tesseract erforderlich.

## Lizenz

MIT License
