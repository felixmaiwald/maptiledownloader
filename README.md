# Map Tile Viewer

Ein interaktiver Kartenbetrachter für den Desktop, geschrieben in Python mit tkinter.
Unterstützt OpenStreetMap, Google Maps und Bing Maps als Kachelquellen.

## Features

- **Interaktive Karte** – Verschieben per Maus, Zoomen per Mausrad oder Tastatur
- **6 Kartenanbieter** – OpenStreetMap, Google Straße/Satellit/Hybrid, Bing Straße/Satellit
- **Ortssuche** – Freitextsuche via Nominatim (z. B. „Marienplatz München")
- **Koordinatenanzeige** – Echtzeit-Anzeige von Lat/Lon unter dem Mauszeiger
- **Maßstabsbalken** – automatisch skaliert (m / km, breitengradkorrigiert)
- **Messlinie** – Luftlinie zwischen beliebig vielen Punkten mit Gummiband-Vorschau
- **PNG-Export** – zwei Methoden:
  - Bereich im Fenster aufziehen (Drag-Auswahl)
  - Beliebigen Bereich per Koordinaten eingeben (größer als das Sichtfenster)
- **LRU-RAM-Cache** – begrenzt den Speicherverbrauch (Standard: 300 Kacheln ≈ 75 MB)
- **Disk-Cache** – geladene Kacheln lokal gespeichert, kein erneuter Download
- **Fortschrittsdialog** – beim Export mit Abbrechen-Funktion
- **Strip-Processing** – Export großer Bereiche ohne exzessiven RAM-Verbrauch

---

## Installation

### Voraussetzungen

- Python 3.10 oder neuer
- `requests`
- `Pillow`
- `tkinter` (in Python standardmäßig enthalten)

### Abhängigkeiten installieren

```bash
pip install requests Pillow
```

**Debian / Ubuntu** (falls `ImageTk` fehlt):

```bash
sudo apt install python3-pil.imagetk python3-tk
pip install requests
```

**Empfohlen: Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
pip install requests Pillow
```

---

## Starten

```bash
python map_tile_viewer.py
```

Die Karte öffnet bei **München (48.1374°N, 11.5755°E)** auf Zoomstufe 12.

---

## Bedienung

### Navigation

| Aktion | Eingabe |
|---|---|
| Karte verschieben | Linke Maustaste halten + ziehen |
| Hineinzoomen | Mausrad ↑ · Taste `+` · Button `＋` |
| Herauszoomen | Mausrad ↓ · Taste `-` · Button `－` |
| Zoom direkt wählen | Zoom-Slider in der Toolbar |
| Ort suchen | Suchfeld + `Enter` oder Button „Suchen" |
| Auswahl aufheben | `Esc` |

### Kartenanbieter wechseln

Die Anbieter-Buttons in der oberen Toolbar wechseln sofort die Kachelquelle.
Der aktive Anbieter wird farbig hervorgehoben.

### Messlinie

1. Button **„Linie messen"** klicken → Cursor wird zum Kreuz
2. Beliebig viele Punkte per Klick setzen (Labels: A, B, C, …)
3. Gummiband-Linie zeigt live die Distanz zum nächsten Punkt
4. Gesamtstrecke erscheint in der Toolbar: `∑ 14.231 km  (4 Punkte)`

| Aktion | Eingabe |
|---|---|
| Punkt setzen | Linksklick |
| Letzten Punkt entfernen | Button „Undo" |
| Alle Punkte löschen | Button „Löschen" oder `Esc` |
| Messmodus beenden | Nochmals „Linie messen" klicken |

Messpunkte bleiben beim Zoomen und Verschieben korrekt, da sie als geografische
Koordinaten (lat/lon) gespeichert werden.

### PNG-Export

**Methode 1 – Drag-Auswahl (sichtbarer Bereich):**

1. Button **„Bereich aufziehen"** klicken
2. Rechteck auf der Karte aufziehen
3. Info-Leiste zeigt: Kachelanzahl, Bildgröße, Ausdehnung in km
4. **„Auswahl als PNG speichern"** → Datei-Dialog → Export startet

**Methode 2 – Koordinaten (beliebige Größe):**

1. Button **„Beliebigen Bereich exportieren..."** klicken
2. Koordinaten eingeben (Nord / Süd / West / Ost in Dezimalgrad)
   - oder: „Aktuelle Ansicht übernehmen" / „Ort suchen"
3. Export-Zoom (8–20) und Anbieter wählen
4. Live-Vorschau: Kacheln, Pixel, km, geschätzte Dateigröße
5. **„Als PNG exportieren"** → Fortschrittsdialog mit Abbrechen-Option

---

## Konfiguration

Am Anfang der Datei `map_tile_viewer.py` können folgende Konstanten angepasst werden:

```python
# RAM-Cache: Anzahl Kacheln im Speicher (je ~256 KB)
MAX_TILE_CACHE = 300     # 300 ≈ 75 MB  |  100 ≈ 25 MB  |  500 ≈ 125 MB

# Startposition
DEFAULT_LAT  = 48.1374   # Breitengrad
DEFAULT_LON  = 11.5755   # Längengrad
DEFAULT_ZOOM = 12        # Zoomstufe (2–20)
```

### Eigenen Kartenanbieter hinzufügen

```python
PROVIDERS["OpenTopoMap"] = {
    "url":     "https://tile.opentopomap.org/{z}/{x}/{y}.png",
    "max_z":   17,
    "headers": {"User-Agent": "MapTileViewer/5.0"},
    "attr":    "© OpenTopoMap contributors",
}
```

---

## Disk-Cache

Kacheln werden unter `tile_cache/` gespeichert:

```
tile_cache/
├── OpenStreetMap/
│   └── 12/
│       ├── 2192_1422.png
│       └── 2193_1422.png
├── Google_Satellit/
│   └── 14/ ...
└── Bing_Strasse/
    └── ...
```

- Kacheln werden **nie automatisch gelöscht**
- Manuell leeren: Button **„Cache leeren"** in der Toolbar

---

## Technische Details

### Koordinatensystem

Web-Mercator-Schema (EPSG:3857) mit XYZ-Tile-Format:

```
n      = 2^zoom
tile_x = int((lon + 180) / 360 * n)
tile_y = int((1 - asinh(tan(lat_rad)) / π) / 2 * n)
```

Bing Maps verwendet zusätzlich das **Quadkey-Format** (x/y-Bits verschränkt, Basis-4-String).

### Threading-Modell

```
Haupt-Thread (tkinter)
│
├── _render()            → fehlende Kacheln sammeln, Overlays zeichnen
├── _schedule_render()   → Debounce 16 ms (~60 fps)
│
└── Hintergrund-Threads (daemon)
    ├── _load_bg()       → Kacheln laden, PhotoImage erzeugen
    ├── _search_bg()     → Geocoding via Nominatim
    └── _export_bg()     → Strip-Processing + PNG speichern
```

Canvas-Updates laufen ausschließlich im Haupt-Thread via `after(0, ...)`.

### RAM-Cache (LRU)

`LRUTileCache` basiert auf `collections.OrderedDict`.
Jeder Zugriff verschiebt den Eintrag ans Ende (MRU).
Bei Überschreitung von `MAX_TILE_CACHE` wird der LRU-Eintrag entfernt.

```
OpenStreetMap  |  Zoom 12  |  RAM-Cache: 187/300 (47 MB)
```

### Export: Strip-Processing

Große Exportbereiche werden in horizontalen Streifen (4 Kachelzeilen = 1024 px) aufgebaut.
Jeder Streifen wird nach dem Einfügen mit `.close()` freigegeben.

| | Vorher | Nachher |
|---|---|---|
| Peak-RAM | Raster + Ausgabe | 1 Streifen + Ausgabe |
| 8192×8192 px | ~384 MB | ~195 MB |

### Distanzmessung (Haversine)

```
a = sin²(Δlat/2) + cos(lat1) · cos(lat2) · sin²(Δlon/2)
d = 2 · R · arcsin(√a)     (R = 6 371 000 m)
```

Fehler < 0,5 % (vernachlässigt Erdabplattung).

---

## Lizenzhinweise

| Anbieter | Bedingung |
|---|---|
| OpenStreetMap | ODbL – Attribution Pflicht |
| Google Maps | Google Terms of Service |
| Bing Maps | Microsoft Terms of Service |

Die Kachel-URLs von Google und Bing sind für den **persönlichen / edukativen Gebrauch**
nutzbar. Für kommerzielle Anwendungen sind die jeweiligen API-Produkte zu verwenden.

---

## Geplante Features

- GPX-Track-Import und Anzeige
- GeoJSON-Overlay
- Lesezeichen / Favoriten
- Mini-Map (Übersichtsfenster)
- Offline-Kachelpakete (.mbtiles)

---

*Map Tile Viewer v5.0 · Python / tkinter · MIT License*
