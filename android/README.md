# Map Tile Viewer – Android

Eine Android-App zum Anzeigen und Vergleichen verschiedener Kartendienste.
Unterstützt GPS-Lokalisierung, Streckenmessung, Ortssuche, Karten-Export und Offline-Download.

---

## Schnellstart (Kommandozeile)

```bash
rm -rf ~/Downloads/MapTileViewer_Android
cd ~/Downloads && unzip MapTileViewer_Android.zip
cd MapTileViewer_Android
cp ~/.gradle-wrapper/gradle-wrapper.jar gradle/wrapper/
echo "sdk.dir=$HOME/Android/Sdk" > local.properties
./gradlew assembleDebug
```

APK liegt danach unter `app/build/outputs/apk/debug/app-debug.apk`.

---

## Funktionen

- **10 Kartenanbieter** – Google (Straße/Satellit/Hybrid), CartoDB, Esri Dunkel, OpenTopoMap, Esri Straße/Satellit, Bing Straße/Satellit
- **GPS-Lokalisierung** – Follow-Modus, Genauigkeitsanzeige, Geschwindigkeit
- **Zoom-Level-Anzeige** – Badge oben rechts auf der Karte, aktualisiert sich in Echtzeit
- **Streckenmessung** – Punkte setzen, Distanz berechnen, Undo/Reset
- **Ortssuche** – Nominatim-Geocoding (OpenStreetMap)
- **PNG-Export** – aktuellen Kartenausschnitt als Bild speichern
- **Offline-Download** – Kartenbereich per Finger aufziehen, Zoomstufen wählen, Kacheln cachen
- **Kontextmenü (⋮)** – Messwerkzeug, Download und Export einzeln ein-/ausblendbar

---

## Kompilieranleitung

### Voraussetzungen

| Komponente | Version | Hinweis |
|---|---|---|
| JDK | 17 | In Android Studio enthalten |
| Android SDK | API 34 | In Android Studio enthalten |
| Gradle | 8.2 | Via Wrapper im Projekt |
| Android Studio | Flamingo+ | Empfohlen |

---

### Methode 1 – Android Studio (empfohlen)

1. ZIP entpacken
2. Android Studio starten: **File → Open** → Ordner `MapTileViewer_Android`
3. Gradle-Sync abwarten (~2 Min.)
4. **Build → Build Bundle(s) / APK(s) → Build APK(s)**

APK-Pfad:
```
app/build/outputs/apk/debug/app-debug.apk
```

Auf Gerät installieren: **Run → Run 'app'** (USB-Debugging am Handy aktivieren)

---

### Methode 2 – Kommandozeile

#### Schritt 1 – gradle-wrapper.jar herunterladen (einmalig)

ZIP entpacken und in den Projektordner wechseln:

```bash
rm -rf ~/Downloads/MapTileViewer_Android
cd ~/Downloads && unzip MapTileViewer_Android.zip
cd MapTileViewer_Android
```

Die `gradle-wrapper.jar` kann nicht im ZIP enthalten sein und muss einmalig heruntergeladen werden:

```bash
cd MapTileViewer_Android
mkdir -p gradle/wrapper

curl -Lo gradle/wrapper/gradle-wrapper.jar \
  "https://services.gradle.org/versions/wrapper/gradle-wrapper.jar"
```

**Für spätere Projekte** einmalig speichern:

```bash
mkdir -p ~/.gradle-wrapper
cp gradle/wrapper/gradle-wrapper.jar ~/.gradle-wrapper/
# Wiederverwenden:
cp ~/.gradle-wrapper/gradle-wrapper.jar gradle/wrapper/
```

#### Schritt 2 – SDK-Pfad setzen

```bash
echo "sdk.dir=$HOME/Android/Sdk" > local.properties
```

#### Schritt 3 – Bauen

```bash
chmod +x gradlew
./gradlew assembleDebug

# Windows
gradlew.bat assembleDebug
```

#### Schritt 4 – Auf Gerät installieren (ADB)

```bash
adb devices
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

### Methode 3 – GitHub Actions (Cloud-Build)

Datei `.github/workflows/build.yml` anlegen:

```yaml
name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      - name: Build Debug APK
        run: |
          cd MapTileViewer_Android
          chmod +x gradlew
          ./gradlew assembleDebug
      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: app-debug
          path: MapTileViewer_Android/app/build/outputs/apk/debug/app-debug.apk
```

---

### Häufige Fehler

| Fehlermeldung | Lösung |
|---|---|
| `GradleWrapperMain not found` | `gradle-wrapper.jar` herunterladen (Schritt 1) |
| `SDK location not found` | `local.properties` mit `sdk.dir=...` anlegen |
| `Minimum Gradle version is 8.2` | `./gradlew` statt `gradle` verwenden |
| `MissingPermission Lint error` | bereits behoben: `lint { abortOnError false }` |
| `Could not find play-services` | Internetverbindung prüfen, Gradle-Sync wiederholen |
| `Conflicting import` | Doppelter Import – nur einmal pro Klasse importieren |

---

### Dauerhaft: ANDROID_HOME setzen

```bash
echo 'export ANDROID_HOME=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/platform-tools' >> ~/.bashrc
source ~/.bashrc
```

---

## Projektstruktur

```
MapTileViewer_Android/
├── app/
│   └── src/main/
│       ├── java/com/maptileviewer/
│       │   ├── MainActivity.kt          # Hauptaktivität, UI-Logik
│       │   ├── TileSources.kt           # Alle Kartenanbieter
│       │   ├── TileProxyServer.kt       # Lokaler HTTP-Proxy für Google Maps
│       │   ├── LocationManager.kt       # GPS / FusedLocationProvider
│       │   ├── LocationOverlay.kt       # GPS-Punkt auf der Karte
│       │   ├── MeasureOverlay.kt        # Streckenmessung
│       │   ├── RegionSelectOverlay.kt   # Rechteck-Auswahl für Offline-Download
│       │   ├── GeocodingService.kt      # Nominatim-Ortssuche
│       │   └── ExportHelper.kt          # PNG-Export
│       └── res/
│           ├── layout/activity_main.xml
│           ├── menu/menu_main.xml       # ⋮-Kontextmenü
│           └── drawable/ic_more_vert.xml
├── gradlew / gradlew.bat
├── settings.gradle
└── build.gradle
```

---

## Kartendienste

| Anbieter | Typ | Besonderheit |
|---|---|---|
| Google Straße | Straßenkarte | via lokalem Proxy (Referer-Header) |
| Google Satellit | Luftbild | via lokalem Proxy |
| Google Hybrid | Satellit + Beschriftung | via lokalem Proxy |
| CartoDB | Hell, OSM-Daten | direkt, kein API-Key |
| Esri Dunkel | Dunkles Grau-Design | ArcGIS Canvas, kostenlos, max. Zoom 16 |
| OpenTopoMap | Wanderkarte | Höhenlinien, max. Zoom 17 |
| Esri Straße | ArcGIS Basemap | direkt, kostenlos |
| Esri Satellit | ArcGIS Imagery | direkt, kostenlos |
| Bing Straße | Bing Maps | Quadkey-Format |
| Bing Satellit | Bing Luftbild | Quadkey-Format |

> ⚠️ Google-Kacheln können wegen Nutzungsbedingungen nicht offline gecacht werden.
> Offline-Download funktioniert mit: CartoDB, Esri, OpenTopoMap, Bing.

---

## Benutzeroberfläche

```
┌──[Suche_____________________][🔍][⋮]─┐
│  [Google][CartoDB][Esri]...           │
├───────────────────────────────────────┤
│                                       │
│   [Karte]                   [Z 14]   │  ← Zoom-Level Badge
│                                       │
│ ⬇              💾  📍               │  ← FABs: Download, Export, GPS
├───────────────────────────────────────┤
│  📏 Messen   Undo   Reset   1.23 km  │  ← Messwerkzeug-Leiste
└───────────────────────────────────────┘
```

**⋮-Menü** (oben rechts in der Toolbar):

| Eintrag | Steuert |
|---|---|
| ✓ 📏 Messwerkzeug | `bottomBar` (Mess-Leiste) |
| ✓ ⬇ Offline-Download | `fabDownloadRegion` |
| ✓ 💾 Karte speichern | `fabExport` |

---

## Offline-Download

1. **⬇-FAB** tippen → Hinweis „Bereich auf der Karte aufziehen"
2. Finger auf Karte ziehen → blauer Rahmen erscheint (`RegionSelectOverlay`)
3. Finger loslassen → Dialog mit Zoomstufen-Auswahl (Von / Bis)
4. **Herunterladen** → Fortschritts-Dialog mit ProgressBar
5. Kacheln werden in `/sdcard/osmdroid/tiles/` gespeichert und automatisch offline genutzt

**Faustregel Kachel-Anzahl:**

| Bereich | Z 10–14 | Z 10–16 |
|---|---|---|
| Stadtbezirk (~5 km²) | ~200 | ~1.500 |
| Großstadt (~200 km²) | ~1.000 | ~8.000 |
| Bundesland | ~5.000 | ~50.000 |

---

## Code-Dokumentation

### ExportHelper.kt

| Funktion | Beschreibung |
|---|---|
| `exportMapToPng(context, mapView)` | Rendert die aktuelle Kartenansicht in eine Bitmap und speichert sie als PNG in `Pictures/MapTileViewer/`. Gibt den Dateipfad zurück oder `null` bei Fehler. |

---

### GeocodingService.kt

| Funktion | Beschreibung |
|---|---|
| `search(query)` | Schickt eine Anfrage an die Nominatim-API (OpenStreetMap) und gibt den ersten Treffer als `GeoPoint` zurück. Läuft im IO-Thread (`withContext(Dispatchers.IO)`). |

---

### LocationManager.kt

| Funktion | Beschreibung |
|---|---|
| `hasPermission()` | Prüft ob `ACCESS_FINE_LOCATION` erteilt wurde. Gibt `true` zurück wenn ja. |
| `locationFlow(accuracy, interval)` | Liefert einen Kotlin-Flow mit kontinuierlichen GPS-Updates via FusedLocationProviderClient. |
| `onLocationResult(result)` | Callback des FusedLocationProvider – wandelt Ergebnis in `LocationUpdate`-Objekt um. |
| `onLocationAvailability(avail)` | Wird aufgerufen wenn GPS-Verfügbarkeit sich ändert. Sendet `LocationUpdate.Unavailable`. |
| `formatAccuracy(accuracyM)` | Formatiert Genauigkeitswert in lesbaren Text (z.B. `"±5 m"`). |

---

### LocationOverlay.kt

| Funktion | Beschreibung |
|---|---|
| `draw(canvas, mapView, shadow)` | Zeichnet GPS-Punkt (blauer Kreis) und Genauigkeitsradius auf den Canvas. |
| `updateLocation(geoPoint, accuracy)` | Aktualisiert Position und Genauigkeitsradius, triggert Neuzeichnen. |
| `hasLocation()` | Gibt `true` zurück wenn eine GPS-Position vorliegt. |
| `getPosition()` | Gibt den letzten bekannten `GeoPoint` zurück oder `null`. |

---

### MainActivity.kt

| Funktion | Beschreibung |
|---|---|
| `onCreate(savedInstanceState)` | Einstiegspunkt. Initialisiert osmdroid-Config, ViewBinding, ruft alle `setup*()`-Methoden auf. |
| `onResume()` | Setzt Karten-Rendering fort und startet GPS-Updates neu. |
| `onPause()` | Pausiert Karte und stoppt GPS-Updates zum Akkusparen. |
| `setupMap()` | Konfiguriert MapView: Startzoom, Startposition (München), ScaleBar, Zoom-Controller, MapListener. |
| `onScroll(event)` | MapListener-Callback bei Scrolling – aktualisiert Zoom-Level-Badge. |
| `onZoom(event)` | MapListener-Callback bei Zoom-Geste – aktualisiert Badge mit `event.zoomLevel`. |
| `setupProviderChips()` | Erstellt Chip-Buttons für alle Kartenanbieter aus `TileSources.ALL` dynamisch. |
| `switchProvider(source, chip)` | Wechselt aktiven Tile-Source, markiert Chip, leert Kachel-Cache. |
| `setupMeasureTool()` | Bindet `MeasureOverlay` und verkabelt Mess-Buttons (Start/Stop/Undo/Reset). |
| `setupSearch()` | Bindet Suchfeld an `GeocodingService`, behandelt Enter-Taste und Such-Button. |
| `performSearch()` | Führt Geocoding-Suche im IO-Scope aus, animiert Karte zum Ergebnis-GeoPoint. |
| `setupLocationButton()` | Initialisiert GPS-Button und verknüpft mit `toggleFollowMode()`. |
| `toggleFollowMode()` | Schaltet GPS-Follow-Modus ein/aus. |
| `startLocationUpdates()` | Startet `locationFlow` als Coroutine, verarbeitet `LocationUpdate`-Events. |
| `stopLocationUpdates()` | Cancelt GPS-Coroutine, entfernt `LocationOverlay`. |
| `onLocationUpdate(update)` | Verarbeitet GPS-Update: aktualisiert Overlay, GPS-Info-TextView, Follow-Modus. |
| `onLocationUnavailable()` | Behandelt GPS-Ausfall: setzt Follow-Modus zurück, zeigt Hinweis. |
| `showPermissionRationale()` | Zeigt Dialog der erklärt warum GPS-Berechtigung benötigt wird. |
| `showLocationInfoDialog()` | Zeigt Dialog mit GPS-Details (Koordinaten, Höhe, Geschwindigkeit). |
| `requestLocationPermission()` | Startet Android-Berechtigungsdialog für `ACCESS_FINE_LOCATION`. |
| `setupMenu()` | Bindet ⋮-Button an `PopupMenu` mit 3 checkbaren Einträgen zum Ein-/Ausblenden von Funktionen. |
| `setupDownloadButton()` | Bindet ⬇-FAB: aktiviert `RegionSelectOverlay` für Bereichsauswahl. |
| `showDownloadDialog(bbox)` | Zeigt Dialog zur Zoomstufen-Auswahl (NumberPicker Von/Bis) nach Bereichsauswahl. |
| `startTileDownload(bbox, zoomMin, zoomMax)` | Startet `CacheManager.downloadAreaAsync()` mit Fortschritts-Dialog (AlertDialog + ProgressBar). |
| `setupExportButton()` | Bindet Export-Button an `ExportHelper.exportMapToPng()`, zeigt Erfolg/Fehler per Toast. |
| `updateZoomLevel(zoom)` | Aktualisiert `tvZoomLevel`-Badge oben rechts mit aktuellem Zoom als Integer. |
| `hideKeyboard()` | Versteckt Soft-Tastatur nach Suchbestätigung via `InputMethodManager`. |

---

### MeasureOverlay.kt

| Funktion | Beschreibung |
|---|---|
| `draw(canvas, mapView, shadow)` | Zeichnet alle Messpunkte, Verbindungslinien und Distanz-Labels auf den Canvas. |
| `drawLabelWithBg(canvas, text, x, y, paint)` | Zeichnet Text mit weißem abgerundetem Hintergrund für bessere Lesbarkeit. |
| `onSingleTapConfirmed(e, mapView)` | Tap-Handler: wandelt Bildschirmkoordinaten in `GeoPoint` um, fügt Messpunkt hinzu. |
| `undo()` | Entfernt letzten Messpunkt, aktualisiert Distanzanzeige. |
| `clear()` | Löscht alle Messpunkte, setzt Overlay zurück. |
| `totalDistance()` | Berechnet Gesamtdistanz via `haversine()`. Gibt Meter als `Double` zurück. |
| `haversine(a, b)` | Berechnet Großkreisabstand zwischen zwei `GeoPoint`s in Metern. |
| `formatDistance(meters)` | Unter 1000 m → `"123 m"`, darüber → `"1.23 km"`. |

---

### RegionSelectOverlay.kt

| Funktion | Beschreibung |
|---|---|
| `onTouchEvent(e, mapView)` | Verarbeitet Finger-Drag: ACTION_DOWN setzt Startpunkt, ACTION_MOVE aktualisiert Rechteck, ACTION_UP berechnet `BoundingBox` und ruft `onRegionSelected` auf. |
| `draw(canvas, mapView, shadow)` | Zeichnet halbtransparentes blaues Rechteck mit Rahmen und Label „Bereich auswählen". |

---

### TileProxyServer.kt

| Funktion | Beschreibung |
|---|---|
| `start(scope)` | Startet lokalen TCP-Server auf Port 8765 im CoroutineScope. |
| `handle(socket)` | Verarbeitet HTTP-Anfrage: liest Pfad, leitet an `resolve()` weiter, setzt Referer-Header. |
| `resolve(path)` | Wandelt Proxy-Pfad in echte Google-Maps-URL mit korrekten Headern um. |

---

### TileSources.kt

| Funktion / Klasse | Beschreibung |
|---|---|
| `getTileURLString(pMapTileIndex)` (Google) | Baut Proxy-URL für Google Street/Satellit/Hybrid über `TileProxyServer`. |
| `getTileURLString(pMapTileIndex)` (Esri Dunkel) | Berechnet z/y/x aus osmdroid-Index, baut ArcGIS-Canvas-URL für dunkles Design. |
| `getTileURLString(pMapTileIndex)` (Bing) | Konvertiert z/x/y in Bing-Quadkey-Format. |
| `toQuadKey(pMapTileIndex)` | Wandelt osmdroid-Tile-Index in Bing-Quadkey-String um (bitweise Berechnung). |

---

*Map Tile Viewer Android v1.1 - Stand März 2026*
