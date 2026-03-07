# Gradle Wrapper Setup

Die Datei `gradle/wrapper/gradle-wrapper.jar` kann aus Lizenzgruenden nicht
im ZIP enthalten sein. Ohne sie funktioniert `./gradlew` nicht.

## Einfachste Loesung: gradle-wrapper.jar herunterladen

```bash
cd MapTileViewer_Android

# Variante A: via curl (empfohlen)
mkdir -p gradle/wrapper
curl -Lo gradle/wrapper/gradle-wrapper.jar \
  https://github.com/gradle/gradle/raw/v8.2.0/gradle/wrapper/gradle-wrapper.jar

# Variante B: via wget
wget -O gradle/wrapper/gradle-wrapper.jar \
  https://github.com/gradle/gradle/raw/v8.2.0/gradle/wrapper/gradle-wrapper.jar
```

Danach normal bauen:

```bash
chmod +x gradlew
./gradlew assembleDebug
```

## Alternative: System-Gradle verwenden

```bash
# Gradle direkt (ohne Wrapper), falls bereits installiert:
gradle assembleDebug

# Oder Gradle 8.x via SDKMAN installieren:
curl -s "https://get.sdkman.io" | bash
sdk install gradle 8.2
gradle assembleDebug
```

## Mit Android Studio

Android Studio braucht die gradle-wrapper.jar NICHT – es laedt Gradle
automatisch beim ersten Sync herunter. Einfach Projekt oeffnen und
Gradle Sync abwarten.
