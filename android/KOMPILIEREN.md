# Kompilieranleitung – Map Tile Viewer (Android)

Diese Anleitung beschreibt, wie du das Projekt lokal (Android Studio oder CLI)
zu einer APK baust. Optional ist ein Cloud-Build über GitHub Actions möglich.

---

## Voraussetzungen

| Komponente | Version | Hinweis |
|---|---|---|
| JDK | 17 | In Android Studio enthalten |
| Android SDK | API 34 | In Android Studio enthalten |
| Build Tools | 34.0.0 | Automatisch via Gradle |
| Gradle | 8.x | Via Wrapper im Projekt enthalten |
| Android Studio | Flamingo+ | Empfohlen, alles inklusive |

---

## Methode 1 – Android Studio (empfohlen)

### Schritt 1: Android Studio installieren

https://developer.android.com/studio → herunterladen → installieren.
Android Studio bringt JDK 17, SDK und Gradle automatisch mit.

### Schritt 2: Projekt öffnen

```
1. MapTileViewer_Android.zip entpacken
2. Android Studio starten
3. File → Open → Ordner "MapTileViewer_Android" auswählen
4. Gradle-Sync abwarten (~1–2 Minuten)
```

### Schritt 3: APK bauen

```
Build → Build Bundle(s) / APK(s) → Build APK(s)
```

APK-Pfad:

```
app/build/outputs/apk/debug/app-debug.apk
```

### Schritt 4: Auf Gerät installieren

```
Run → Run 'app'   (grüner Play-Button ▶)
```

USB-Debugging muss am Gerät aktiviert sein (Einstellungen → Entwickleroptionen).

---

## Methode 2 – Kommandozeile (kein Android Studio nötig)

### Voraussetzungen installieren

**Windows:**

```powershell
# JDK 17
winget install EclipseAdoptium.Temurin.17.JDK

# Android Command Line Tools:
# https://developer.android.com/studio#command-tools
# → Entpacken nach C:\Android\cmdline-tools\latest\

# SDK installieren
sdkmanager "platform-tools" "build-tools;34.0.0" "platforms;android-34"

# Umgebungsvariablen setzen
setx JAVA_HOME "C:\Program Files\Eclipse Adoptium\jdk-17"
setx ANDROID_HOME "C:\Android"
```

**macOS:**

```bash
brew install --cask temurin@17
brew install --cask android-commandlinetools
sdkmanager "platform-tools" "build-tools;34.0.0" "platforms;android-34"
export ANDROID_HOME=~/Library/Android/sdk
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

**Linux (Ubuntu / Debian):**

```bash
sudo apt install openjdk-17-jdk
# Android SDK → https://developer.android.com/studio#command-tools
# Entpacken, dann:
./sdkmanager "platform-tools" "build-tools;34.0.0" "platforms;android-34"
export ANDROID_HOME=~/Android/Sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### APK bauen

**Linux / macOS:**

```bash
cd MapTileViewer_Android
chmod +x gradlew
./gradlew assembleDebug
```

**Windows (PowerShell / CMD):**

```bat
cd MapTileViewer_Android
gradlew.bat assembleDebug
```

**APK liegt unter:**

```
app/build/outputs/apk/debug/app-debug.apk
```

### APK via ADB installieren

```bash
# Gerät prüfen (USB-Debugging aktiviert, Kabel verbunden)
adb devices

# Installieren
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## Methode 3 – GitHub Actions (Cloud-Build, kein lokales Setup)

Datei `.github/workflows/build.yml` im Projekt anlegen:

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

      - name: APK hochladen
        uses: actions/upload-artifact@v4
        with:
          name: app-debug
          path: MapTileViewer_Android/app/build/outputs/apk/debug/app-debug.apk
```

Nach jedem `git push` → GitHub baut die APK automatisch.
Download: **Actions** → letzter Build → **Artifacts → app-debug**.

---

## Häufige Fehler

### "SDK location not found"

Datei `local.properties` im Projekt-Root anlegen:

```properties
# Windows
sdk.dir=C\:\\Users\\<USER>\\AppData\\Local\\Android\\Sdk

# Linux / macOS
sdk.dir=/home/<USER>/Android/Sdk
```

### "Java version" / "Unsupported class file major version"

Falsche JDK-Version. Lösung in Android Studio:

```
File → Project Structure → SDK Location → Gradle JDK → JDK 17 auswählen
```

### "Could not find play-services-location"

Google Maven-Repository fehlt oder Netzwerkproblem:

```
# In Android Studio:
File → Sync Project with Gradle Files

# Prüfen ob in settings.gradle enthalten:
repositories {
    google()        ← muss vorhanden sein
    mavenCentral()
}
```

### Gradle Sync hängt (Proxy / Firewall)

`gradle.properties` ergänzen:

```properties
systemProp.http.proxyHost=proxy.firma.de
systemProp.http.proxyPort=8080
systemProp.https.proxyHost=proxy.firma.de
systemProp.https.proxyPort=8080
```

### "USB device not found" (ADB)

```bash
# Treiber prüfen (Windows: Google USB-Treiber aus SDK)
# USB-Debugging aktivieren:
# Einstellungen → Über das Telefon → Build-Nummer 7x tippen
# → Entwickleroptionen → USB-Debugging → EIN

adb kill-server
adb start-server
adb devices
```

---

## Release-APK (signiert, für Weitergabe)

Eine Debug-APK ist nur für Tests gedacht. Für die Weitergabe an andere Geräte
oder den Play Store ist eine signierte Release-APK nötig.

### Android Studio

```
Build → Generate Signed Bundle / APK → APK
→ Keystore erstellen oder vorhandenen wählen
→ Release-Variante wählen → Finish
```

### Kommandozeile

```bash
# Keystore erstellen (einmalig)
keytool -genkey -v -keystore maptileviewer.jks \
        -alias maptileviewer -keyalg RSA -keysize 2048 -validity 10000

# Release-APK bauen
./gradlew assembleRelease \
    -Pandroid.injected.signing.store.file=maptileviewer.jks \
    -Pandroid.injected.signing.store.password=PASSWORT \
    -Pandroid.injected.signing.key.alias=maptileviewer \
    -Pandroid.injected.signing.key.password=PASSWORT
```

---

*Map Tile Viewer Android v1.0 · Kompilieranleitung · Stand März 2026*
