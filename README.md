# PdfSnapOCR

**PdfSnapOCR** erstellt aus Bildschirm-Screenshots einer PDF automatisch eine neue, durchsuchbare PDF.

Das Tool ist unabhängig vom verwendeten PDF-Reader und funktioniert beispielsweise mit Adobe Acrobat Reader, Microsoft Edge, Google Chrome, Firefox oder SumatraPDF.

> **Wichtig:** PdfSnapOCR ist für selbst erstellte oder frei verfügbare PDFs gedacht. Beachte bei fremden Inhalten Urheberrecht, Lizenzbedingungen und lokale Regelungen.

## Alle Dateien benötigt

Du benötigst **alle fünf Python-Dateien**. Sie müssen im **selben Ordner** liegen.

```text
PdfSnapOCR/
├─ PdfSnapOCR.py
├─ pdfsnapocr_app.py
├─ pdfsnapocr_ui.py
├─ pdfsnapocr_frames.py
└─ pdfsnapocr_core.py
```

| Datei | Aufgabe |
|---|---|
| `PdfSnapOCR.py` | Startdatei; startet die Anwendung. |
| `pdfsnapocr_app.py` | Einstellungen, Start/Stopp, automatische Aufnahme, PDF- und OCR-Erstellung. |
| `pdfsnapocr_ui.py` | Helle Benutzeroberfläche und PDF-Bereich-Auswahl. |
| `pdfsnapocr_frames.py` | Manuell verschiebbarer und vergrößerbarer PDF-Rahmen. |
| `pdfsnapocr_core.py` | Screenshots, Doppelseitentrennung, PDF-Erstellung und OCR. |

Starte ausschließlich:

```bat
python PdfSnapOCR.py
```

Die anderen Dateien werden automatisch geladen. Starte `pdfsnapocr_app.py`, `pdfsnapocr_ui.py`, `pdfsnapocr_frames.py` oder `pdfsnapocr_core.py` nicht direkt.

## Funktionen

- Helle, moderne GUI
- Automatische Installation der Python-Abhängigkeiten
- Manuell verschiebbarer und vergrößerbarer PDF-Seitenbereich
- Einzelseitenmodus
- Doppelseitenmodus mit automatischer Teilung in linke und rechte Seite
- Automatisches Weiterblättern
- Automatischer Stopp bei unveränderter Seite
- Automatische PDF-Erstellung aus allen Screenshots
- Optionale OCR-Textebene mit OCRmyPDF und Tesseract
- Sitzungsordner mit Zeitstempel
- Lokale Speicherung der Einstellungen

## Installation mit Terminal

Diese Methode ist empfohlen, wenn du Git bereits installiert hast.

1. Öffne in Windows 11 das Startmenü und suche nach **Eingabeaufforderung** oder **Terminal**.
2. Öffne die Eingabeaufforderung.
3. Gib nacheinander folgende Befehle ein:

```bat
git clone https://github.com/basecore/PdfSnapOCR.git
cd PdfSnapOCR
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade mss pillow pymupdf keyboard ocrmypdf
python PdfSnapOCR.py
```

Falls Python nicht gefunden wird, installiere zuerst Python 3.10 oder neuer von https://www.python.org/downloads/ und aktiviere bei der Installation unbedingt **Add Python to PATH**.

Falls Git nicht installiert ist, verwende stattdessen die manuelle ZIP-Installation unten.

## Manuelle Installation per ZIP

Diese Methode benötigt kein Git.

1. Öffne das Repository: https://github.com/basecore/PdfSnapOCR
2. Klicke oben auf den grünen Button **Code**.
3. Wähle **Download ZIP**.
4. Entpacke die heruntergeladene ZIP-Datei, zum Beispiel nach:

```text
Dokumente\PdfSnapOCR
```

5. Öffne den entpackten Ordner.
6. Öffne darin die Eingabeaufforderung: Klicke in die Adressleiste des Datei-Explorers, tippe `cmd` ein und drücke Enter.
7. Gib nacheinander folgende Befehle ein:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade mss pillow pymupdf keyboard ocrmypdf
python PdfSnapOCR.py
```

Wichtig: Alle fünf Python-Dateien müssen nach dem Entpacken im selben Ordner liegen. Wenn du nur `PdfSnapOCR.py` herunterlädst, startet das Programm nicht.

## Tesseract OCR

Für die OCR-Textebene wird Tesseract benötigt.

Im Programm auf **„Tesseract prüfen / installieren“** klicken. Das Tool versucht die Installation automatisch über `winget`:

```bat
winget install --id UB-Mannheim.TesseractOCR --exact --silent
```

Falls das nicht funktioniert:

https://github.com/UB-Mannheim/tesseract/wiki

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

### Andere PDF-Reader

| Reader | Empfohlene Einstellung |
|---|---|
| Microsoft Edge | Seitenlayout: **Einzelseite** oder **Zwei Seiten** |
| Google Chrome | Seitenansicht: **Einzelseite** oder **Zwei Seiten** |
| Firefox | Seitenlayout: **Einzelseite** oder **Zwei Seiten** |
| SumatraPDF | Ansicht: **Einzel Seite** oder **Buchansicht** |
| Foxit Reader | Ansicht: **Einzelseite** oder **Doppelseite** |

## Doppelseitenmodus

Für den Doppelseitenmodus:

1. Stelle den PDF-Reader auf **Zweiseitenansicht** bzw. **Zwei Seiten**.
2. Stelle sicher, dass **beide Seiten vollständig sichtbar** sind.
3. Wähle in PdfSnapOCR den Bereich aus, der **beide Seiten gemeinsam** enthält.
4. Das Tool teilt den Screenshot automatisch in der horizontalen Mitte.

```text
+------------+------------+
|   Seite 1  |   Seite 2  |
+------------+------------+
```

## Bedienung

1. PDF im gewünschten Reader öffnen
2. Seitenansicht auf **Einzelansicht** oder **Zweiseitenansicht** stellen
3. In PdfSnapOCR den Seitenbereich auswählen
4. Erste PDF-Seite bzw. erstes Doppelseitenpaar anzeigen
5. **„Automatische Aufnahme starten“** klicken
6. Das Tool erstellt automatisch Screenshots und blättert weiter
7. Am Dokumentende stoppt es automatisch
8. PDF und optionale OCR-PDF werden erstellt

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
