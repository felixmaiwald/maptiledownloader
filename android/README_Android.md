# Map Tile Viewer (Android)

Android-App zum Anzeigen von Map-Tiles (OpenStreetMap, Google, Bing) mit Suche,
Messlinie und PNG-Export. Geschrieben in Kotlin mit OsmDroid und Material Design 3.

---

## Features

- **Interaktive Karte** – Pan, Pinch-Zoom und Fling via OsmDroid
- **6 Kartenquellen** – wählbar per Chip in der oberen Leiste:
  - OpenStreetMap (MAPNIK)
  - Google Straße / Satellit / Hybrid
  - Bing Straße / Satellit
- **Ortssuche** – Freitextsuche via Nominatim (z. B. „Marienplatz München")
- **Messlinie** – Luftlinie zwischen beliebig vielen Punkten (Haversine-Distanz)
- **Mein Standort** – GPS-Overlay mit Folgen-Funktion
- **PNG-Export** – aktueller Kartenviewport als Bilddatei speichern
- **Maßstabsbalken** – automatisch skaliert
- **Kompass** – drehbarer Kompass-Overlay
- **Disk-Cache** – Kacheln automatisch lokal gecacht (OsmDroid intern)

---

## Voraussetzungen

| Tool | Version |
|---|---|
| Android Studio | Flamingo 2022.2.1 oder neuer |
| JDK | 17 (über Android Studio enthalten) |
| Android SDK | API 34 (compileSdk) |
| Mindest-Android | API 24 (Android 7.0 Nougat) |

---

## Projekt öffnen

1. ZIP-Archiv entpacken
2. Android Studio starten
3. **File → Open** → Ordner `MapTileViewer_Android` auswählen
4. Gradle-Sync abwarten (~1–2 Minuten)
5. Gerät oder Emulator (API 24+) auswählen → **Run ▶**

---

## APK bauen

### Debug-APK (für Tests)

```bash
# Im Projekt-Root-Ordner:
./gradlew assembleDebug

# Ergebnis:
app/build/outputs/apk/debug/app-debug.apk
```

### Release-APK (signiert)

Android Studio:
**Build → Generate Signed App Bundle / APK → APK**
→ Keystore anlegen oder vorhandenen wählen → Fertig

### Auf Gerät installieren (ohne Play Store)

```bash
# Via ADB (USB-Debugging aktiviert):
adb install app/build/outputs/apk/debug/app-debug.apk
```

Oder APK-Datei direkt auf das Gerät kopieren und öffnen
(Einstellungen → Sicherheit → **Unbekannte Quellen** erlauben).

---

## Bedienung

### Karte navigieren

| Geste | Funktion |
|---|---|
| Ein Finger ziehen | Karte verschieben |
| Zwei Finger spreizen / zusammen | Zoom + / – |
| Doppeltippen | Hineinzoomen |
| Zwei-Finger-Doppeltippen | Herauszoomen |

### Kartenquelle wechseln

Horizontal scrollbare Chips oben in der App antippen.
Der aktive Chip wird hervorgehoben.

### Ort suchen

1. Suchbegriff in das Textfeld eingeben
2. „Suchen" tippen oder Tastatur-Aktion „Suchen" auslösen
3. Karte springt zum ersten Nominatim-Treffer, Zoom 14

### Messlinie

1. **📏 Messen** aktivieren → Cursor wechselt
2. Punkte auf die Karte tippen (werden als A, B, C, … markiert)
3. Jedes Segment zeigt seine Länge, unten steht die Gesamtstrecke:
   `∑ 14.231 km  (4 Punkte)`

| Button | Funktion |
|---|---|
| **↩ Undo** | Letzten Punkt entfernen |
| **🗑 Löschen** | Alle Punkte löschen, Messmodus beenden |
| **📏 Messen** (nochmals) | Messmodus beenden (Punkte bleiben) |

### Standort

FAB (📍) → fordert GPS-Berechtigung an → zentriert Karte auf aktuellen Standort
und folgt der Bewegung.

### PNG-Export

FAB (💾) → aktueller Kartenausschnitt wird als PNG gespeichert:

- **Android 10+**: `Bilder/MapTileViewer/karte_<timestamp>.png` (MediaStore, keine Berechtigung nötig)
- **Android ≤ 9**: `Pictures/MapTileViewer/` (benötigt WRITE_EXTERNAL_STORAGE)

---

## Projektstruktur

```
MapTileViewer_Android/
├── app/
│   ├── build.gradle                        ← Abhängigkeiten & Build-Konfig
│   └── src/main/
│       ├── AndroidManifest.xml             ← Berechtigungen & Activity-Deklaration
│       ├── java/com/maptileviewer/
│       │   ├── MainActivity.kt             ← Haupt-Activity, UI-Koordination
│       │   ├── TileSources.kt              ← Kachel-Quellen (OSM, Google, Bing)
│       │   ├── MeasureOverlay.kt           ← Messwerkzeug (Canvas + Haversine)
│       │   ├── GeocodingService.kt         ← Nominatim-Suche (OkHttp + Coroutines)
│       │   └── ExportHelper.kt             ← PNG-Export (MediaStore / File)
│       └── res/
│           ├── layout/activity_main.xml    ← UI-Layout (ConstraintLayout)
│           ├── values/strings.xml
│           ├── values/colors.xml
│           ├── values/themes.xml           ← Material3 Dark Theme
│           └── drawable/bg_search_field.xml
├── build.gradle
├── settings.gradle
└── gradle.properties
```

---

## Abhängigkeiten

```gradle
// OsmDroid: Karten-Rendering, Tile-Cache, Gesten
implementation 'org.osmdroid:osmdroid-android:6.1.18'

// OkHttp: HTTP für Geocoding
implementation 'com.squareup.okhttp3:okhttp:4.12.0'

// Kotlin Coroutines: Hintergrundoperationen
implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'

// Material Design 3
implementation 'com.google.android.material:material:1.11.0'
```

---

## Berechtigungen

| Berechtigung | Zweck |
|---|---|
| `INTERNET` | Kachel-Downloads, Geocoding |
| `ACCESS_NETWORK_STATE` | Netzwerkstatus prüfen |
| `ACCESS_FINE_LOCATION` | GPS für „Mein Standort" |
| `ACCESS_COARSE_LOCATION` | Netz-Standort als Fallback |
| `WRITE_EXTERNAL_STORAGE` | PNG-Export auf Android ≤ 9 |

---

## Distanzmessung (Haversine-Formel)

```
a = sin²(Δlat/2) + cos(lat₁) · cos(lat₂) · sin²(Δlon/2)
d = 2 · R · arcsin(√a)     (R = 6 371 000 m)
```

Fehler < 0,5 % (vernachlässigt Erdabplattung). Ausreichend für
Messungen bis ~2 000 km.

---

## Lizenzhinweise

| Anbieter | Bedingung |
|---|---|
| OpenStreetMap | ODbL – Attribution Pflicht |
| Google Maps | Google Terms of Service |
| Bing Maps | Microsoft Terms of Service |

Die Kachel-URLs von Google und Bing sind für den **persönlichen /
edukativen Gebrauch** nutzbar. Für kommerzielle Anwendungen bitte
die offiziellen SDK/API-Produkte (Maps SDK for Android, Bing Maps SDK)
verwenden.

---

## Roadmap

- [ ] BBox-Export: zusammengesetztes PNG aus beliebigem Bereich (Tile-Stitching)
- [ ] GPX-Track-Import und Anzeige
- [ ] GeoJSON-Overlay
- [ ] Lesezeichen / Favoriten
- [ ] Mini-Map (Übersichtsfenster)
- [ ] Offline-Cache-Pakete (.mbtiles)
- [ ] GitHub Actions CI (automatische APK-Builds)

---

*Map Tile Viewer Android v1.0 · Kotlin / OsmDroid · MIT License*
