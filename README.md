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
2. In PdfSnapOCR den Seitenbereich auswählen
3. Erste PDF-Seite anzeigen
4. **„Automatische Aufnahme starten“** klicken
5. Das Tool erstellt automatisch Screenshots und blättert weiter
6. Am Dokumentende stoppt es automatisch
7. PDF und optionale OCR-PDF werden erstellt

## Doppelseitenmodus

Bei zwei nebeneinander liegenden Seiten beide Seiten gemeinsam markieren. Das Tool teilt den Screenshot automatisch in der Mitte:

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

## Lizenz

MIT License
