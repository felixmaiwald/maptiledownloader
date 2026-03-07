# Map Tile Viewer – Android

Eine Android-App zum Anzeigen und Vergleichen verschiedener Kartendienste.
Unterstuetzt GPS-Lokalisierung, Streckenmessung, Ortssuche und Karten-Export.

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

- **10 Kartenanbieter** – Google (Strasse/Satellit/Hybrid), CartoDB, Stadia Dunkel,
  OpenTopoMap, Esri, Bing
- **GPS-Lokalisierung** – Follow-Modus, Genauigkeitsanzeige, Geschwindigkeit
- **Streckenmessung** – Punkte setzen, Distanz berechnen, Undo/Reset
- **Ortssuche** – Nominatim-Geocoding (OpenStreetMap)
- **PNG-Export** – aktuellen Kartenausschnitt als Bild speichern

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
2. Android Studio starten: **File -> Open** -> Ordner `MapTileViewer_Android`
3. Gradle-Sync abwarten (~2 Min.)
4. **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**

APK-Pfad:
```
app/build/outputs/apk/debug/app-debug.apk
```

Auf Geraet installieren: **Run -> Run 'app'** (USB-Debugging am Handy aktivieren)

---

### Methode 2 – Kommandozeile

#### Schritt 1 – gradle-wrapper.jar herunterladen (einmalig)

ZIP entpacken und in den Projektordner wechseln:

```bash
rm -rf ~/Downloads/MapTileViewer_Android
cd ~/Downloads && unzip MapTileViewer_Android.zip
cd MapTileViewer_Android
```

Die `gradle-wrapper.jar` kann nicht im ZIP enthalten sein und muss einmalig
heruntergeladen werden:

```bash
cd MapTileViewer_Android
mkdir -p gradle/wrapper

curl -Lo gradle/wrapper/gradle-wrapper.jar \
  "https://services.gradle.org/versions/wrapper/gradle-wrapper.jar"
```

**Fuer spaetere Projekte** einmalig speichern:

```bash
mkdir -p ~/.gradle-wrapper
cp gradle/wrapper/gradle-wrapper.jar ~/.gradle-wrapper/
# Wiederverwenden:
cp ~/.gradle-wrapper/gradle-wrapper.jar gradle/wrapper/
```

#### Schritt 2 – SDK-Pfad setzen

```bash
# Linux / macOS
echo "sdk.dir=$HOME/Android/Sdk" > local.properties

# Falls SDK woanders liegt, Pfad pruefen:
find $HOME -name "adb" 2>/dev/null | head -3
```

#### Schritt 3 – Bauen

```bash
# Linux / macOS
chmod +x gradlew
./gradlew assembleDebug

# Windows
gradlew.bat assembleDebug
```

APK liegt unter:
```
app/build/outputs/apk/debug/app-debug.apk
```

#### Schritt 4 – Auf Geraet installieren (ADB)

```bash
# USB-Debugging am Geraet aktivieren:
# Einstellungen -> Ueber das Telefon -> Build-Nummer 7x tippen
# -> Entwickleroptionen -> USB-Debugging -> EIN

adb devices                                                    # Geraet pruefen
adb install app/build/outputs/apk/debug/app-debug.apk         # Installieren
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

Nach jedem `git push` -> GitHub baut die APK automatisch.
Download: **Actions -> letzter Build -> Artifacts -> app-debug**

---

### Haeufige Fehler

| Fehlermeldung | Loesung |
|---|---|
| `GradleWrapperMain not found` | `gradle-wrapper.jar` herunterladen (Schritt 1) |
| `SDK location not found` | `local.properties` mit `sdk.dir=...` anlegen |
| `Minimum Gradle version is 8.2` | `./gradlew` statt `gradle` verwenden |
| `MissingPermission Lint error` | bereits behoben: `lint { abortOnError false }` |
| `Could not find play-services` | Internetverbindung pruefen, Gradle-Sync wiederholen |

---

### Dauerhaft: ANDROID_HOME setzen

```bash
echo 'export ANDROID_HOME=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/platform-tools' >> ~/.bashrc
source ~/.bashrc
```

Danach entfaellt `local.properties` bei jedem neuen Projekt.

---

## Projektstruktur

```
MapTileViewer_Android/
├── app/
│   └── src/main/java/com/maptileviewer/
│       ├── MainActivity.kt        # Hauptaktivitaet, UI-Logik
│       ├── TileSources.kt         # Alle Kartenanbieter
│       ├── TileProxyServer.kt     # Lokaler HTTP-Proxy fuer Google Maps
│       ├── LocationManager.kt     # GPS / FusedLocationProvider
│       ├── LocationOverlay.kt     # GPS-Punkt auf der Karte
│       ├── MeasureOverlay.kt      # Streckenmessung
│       ├── GeocodingService.kt    # Nominatim-Ortssuche
│       └── ExportHelper.kt        # PNG-Export
├── gradlew                        # Gradle Wrapper (Linux/macOS)
├── gradlew.bat                    # Gradle Wrapper (Windows)
├── settings.gradle
├── build.gradle
└── KOMPILIEREN.md                 # Ausfuehrliche Kompilieranleitung
```

---

## Kartendienste

| Anbieter | Typ | Besonderheit |
|---|---|---|
| Google Strasse | Strassenkarte | via lokalem Proxy (Referer-Header) |
| Google Satellit | Luftbild | via lokalem Proxy |
| Google Hybrid | Satellit + Beschriftung | via lokalem Proxy |
| CartoDB | Hell, OSM-Daten | direkt, kein API-Key |
| Esri Dunkel | Dunkles Grau-Design | ArcGIS Canvas, kostenlos |
| OpenTopoMap | Wanderkarte | Hoehenlinien, max. Zoom 17 |
| Esri Strasse | ArcGIS Basemap | direkt, kostenlos |
| Esri Satellit | ArcGIS Imagery | direkt, kostenlos |
| Bing Strasse | Bing Maps | Quadkey-Format |
| Bing Satellit | Bing Luftbild | Quadkey-Format |

---

*Map Tile Viewer Android v1.0 - Stand Maerz 2026*
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
| `locationFlow(accuracy, interval)` | Liefert einen Kotlin-Flow mit kontinuierlichen GPS-Updates via FusedLocationProviderClient. Accuracy und Intervall sind konfigurierbar. |
| `onLocationResult(result)` | Callback des FusedLocationProvider – wandelt das Ergebnis in ein `LocationUpdate`-Objekt um und gibt es in den Flow. |
| `onLocationAvailability(avail)` | Wird aufgerufen wenn GPS-Verfügbarkeit sich ändert (z.B. kein Signal in Gebäuden). Sendet `LocationUpdate.Unavailable`. |
| `formatAccuracy(accuracyM)` | Formatiert den Genauigkeitswert in lesbaren Text (z.B. `"±5 m"`, `"±1.2 km"`). |

---

### LocationOverlay.kt

| Funktion | Beschreibung |
|---|---|
| `draw(canvas, mapView, shadow)` | Zeichnet den GPS-Punkt (blauer Kreis) und den Genauigkeitsradius (halbtransparenter Ring) auf den Karten-Canvas. |
| `updateLocation(geoPoint, accuracy)` | Aktualisiert Position und Genauigkeitsradius und triggert ein Neuzeichnen der Karte. |
| `hasLocation()` | Gibt `true` zurück wenn bereits eine GPS-Position vorliegt. |
| `getPosition()` | Gibt den letzten bekannten `GeoPoint` zurück oder `null`. |

---

### MainActivity.kt

| Funktion | Beschreibung |
|---|---|
| `onCreate(savedInstanceState)` | Einstiegspunkt der Activity. Initialisiert osmdroid-Config, ViewBinding, ruft alle `setup*()`-Methoden auf. |
| `onResume()` | Setzt Karten-Rendering fort und startet GPS-Updates neu (Android Lifecycle). |
| `onPause()` | Pausiert Karte und stoppt GPS-Updates um Akku zu schonen (Android Lifecycle). |
| `setupMap()` | Konfiguriert die osmdroid-MapView: Startzoom, Startposition (München), ScaleBar, Zoom-Controller, MapListener. |
| `onScroll(event)` | MapListener-Callback bei Karten-Scrolling – aktualisiert Zoom-Level-Anzeige. |
| `onZoom(event)` | MapListener-Callback bei Zoom-Geste – aktualisiert Zoom-Level-Anzeige mit `event.zoomLevel`. |
| `setupProviderChips()` | Erstellt die Chip-Buttons für alle Kartenanbieter aus `TileSources.ALL` dynamisch zur Laufzeit. |
| `switchProvider(source, chip)` | Wechselt den aktiven Tile-Source, markiert den gewählten Chip und leert den Kachel-Cache. |
| `setupMeasureTool()` | Bindet `MeasureOverlay` an die Karte und verkabelt die Mess-Buttons (Start/Stop/Undo/Reset). |
| `setupSearch()` | Bindet das Suchfeld an `GeocodingService` und behandelt Enter-Taste sowie den Such-Button. |
| `performSearch()` | Führt die Geocoding-Suche im IO-Scope aus und animiert die Karte zum Ergebnis-GeoPoint. |
| `setupLocationButton()` | Initialisiert den GPS-Button und verknüpft ihn mit `toggleFollowMode()`. |
| `toggleFollowMode()` | Schaltet den GPS-Follow-Modus ein/aus. Im Follow-Modus folgt die Karte automatisch der Position. |
| `startLocationUpdates()` | Startet den `locationFlow` als Coroutine und verarbeitet `LocationUpdate`-Events. |
| `stopLocationUpdates()` | Cancelt die GPS-Coroutine und entfernt den `LocationOverlay` von der Karte. |
| `onLocationUpdate(update)` | Verarbeitet ein erfolgreiches GPS-Update: aktualisiert Overlay, GPS-Info-TextView, Follow-Modus. |
| `onLocationUnavailable()` | Behandelt GPS-Ausfall: setzt Follow-Modus zurück, zeigt Hinweis im GPS-Info-Feld. |
| `showPermissionRationale()` | Zeigt einen Dialog der erklärt warum die App GPS-Berechtigung benötigt. |
| `showLocationInfoDialog()` | Zeigt einen Dialog mit Details zur aktuellen GPS-Position (Koordinaten, Höhe, Geschwindigkeit). |
| `requestLocationPermission()` | Startet den Android-Berechtigungsdialog für `ACCESS_FINE_LOCATION`. |
| `setupExportButton()` | Bindet den Export-Button an `ExportHelper.exportMapToPng()` und zeigt Erfolg/Fehler per Toast. |
| `updateZoomLevel(zoom)` | Aktualisiert das `tvZoomLevel`-TextView oben rechts mit dem aktuellen Zoom-Level als Integer. |
| `hideKeyboard()` | Versteckt die Soft-Tastatur nach Suchbestätigung via `InputMethodManager`. |

---

### MeasureOverlay.kt

| Funktion | Beschreibung |
|---|---|
| `draw(canvas, mapView, shadow)` | Zeichnet alle Messpunkte (Kreise), Verbindungslinien und Distanz-Labels auf den Canvas. |
| `drawLabelWithBg(canvas, text, x, y, paint)` | Hilfsfunktion: zeichnet Text mit weißem abgerundetem Hintergrund für bessere Lesbarkeit. |
| `onSingleTapConfirmed(e, mapView)` | Tap-Handler: wandelt Bildschirmkoordinaten in `GeoPoint` um und fügt ihn zur Messpunkteliste hinzu. |
| `undo()` | Entfernt den zuletzt gesetzten Messpunkt und aktualisiert die Distanzanzeige. |
| `clear()` | Löscht alle Messpunkte und setzt die Overlay-Anzeige zurück. |
| `totalDistance()` | Berechnet die Gesamtdistanz aller Messpunkte via `haversine()`. Gibt Meter als `Double` zurück. |
| `haversine(a, b)` | Berechnet den Großkreisabstand zwischen zwei `GeoPoint`s in Metern (Haversine-Formel). |
| `formatDistance(meters)` | Gibt Distanz als lesbaren String aus: unter 1000 m → `"123 m"`, darüber → `"1.23 km"`. |

---

### TileProxyServer.kt

| Funktion | Beschreibung |
|---|---|
| `start(scope)` | Startet einen lokalen TCP-Server auf Port 8765 im angegebenen CoroutineScope. Lauscht auf Verbindungen von osmdroid. |
| `handle(socket)` | Verarbeitet eine einzelne HTTP-Anfrage: liest den Pfad, leitet ihn an `resolve()` weiter, setzt Referer-Header und gibt die Google-Kachel zurück. |
| `resolve(path)` | Wandelt einen lokalen Proxy-Pfad (z.B. `/google/street/{z}/{x}/{y}`) in die echte Google-Maps-URL mit korrekten Headern um. |

---

### TileSources.kt

| Funktion / Klasse | Beschreibung |
|---|---|
| `getTileURLString(pMapTileIndex)` (Google) | Baut die Proxy-URL für Google Street/Satellit/Hybrid. Leitet über `TileProxyServer` um Referer-Header zu setzen. |
| `getTileURLString(pMapTileIndex)` (Esri Dunkel) | Berechnet z/y/x aus dem osmdroid-Index und baut die ArcGIS-Canvas-URL für das dunkle Design. |
| `getTileURLString(pMapTileIndex)` (Bing) | Konvertiert z/x/y in das Bing-spezifische Quadkey-Format (Base-4-String). |
| `toQuadKey(pMapTileIndex)` | Hilfsfunktion: wandelt osmdroid-Tile-Index in den Bing Quadkey-String um (bitweise Berechnung pro Zoomstufe). |

---

*Map Tile Viewer Android v1.0 - Stand März 2026*
