#!/usr/bin/env python3
"""
Map Tile Viewer  v4.0
=====================
Neu in v4.0: Koordinaten-Dialog fuer beliebig grosse Exportbereiche,
unabhaengig vom sichtbaren Kartenausschnitt.
"""

import os, math, threading, collections
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from io import BytesIO

try:
    import requests
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "Pillow"])
    import requests
    from PIL import Image, ImageTk, ImageDraw

# ──────────────────────────────────────────────────────────────────────────────
#  Konstanten & Konfiguration
# ──────────────────────────────────────────────────────────────────────────────

TILE_SIZE   = 256
CACHE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tile_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Maximale Anzahl von Kacheln im RAM-Cache (je Kachel ~256 KB RGBA)
# 300 Kacheln ≈ 75 MB  |  100 ≈ 25 MB  |  500 ≈ 125 MB
MAX_TILE_CACHE = 300

DEFAULT_LAT  = 48.1374
DEFAULT_LON  = 11.5755
DEFAULT_ZOOM = 12

COLORS = {
    "bg":        "#0f0f1a",
    "toolbar":   "#16213e",
    "toolbar2":  "#0d1b3e",
    "toolbar3":  "#0a1828",
    "accent":    "#4a9eff",
    "text":      "#c8d8f0",
    "dim":       "#5a6a8a",
    "tile_bg":   "#0a0a18",
    "tile_grid": "#1a1a2e",
    "btn":       "#1e3a6e",
    "btn_hover": "#2a4a8e",
    "btn_active":"#3a5aae",
    "danger":    "#6e1e1e",
    "success":   "#1e6e3a",
    "zoom_fg":   "#88ffaa",
    "sel_border":"#4a9eff",
    "export_btn":"#1e5a3a",
    "dialog_bg": "#0f1a2e",
    "field_bg":  "#1a2a4a",
    "warn":      "#8e5a1e",
}

PROVIDERS = {
    "OpenStreetMap": {
        "url":    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "max_z":  19,
        "headers":{"User-Agent":"MapTileViewer/4.0 (personal use; python/requests)"},
        "attr":   "© OpenStreetMap contributors",
    },
    "Google Strasse": {
        "url":    "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "max_z":  20,
        "headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        "attr":   "© Google Maps",
    },
    "Google Satellit": {
        "url":    "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "max_z":  20,
        "headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        "attr":   "© Google Maps",
    },
    "Google Hybrid": {
        "url":    "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "max_z":  20,
        "headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        "attr":   "© Google Maps",
    },
    "Bing Strasse": {
        "url":    "__bing_road__",
        "max_z":  19,
        "headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        "attr":   "© Microsoft Bing Maps",
    },
    "Bing Satellit": {
        "url":    "__bing_aerial__",
        "max_z":  19,
        "headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        "attr":   "© Microsoft Bing Maps",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
#  Koordinaten-Werkzeuge
# ──────────────────────────────────────────────────────────────────────────────

def ll2tile(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y

def ll2tile_f(lat, lon, z):
    """Wie ll2tile, aber gibt Fliesskomma-Koordinaten zurueck (fuer exaktes Cropping)."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def tile2ll(tx, ty, z):
    n = 2 ** z
    lon = tx / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / n))))
    return lat, lon

def tile2quadkey(x, y, z):
    qk = []
    for i in range(z, 0, -1):
        d, m = 0, 1 << (i - 1)
        if x & m: d += 1
        if y & m: d += 2
        qk.append(str(d))
    return "".join(qk)

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    a = math.radians(lat2 - lat1)
    b = math.radians(lon2 - lon1)
    h = (math.sin(a/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(b/2)**2)
    return 2 * R * math.asin(math.sqrt(h))

def viewport_bounds(tile_x, tile_y, offset_x, offset_y, zoom, W, H):
    """
    Berechnet die geografischen Grenzen des sichtbaren Kartenausschnitts.

    Args:
        tile_x, tile_y:   Kachel-Index der Bildschirmmitte.
        offset_x, offset_y: Sub-Kachel-Offset in Pixeln.
        zoom:             Aktuelle Zoomstufe.
        W, H:             Canvas-Groesse in Pixeln.

    Returns:
        (lat_n, lat_s, lon_w, lon_e): Geografische Grenzen des Sichtfensters.
    """
    CX, CY = W / 2, H / 2
    ftx_w = tile_x + (-CX + offset_x) / TILE_SIZE
    fty_n = tile_y + (-CY + offset_y) / TILE_SIZE
    ftx_e = tile_x + ( CX + offset_x) / TILE_SIZE
    fty_s = tile_y + ( CY + offset_y) / TILE_SIZE
    lat_n, lon_w = tile2ll(ftx_w, fty_n, zoom)
    lat_s, lon_e = tile2ll(ftx_e, fty_s, zoom)
    return lat_n, lat_s, lon_w, lon_e

# ──────────────────────────────────────────────────────────────────────────────
#  Kachel-Download & Cache
# ──────────────────────────────────────────────────────────────────────────────

def tile_url(provider, x, y, z):
    tmpl = PROVIDERS[provider]["url"]
    if tmpl == "__bing_road__":
        return f"https://t0.ssl.ak.tiles.virtualearth.net/tiles/r{tile2quadkey(x,y,z)}.png?g=1"
    if tmpl == "__bing_aerial__":
        return f"https://t0.ssl.ak.tiles.virtualearth.net/tiles/a{tile2quadkey(x,y,z)}.jpeg?g=1"
    return tmpl.format(x=x, y=y, z=z)

def cache_path(provider, x, y, z):
    d = os.path.join(CACHE_DIR, provider.replace(" ", "_"), str(z))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{x}_{y}.png")

_PLACEHOLDER = None

def placeholder_tile():
    global _PLACEHOLDER
    if _PLACEHOLDER is None:
        img  = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (15, 15, 30, 255))
        draw = ImageDraw.Draw(img)
        for i in range(0, TILE_SIZE + 1, 64):
            draw.line([(i, 0), (i, TILE_SIZE)], fill=(30, 30, 50, 255))
            draw.line([(0, i), (TILE_SIZE, i)], fill=(30, 30, 50, 255))
        _PLACEHOLDER = img
    return _PLACEHOLDER.copy()

def fetch_tile(provider, x, y, z, progress_cb=None):
    """
    Laedt eine Kachel (Cache-first). Optionaler progress_cb() wird nach
    erfolgreichem Download aufgerufen (fuer Fortschrittsanzeige).
    """
    cp = cache_path(provider, x, y, z)
    if os.path.exists(cp):
        try:
            img = Image.open(cp).convert("RGBA")
            if progress_cb:
                progress_cb()
            return img
        except Exception:
            pass
    url  = tile_url(provider, x, y, z)
    hdrs = PROVIDERS[provider]["headers"].copy()
    hdrs["Accept"] = "image/png,image/jpeg,image/*,*/*"
    try:
        r = requests.get(url, headers=hdrs, timeout=12)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img.save(cp)
        if progress_cb:
            progress_cb()
        return img
    except Exception as exc:
        print(f"  [WARN] {provider} {z}/{x}/{y}: {exc}")
        return placeholder_tile()

# ──────────────────────────────────────────────────────────────────────────────
#  Geocoding
# ──────────────────────────────────────────────────────────────────────────────

def geocode(query):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": query, "format": "json", "limit": 1},
                         headers={"User-Agent": "MapTileViewer/4.0"}, timeout=8)
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:
        print(f"  [Geocode] {exc}")
    return None

# ──────────────────────────────────────────────────────────────────────────────
#  Export-Fortschrittsdialog
# ──────────────────────────────────────────────────────────────────────────────

class ExportProgressDialog(tk.Toplevel):
    """Modaler Fortschrittsdialog mit Abbrechen-Button."""

    def __init__(self, parent, total_tiles):
        super().__init__(parent)
        self.title("PNG-Export")
        self.resizable(False, False)
        self.configure(bg=COLORS["toolbar"])
        self.grab_set()
        self.cancelled = False
        self.total     = total_tiles

        self.geometry("440x200")
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - 440) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.geometry(f"+{px}+{py}")

        tk.Label(self, text="Karten-Export laeuft ...", bg=COLORS["toolbar"],
                 fg=COLORS["accent"], font=("Helvetica", 13, "bold")).pack(pady=(16, 4))

        self.info_var = tk.StringVar(value=f"0 / {total_tiles} Kacheln ...")
        tk.Label(self, textvariable=self.info_var, bg=COLORS["toolbar"],
                 fg=COLORS["text"], font=("Helvetica", 10)).pack()

        self.bar = ttk.Progressbar(self, length=380, mode="determinate",
                                   maximum=total_tiles)
        self.bar.pack(pady=10)

        self.size_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.size_var, bg=COLORS["toolbar"],
                 fg=COLORS["dim"], font=("Helvetica", 9)).pack()

        tk.Button(self, text="  Abbrechen  ", command=self._cancel,
                  bg=COLORS["danger"], fg="white", relief="flat",
                  font=("Helvetica", 10), cursor="hand2").pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def update_progress(self, done, total, img_w, img_h):
        if not self.winfo_exists():
            return
        self.bar["value"] = done
        self.info_var.set(f"{done} / {total} Kacheln geladen ...")
        mb = (img_w * img_h * 3) / 1_048_576
        self.size_var.set(f"Ausgabe: {img_w} x {img_h} px  (~{mb:.1f} MB unkomprimiert)")

    def _cancel(self):
        self.cancelled = True
        self.destroy()

# ──────────────────────────────────────────────────────────────────────────────
#  Koordinaten-Export-Dialog
# ──────────────────────────────────────────────────────────────────────────────

class BBoxExportDialog(tk.Toplevel):
    """
    Dialog zur Eingabe eines beliebig grossen Export-Bereichs per Koordinaten.

    Ermoeglicht es, einen Kartenausschnitt zu exportieren, der groesser ist
    als das sichtbare Vorschaufenster. Der Bereich wird ueber geografische
    Koordinaten (Nord/Sued/West/Ost) definiert.

    Features:
        - Vier Eingabefelder fuer N/S/W/E in Dezimalgrad
        - "Aktuelle Ansicht" Button: fuellt Felder mit aktuellen Viewport-Grenzen
        - Geocoding-Suche: Ortsname -> Koordinaten automatisch eintragen
        - Zoom-Selektor: Export-Zoom unabhaengig vom Vorschau-Zoom waehlbar
        - Live-Vorschau: Kachelanzahl, Bildgroesse, Ausdehnung in km, Dateigroesse
        - Warnhinweise bei sehr grossen Bereichen (>500 Kacheln oder >200 MP)
        - Export-Button startet Download und oeffnet Fortschrittsdialog
    """

    MAX_TILES_WARN = 500    # Ab dieser Kachelanzahl Warnhinweis
    MAX_PX_HARD    = 200_000_000  # Absolutes Limit fuer Rueckfrage

    def __init__(self, parent):
        """
        Args:
            parent: MapViewer-Instanz (wird fuer Viewport-Daten und Export benoetigt).
        """
        super().__init__(parent)
        self.parent  = parent
        self.title("Bereich per Koordinaten exportieren")
        self.resizable(True, True)
        self.configure(bg=COLORS["dialog_bg"])
        self.minsize(520, 560)

        # Fenster zentrieren
        self.geometry("560x620")
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - 560) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 620) // 2
        self.geometry(f"+{px}+{py}")

        self._build_ui()

        # Mit aktueller Ansicht vorbelegen
        self._fill_from_viewport()

    # ── Dialog-UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        """Erstellt alle Elemente des Koordinaten-Dialogs."""
        pad = {"padx": 18, "pady": 6}

        # ── Titel ──────────────────────────────────────────────────────────────
        tk.Label(self, text="Exportbereich definieren",
                 bg=COLORS["dialog_bg"], fg=COLORS["accent"],
                 font=("Helvetica", 14, "bold")).pack(pady=(18, 4))
        tk.Label(self,
                 text="Der Bereich kann groesser sein als das sichtbare Vorschaufenster.",
                 bg=COLORS["dialog_bg"], fg=COLORS["dim"],
                 font=("Helvetica", 9)).pack()

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=18, pady=10)

        # ── Schnell-Buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=COLORS["dialog_bg"])
        btn_frame.pack(fill=tk.X, **pad)

        self._mbtn(btn_frame, "Aktuelle Ansicht uebernehmen",
                   self._fill_from_viewport).pack(side=tk.LEFT, padx=(0, 8))
        self._mbtn(btn_frame, "Auswahl vom Viewer uebernehmen",
                   self._fill_from_selection).pack(side=tk.LEFT)

        # ── Orts-Suche ────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=COLORS["dialog_bg"])
        search_frame.pack(fill=tk.X, **pad)
        tk.Label(search_frame, text="Ort suchen:", bg=COLORS["dialog_bg"],
                 fg=COLORS["text"], font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(0,6))
        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg=COLORS["field_bg"], fg="white", insertbackground="white",
                 relief="flat", font=("Helvetica", 10), width=22
                 ).pack(side=tk.LEFT, ipady=4)
        self._mbtn(search_frame, " Suchen ",
                   self._geocode_fill).pack(side=tk.LEFT, padx=6)
        self.search_var.get  # bind Enter
        search_frame.winfo_children()[1].bind("<Return>", lambda e: self._geocode_fill())

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=18, pady=6)

        # ── Koordinaten-Eingabe ────────────────────────────────────────────────
        tk.Label(self, text="Begrenzungsrahmen (Dezimalgrad)",
                 bg=COLORS["dialog_bg"], fg=COLORS["text"],
                 font=("Helvetica", 11, "bold")).pack(**pad)

        coords_frame = tk.Frame(self, bg=COLORS["dialog_bg"])
        coords_frame.pack(**pad)

        self._coord_vars = {}
        fields = [
            ("Nord (max. Breitengrad)",  "lat_n", "+48.20000"),
            ("Sued (min. Breitengrad)",  "lat_s", "+48.07000"),
            ("West (min. Laengengrad)",  "lon_w", "+11.40000"),
            ("Ost  (max. Laengengrad)",  "lon_e", "+11.72000"),
        ]
        for i, (label, key, placeholder) in enumerate(fields):
            row = tk.Frame(coords_frame, bg=COLORS["dialog_bg"])
            row.grid(row=i, column=0, sticky="w", pady=3)
            tk.Label(row, text=f"{label}:", bg=COLORS["dialog_bg"],
                     fg=COLORS["dim"], font=("Helvetica", 10), width=28,
                     anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar()
            var.trace_add("write", self._on_input_change)
            entry = tk.Entry(row, textvariable=var, bg=COLORS["field_bg"],
                             fg="white", insertbackground="white",
                             relief="flat", font=("Courier", 11), width=16)
            entry.pack(side=tk.LEFT, ipady=5, padx=(8, 0))
            self._coord_vars[key] = var

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=18, pady=8)

        # ── Zoom-Auswahl ───────────────────────────────────────────────────────
        zoom_frame = tk.Frame(self, bg=COLORS["dialog_bg"])
        zoom_frame.pack(fill=tk.X, **pad)
        tk.Label(zoom_frame, text="Export-Zoom:", bg=COLORS["dialog_bg"],
                 fg=COLORS["text"], font=("Helvetica", 11, "bold")
                 ).pack(side=tk.LEFT, padx=(0, 12))

        self.export_zoom_var = tk.IntVar(value=self.parent.zoom)
        self.export_zoom_var.trace_add("write", self._on_input_change)

        for z in [8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20]:
            rb = tk.Radiobutton(zoom_frame, text=str(z),
                                variable=self.export_zoom_var, value=z,
                                bg=COLORS["dialog_bg"], fg=COLORS["text"],
                                selectcolor=COLORS["btn_active"],
                                activebackground=COLORS["dialog_bg"],
                                font=("Helvetica", 10))
            rb.pack(side=tk.LEFT, padx=2)

        tk.Label(zoom_frame, text="(OSM: max 19  |  Google/Bing: max 20  |  aktuell: " + str(self.parent.zoom) + ")",
                 bg=COLORS["dialog_bg"], fg=COLORS["dim"],
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=8)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=18, pady=6)

        # ── Anbieter-Auswahl ───────────────────────────────────────────────────
        prov_frame = tk.Frame(self, bg=COLORS["dialog_bg"])
        prov_frame.pack(fill=tk.X, **pad)
        tk.Label(prov_frame, text="Anbieter:", bg=COLORS["dialog_bg"],
                 fg=COLORS["text"], font=("Helvetica", 11, "bold")
                 ).pack(side=tk.LEFT, padx=(0, 10))
        self.export_prov_var = tk.StringVar(value=self.parent.provider)
        prov_cmb = ttk.Combobox(prov_frame, textvariable=self.export_prov_var,
                                values=list(PROVIDERS.keys()),
                                state="readonly", width=22,
                                font=("Helvetica", 10))
        prov_cmb.pack(side=tk.LEFT)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=18, pady=8)

        # ── Info-Box ───────────────────────────────────────────────────────────
        info_frame = tk.Frame(self, bg="#0a1525", bd=0)
        info_frame.pack(fill=tk.X, padx=18, pady=(0, 6))

        self.info_vars = {k: tk.StringVar(value="–") for k in
                         ["tiles", "pixels", "km", "filesize", "warn"]}

        rows_info = [
            ("Kacheln:", "tiles"),
            ("Bildgroesse:", "pixels"),
            ("Ausdehnung:", "km"),
            ("Dateigroesse (ca.):", "filesize"),
        ]
        for label, key in rows_info:
            row = tk.Frame(info_frame, bg="#0a1525")
            row.pack(fill=tk.X, padx=12, pady=1)
            tk.Label(row, text=label, bg="#0a1525", fg=COLORS["dim"],
                     font=("Helvetica", 9), width=22, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, textvariable=self.info_vars[key], bg="#0a1525",
                     fg=COLORS["text"], font=("Courier", 9)).pack(side=tk.LEFT)

        self.warn_lbl = tk.Label(info_frame, textvariable=self.info_vars["warn"],
                                 bg="#0a1525", fg="#ffaa44",
                                 font=("Helvetica", 9, "bold"))
        self.warn_lbl.pack(pady=(4, 6))

        # ── Export-Button ──────────────────────────────────────────────────────
        self.export_btn = tk.Button(self, text="  Als PNG exportieren  ",
                                    command=self._start_export,
                                    bg=COLORS["export_btn"], fg="white",
                                    relief="flat", font=("Helvetica", 11, "bold"),
                                    cursor="hand2", pady=8)
        self.export_btn.pack(pady=(4, 18))

    def _mbtn(self, parent, text, cmd):
        """Hilfs-Methode: kleiner Dialog-Button."""
        return tk.Button(parent, text=text, command=cmd,
                         bg=COLORS["btn"], fg="white", relief="flat",
                         font=("Helvetica", 9), cursor="hand2",
                         activebackground=COLORS["btn_hover"],
                         padx=8, pady=3)

    # ── Koordinaten-Quellen ────────────────────────────────────────────────────

    def _fill_from_viewport(self):
        """
        Befuellt die Koordinatenfelder mit den Grenzen des aktuellen Vorschaufensters.

        Liest die Canvas-Groesse und den aktuellen Karten-Zustand vom Parent
        und berechnet mit viewport_bounds() die geografischen Grenzen.
        """
        p  = self.parent
        W  = p.canvas.winfo_width()
        H  = p.canvas.winfo_height()
        if W < 2:
            return
        lat_n, lat_s, lon_w, lon_e = viewport_bounds(
            p.tile_x, p.tile_y, p.offset_x, p.offset_y, p.zoom, W, H)
        self._set_coords(lat_n, lat_s, lon_w, lon_e)
        self.export_zoom_var.set(p.zoom)

    def _fill_from_selection(self):
        """
        Befuellt die Koordinatenfelder aus der aktuellen Drag-Auswahl im Viewer.

        Verwendet die gespeicherten Canvas-Koordinaten (_sel_start/_sel_end)
        und rechnet sie mit _canvas_to_tile() + tile2ll() in Geografisches um.
        Falls keine Auswahl vorhanden, wird eine Hinweismeldung gezeigt.
        """
        p = self.parent
        if not (p._sel_start and p._sel_end):
            messagebox.showinfo("Keine Auswahl",
                "Bitte erst im Viewer einen Bereich aufziehen,\n"
                "dann diesen Button klicken.", parent=self)
            return
        x0, y0 = p._sel_start
        x1, y1 = p._sel_end
        ftx0, fty0 = p._canvas_to_tile(min(x0,x1), min(y0,y1))
        ftx1, fty1 = p._canvas_to_tile(max(x0,x1), max(y0,y1))
        lat_n, lon_w = tile2ll(ftx0, fty0, p.zoom)
        lat_s, lon_e = tile2ll(ftx1, fty1, p.zoom)
        self._set_coords(lat_n, lat_s, lon_w, lon_e)
        self.export_zoom_var.set(p.zoom)

    def _geocode_fill(self):
        """
        Sucht einen Ortsnamen per Nominatim und setzt die Koordinaten auf
        einen sinnvollen Bereich um den gefundenen Punkt (zoom-abhaengige Box).
        """
        q = self.search_var.get().strip()
        if not q:
            return
        result = geocode(q)
        if not result:
            messagebox.showwarning("Nicht gefunden",
                f'"{q}" konnte nicht gefunden werden.', parent=self)
            return
        lat, lon = result
        z = self.export_zoom_var.get()
        # Sinnvolle Box-Groesse abhaengig vom Zoom
        delta = {8: 2.0, 10: 0.5, 12: 0.1, 13: 0.05,
                 14: 0.03, 15: 0.015, 16: 0.008,
                 17: 0.004, 18: 0.002, 19: 0.001, 20: 0.0005}.get(z, 0.1)
        self._set_coords(lat + delta, lat - delta,
                         lon - delta * 1.5, lon + delta * 1.5)

    def _set_coords(self, lat_n, lat_s, lon_w, lon_e):
        """Schreibt vier Koordinaten in die Eingabefelder."""
        self._coord_vars["lat_n"].set(f"{lat_n:.6f}")
        self._coord_vars["lat_s"].set(f"{lat_s:.6f}")
        self._coord_vars["lon_w"].set(f"{lon_w:.6f}")
        self._coord_vars["lon_e"].set(f"{lon_e:.6f}")

    # ── Live-Vorschau ──────────────────────────────────────────────────────────

    def _on_input_change(self, *_):
        """
        Callback: wird bei jeder Aenderung in Koordinatenfeldern oder Zoom aufgerufen.
        Berechnet und zeigt Kachelanzahl, Bildgroesse, Ausdehnung und Warnungen.
        """
        try:
            lat_n = float(self._coord_vars["lat_n"].get())
            lat_s = float(self._coord_vars["lat_s"].get())
            lon_w = float(self._coord_vars["lon_w"].get())
            lon_e = float(self._coord_vars["lon_e"].get())
            z     = int(self.export_zoom_var.get())
        except ValueError:
            for k in ["tiles", "pixels", "km", "filesize"]:
                self.info_vars[k].set("–")
            self.info_vars["warn"].set("")
            return

        if lat_n <= lat_s or lon_e <= lon_w:
            self.info_vars["warn"].set("Nord muss groesser als Sued sein, Ost groesser als West!")
            return

        # Kachel-Indizes berechnen
        ftx0, fty0 = ll2tile_f(lat_n, lon_w, z)
        ftx1, fty1 = ll2tile_f(lat_s, lon_e, z)
        tx0, ty0 = int(math.floor(ftx0)), int(math.floor(fty0))
        tx1, ty1 = int(math.ceil(ftx1)),  int(math.ceil(fty1))

        tile_count = (tx1 - tx0) * (ty1 - ty0)
        out_w      = int((ftx1 - ftx0) * TILE_SIZE)
        out_h      = int((fty1 - fty0) * TILE_SIZE)
        px_total   = out_w * out_h
        mb_raw     = px_total * 3 / 1_048_576
        mb_png     = mb_raw * 0.25  # PNG-Kompression grob ~25% der Rohgroesse

        km_w = haversine_m(lat_n, lon_w, lat_n, lon_e) / 1000
        km_h = haversine_m(lat_n, lon_w, lat_s, lon_w) / 1000

        self.info_vars["tiles"].set(f"{tile_count:,}  ({tx1-tx0} x {ty1-ty0})")
        self.info_vars["pixels"].set(f"{out_w:,} x {out_h:,} px")
        self.info_vars["km"].set(f"{km_w:.2f} km x {km_h:.2f} km")
        self.info_vars["filesize"].set(
            f"~{mb_raw:.0f} MB (RAM)  /  ~{mb_png:.0f} MB (PNG-Datei)")

        # Warnungen
        warn = ""
        if tile_count > 2000:
            warn = f"WARNUNG: {tile_count:,} Kacheln – sehr langer Download!"
        elif tile_count > self.MAX_TILES_WARN:
            warn = f"Hinweis: {tile_count} Kacheln – kann laenger dauern."
        if px_total > self.MAX_PX_HARD:
            warn += f"  SEHR GROSSES BILD ({mb_raw:.0f} MB RAM noetig)"
        self.info_vars["warn"].set(warn)

        ok = tile_count > 0 and out_w > 0 and out_h > 0
        self.export_btn.config(state=tk.NORMAL if ok else tk.DISABLED)

    # ── Export starten ─────────────────────────────────────────────────────────

    def _start_export(self):
        """
        Liest alle Parameter aus dem Dialog, oeffnet den Datei-Speicher-Dialog
        und startet den Export-Thread.

        Validiert die Eingaben und zeigt bei sehr grossen Bildern eine
        Bestaetigung an. Schliesst den Dialog nach Bestaetigung.
        """
        try:
            lat_n = float(self._coord_vars["lat_n"].get())
            lat_s = float(self._coord_vars["lat_s"].get())
            lon_w = float(self._coord_vars["lon_w"].get())
            lon_e = float(self._coord_vars["lon_e"].get())
            z     = int(self.export_zoom_var.get())
            prov  = self.export_prov_var.get()
        except ValueError:
            messagebox.showerror("Ungueltige Eingabe",
                "Bitte gueltige Dezimalzahlen eingeben.", parent=self)
            return

        if lat_n <= lat_s or lon_e <= lon_w:
            messagebox.showerror("Ungueltige Koordinaten",
                "Nord > Sued und Ost > West muss gelten.", parent=self)
            return

        # Kachel-Bereich
        ftx0, fty0 = ll2tile_f(lat_n, lon_w, z)
        ftx1, fty1 = ll2tile_f(lat_s, lon_e, z)
        tx0, ty0   = int(math.floor(ftx0)), int(math.floor(fty0))
        tx1, ty1   = int(math.ceil(ftx1)),  int(math.ceil(fty1))
        total      = (tx1 - tx0) * (ty1 - ty0)
        out_w      = int((ftx1 - ftx0) * TILE_SIZE)
        out_h      = int((fty1 - fty0) * TILE_SIZE)

        if out_w * out_h > self.MAX_PX_HARD:
            if not messagebox.askyesno("Sehr grosses Bild",
                f"Das Bild wird {out_w} x {out_h} px gross\n"
                f"(~{out_w*out_h*3/1_048_576:.0f} MB RAM).\n\n"
                f"Trotzdem exportieren?", parent=self):
                return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG-Bild", "*.png"), ("Alle Dateien", "*.*")],
            initialfile=f"karte_{prov.replace(' ','_')}_z{z}.png",
            title="Karte speichern als ...",
            parent=self
        )
        if not save_path:
            return

        self.destroy()  # Dialog schliessen, Export laeuft im Hintergrund

        dlg = ExportProgressDialog(self.parent, total)
        threading.Thread(
            target=self.parent._export_bg,
            args=(save_path, tx0, ty0, tx1, ty1,
                  ftx0, fty0, ftx1, fty1,
                  out_w, out_h, z, prov, dlg),
            daemon=True
        ).start()


# ──────────────────────────────────────────────────────────────────────────────
#  LRU-RAM-Cache fuer Kacheln
# ──────────────────────────────────────────────────────────────────────────────

class LRUTileCache:
    """
    Speichert PhotoImage-Objekte der geladenen Kacheln mit LRU-Verdrängung.

    tkinter-PhotoImage-Objekte dürfen nicht vom GC freigegeben werden,
    solange sie auf dem Canvas referenziert sind. Diese Klasse hält genau
    `maxsize` Bilder im Speicher und wirft das zuletzt am wenigsten
    benutzte (Least Recently Used) heraus, wenn das Limit erreicht ist.

    Intern verwendet sie collections.OrderedDict: Zugriffe verschieben den
    Eintrag ans Ende (→ MRU), Verdrängungen entfernen vom Anfang (→ LRU).

    Attributes:
        maxsize (int): Maximale Anzahl gecachter Kacheln.

    Beispiel:
        cache = LRUTileCache(maxsize=300)
        cache[key] = photo_image   # Einfügen
        if key in cache:           # Prüfen (zählt als Zugriff)
            img = cache[key]       # Lesen  (verschiebt nach MRU)
        len(cache)                 # Aktuelle Größe
        cache.memory_mb            # Geschätzter RAM in MB
    """

    def __init__(self, maxsize: int = MAX_TILE_CACHE):
        self.maxsize = maxsize
        self._data   = collections.OrderedDict()

    def __contains__(self, key) -> bool:
        return key in self._data

    def __getitem__(self, key):
        """Liest einen Eintrag und markiert ihn als zuletzt verwendet."""
        self._data.move_to_end(key)
        return self._data[key]

    def __setitem__(self, key, value):
        """
        Fügt einen Eintrag ein oder aktualisiert ihn.
        Wenn das Cache-Limit erreicht ist, wird der LRU-Eintrag entfernt.
        """
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.maxsize:
            self._data.popitem(last=False)   # LRU entfernen

    def __len__(self) -> int:
        return len(self._data)

    def clear(self):
        """Leert den gesamten Cache."""
        self._data.clear()

    @property
    def memory_mb(self) -> float:
        """Geschätzter RAM-Verbrauch in MB (256×256 RGBA = 262 144 Bytes/Kachel)."""
        return len(self._data) * TILE_SIZE * TILE_SIZE * 4 / 1_048_576

    @property
    def fill_pct(self) -> int:
        """Füllstand in Prozent (0–100)."""
        return int(len(self._data) / self.maxsize * 100)


# ──────────────────────────────────────────────────────────────────────────────
#  Haupt-Viewer
# ──────────────────────────────────────────────────────────────────────────────

class MapViewer(tk.Tk):
    """
    Interaktives Kartenfenster mit Pan, Zoom, Ortssuche,
    Drag-Auswahl und Koordinaten-Export.
    """

    def __init__(self):
        super().__init__()
        self.title("Map Tile Viewer  v4.0  -  OSM / Google / Bing")
        self.geometry("1150x820")
        self.minsize(700, 500)
        self.configure(bg=COLORS["bg"])

        self.zoom      = DEFAULT_ZOOM
        self.provider  = "OpenStreetMap"
        tx, ty         = ll2tile(DEFAULT_LAT, DEFAULT_LON, self.zoom)
        self.tile_x    = tx
        self.tile_y    = ty
        self.offset_x  = 0.0
        self.offset_y  = 0.0

        self._drag_pos    = None
        self._tile_photos = LRUTileCache(maxsize=MAX_TILE_CACHE)
        self._loading     = set()
        self._lock        = threading.Lock()
        self._render_id   = None

        self._export_mode = False
        self._sel_start   = None
        self._sel_end     = None
        self._sel_rect_id = None

        self._build_ui()
        self._bind_events()
        self.after(200, self._render)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar 1: Suche & Anbieter
        top = tk.Frame(self, bg=COLORS["toolbar"], height=48)
        top.pack(fill=tk.X); top.pack_propagate(False)
        tk.Label(top, text="  Ort suchen:", bg=COLORS["toolbar"],
                 fg=COLORS["accent"], font=("Helvetica", 11, "bold")).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        se = tk.Entry(top, textvariable=self.search_var, bg="#1a2a4a", fg="white",
                      insertbackground="white", relief="flat", font=("Helvetica", 11), width=24)
        se.pack(side=tk.LEFT, padx=(4,2), ipady=5)
        se.bind("<Return>", lambda e: self._do_search())
        self._make_btn(top, " Suchen ", self._do_search, COLORS["btn"]).pack(side=tk.LEFT, padx=(0,12), pady=8)
        tk.Frame(top, bg="#2a3a5a", width=2).pack(side=tk.LEFT, fill=tk.Y, pady=6)
        tk.Label(top, text="  Quelle:", bg=COLORS["toolbar"],
                 fg=COLORS["dim"], font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(8,2))
        self._provider_btns = {}
        for name in PROVIDERS:
            short = name.replace("OpenStreetMap", "OSM")
            btn = self._make_btn(top, short, lambda n=name: self._set_provider(n), COLORS["btn"])
            btn.pack(side=tk.LEFT, padx=2, pady=8)
            self._provider_btns[name] = btn
        self._update_provider_btns()
        self._make_btn(top, "Cache leeren", self._clear_cache,
                       COLORS["danger"]).pack(side=tk.RIGHT, padx=10, pady=8)

        # Toolbar 2: Zoom
        mid = tk.Frame(self, bg=COLORS["toolbar2"], height=36)
        mid.pack(fill=tk.X); mid.pack_propagate(False)
        self._make_btn(mid, " + ", self._zoom_in,  COLORS["btn"]).pack(side=tk.LEFT, padx=(10,2), pady=5)
        self._make_btn(mid, " - ", self._zoom_out, COLORS["btn"]).pack(side=tk.LEFT, padx=(2,6),  pady=5)
        tk.Label(mid, text="Zoom:", bg=COLORS["toolbar2"], fg=COLORS["dim"],
                 font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(4,2))
        self.zoom_lbl = tk.Label(mid, text=str(self.zoom), bg=COLORS["toolbar2"],
                                  fg=COLORS["zoom_fg"], font=("Courier", 13, "bold"), width=3)
        self.zoom_lbl.pack(side=tk.LEFT)
        self.zoom_slider = tk.Scale(mid, from_=2, to=20, orient=tk.HORIZONTAL,
                                     command=self._slider_zoom, bg=COLORS["toolbar2"],
                                     fg=COLORS["text"], troughcolor=COLORS["btn"],
                                     highlightthickness=0, sliderrelief="flat",
                                     length=150, showvalue=False, activebackground=COLORS["accent"])
        self.zoom_slider.set(self.zoom)
        self.zoom_slider.pack(side=tk.LEFT, padx=8)
        self.status_var = tk.StringVar(value="Bereit")
        tk.Label(mid, textvariable=self.status_var, bg=COLORS["toolbar2"],
                 fg=COLORS["dim"], font=("Helvetica", 9)).pack(side=tk.LEFT, padx=10)
        self.coord_var = tk.StringVar(value="")
        tk.Label(mid, textvariable=self.coord_var, bg=COLORS["toolbar2"],
                 fg=COLORS["accent"], font=("Courier", 10)).pack(side=tk.RIGHT, padx=12)

        # Toolbar 3: Export
        exp = tk.Frame(self, bg=COLORS["toolbar3"], height=42)
        exp.pack(fill=tk.X); exp.pack_propagate(False)
        tk.Label(exp, text="  Export:", bg=COLORS["toolbar3"],
                 fg=COLORS["accent"], font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(8,4))

        self.sel_btn = self._make_btn(exp, " Bereich aufziehen ",
                                      self._toggle_export_mode, COLORS["btn"])
        self.sel_btn.pack(side=tk.LEFT, padx=4, pady=7)

        self._make_btn(exp, " Auswahl loeschen ",
                       self._clear_selection, COLORS["danger"]).pack(side=tk.LEFT, padx=2, pady=7)

        self.export_drag_btn = self._make_btn(exp, " Auswahl als PNG speichern ",
                                              self._start_export_drag, COLORS["export_btn"])
        self.export_drag_btn.pack(side=tk.LEFT, padx=4, pady=7)
        self.export_drag_btn.config(state=tk.DISABLED)

        # Trennlinie
        tk.Frame(exp, bg="#2a3a5a", width=2).pack(side=tk.LEFT, fill=tk.Y, pady=8, padx=8)

        # NEU: Koordinaten-Export-Button
        self._make_btn(exp, " Beliebigen Bereich exportieren ... ",
                       self._open_bbox_dialog, "#2a4a1e").pack(side=tk.LEFT, padx=4, pady=7)

        self.sel_info_var = tk.StringVar(value="Kein Bereich ausgewaehlt")
        tk.Label(exp, textvariable=self.sel_info_var, bg=COLORS["toolbar3"],
                 fg=COLORS["dim"], font=("Helvetica", 9)).pack(side=tk.LEFT, padx=10)

        # Canvas
        self.canvas = tk.Canvas(self, bg=COLORS["tile_bg"],
                                highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _make_btn(self, parent, text, cmd, bg):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                        relief="flat", font=("Helvetica", 9, "bold"), cursor="hand2",
                        activebackground=COLORS["btn_active"], activeforeground="white",
                        padx=6, pady=2)
        btn.bind("<Enter>", lambda _: btn.config(bg=COLORS["btn_hover"]) if btn["state"] != "disabled" else None)
        btn.bind("<Leave>", lambda _: btn.config(bg=bg))
        return btn

    def _update_provider_btns(self):
        for name, btn in self._provider_btns.items():
            active = (name == self.provider)
            btn.config(bg=COLORS["accent"] if active else COLORS["btn"],
                       fg=COLORS["bg"]     if active else "white")

    # ── Events ─────────────────────────────────────────────────────────────────

    def _bind_events(self):
        c = self.canvas
        c.bind("<ButtonPress-1>",   self._on_press)
        c.bind("<B1-Motion>",       self._on_motion)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<MouseWheel>",      self._wheel)
        c.bind("<Button-4>",        self._wheel)
        c.bind("<Button-5>",        self._wheel)
        c.bind("<Motion>",          self._mouse_coords)
        self.bind("<Configure>",    lambda e: self._schedule_render())
        self.bind("<plus>",         lambda e: self._zoom_in())
        self.bind("<minus>",        lambda e: self._zoom_out())
        self.bind("<KP_Add>",       lambda e: self._zoom_in())
        self.bind("<KP_Subtract>",  lambda e: self._zoom_out())
        self.bind("<Escape>",       lambda e: self._clear_selection())

    def _on_press(self, e):
        if self._export_mode:
            self._sel_start = (e.x, e.y)
            self._sel_end   = (e.x, e.y)
            if self._sel_rect_id:
                self.canvas.delete(self._sel_rect_id)
                self._sel_rect_id = None
            self.canvas.delete("sel_hatch")
        else:
            self._drag_pos = (e.x, e.y)

    def _on_motion(self, e):
        if self._export_mode and self._sel_start:
            self._sel_end = (e.x, e.y)
            self._draw_selection_rect()
        elif self._drag_pos:
            dx = e.x - self._drag_pos[0]
            dy = e.y - self._drag_pos[1]
            self._drag_pos = (e.x, e.y)
            self._pan(-dx, -dy)

    def _on_release(self, e):
        if self._export_mode and self._sel_start:
            self._sel_end = (e.x, e.y)
            self._draw_selection_rect()
            self._update_sel_info()
        self._drag_pos = None

    def _draw_selection_rect(self):
        if not (self._sel_start and self._sel_end):
            return
        x0, y0 = self._sel_start
        x1, y1 = self._sel_end
        if self._sel_rect_id:
            self.canvas.delete(self._sel_rect_id)
        self._sel_rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline=COLORS["sel_border"], width=2, dash=(6,3), fill="")
        self.canvas.delete("sel_hatch")
        for i in range(int(min(x0,x1)), int(max(x0,x1)), 12):
            self.canvas.create_line(i, y0, i, y1, fill=COLORS["sel_border"],
                                    width=1, stipple="gray25", tags="sel_hatch")

    def _update_sel_info(self):
        if not (self._sel_start and self._sel_end):
            self.sel_info_var.set("Kein Bereich ausgewaehlt")
            self.export_drag_btn.config(state=tk.DISABLED)
            return
        x0, y0 = self._sel_start
        x1, y1 = self._sel_end
        if abs(x1-x0) < 10 or abs(y1-y0) < 10:
            self.sel_info_var.set("Auswahl zu klein")
            self.export_drag_btn.config(state=tk.DISABLED)
            return
        ftx0, fty0 = self._canvas_to_tile(min(x0,x1), min(y0,y1))
        ftx1, fty1 = self._canvas_to_tile(max(x0,x1), max(y0,y1))
        tc = (math.ceil(ftx1)-math.floor(ftx0)) * (math.ceil(fty1)-math.floor(fty0))
        ow = int((ftx1-ftx0)*TILE_SIZE)
        oh = int((fty1-fty0)*TILE_SIZE)
        lat_n, lon_w = tile2ll(ftx0, fty0, self.zoom)
        lat_s, lon_e = tile2ll(ftx1, fty1, self.zoom)
        km_w = haversine_m(lat_n, lon_w, lat_n, lon_e) / 1000
        km_h = haversine_m(lat_n, lon_w, lat_s, lon_w) / 1000
        self.sel_info_var.set(f"{tc} Kacheln  |  {ow}x{oh}px  |  {km_w:.1f}x{km_h:.1f}km")
        self.export_drag_btn.config(state=tk.NORMAL, bg=COLORS["export_btn"])

    def _canvas_to_tile(self, cx, cy):
        """Canvas-Pixelposition -> Fliesskomma-Kachel-Koordinaten."""
        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        return (self.tile_x + (cx - W/2 + self.offset_x) / TILE_SIZE,
                self.tile_y + (cy - H/2 + self.offset_y) / TILE_SIZE)

    # ── Modi ───────────────────────────────────────────────────────────────────

    def _toggle_export_mode(self):
        self._export_mode = not self._export_mode
        if self._export_mode:
            self.canvas.config(cursor="crosshair")
            self.sel_btn.config(bg=COLORS["accent"], fg=COLORS["bg"],
                                text=" Auswahl-Modus aktiv ")
            self.status_var.set("Auswahl-Modus: Bereich aufziehen")
        else:
            self.canvas.config(cursor="fleur")
            self.sel_btn.config(bg=COLORS["btn"], fg="white",
                                text=" Bereich aufziehen ")
            self.status_var.set("Pan-Modus")

    def _clear_selection(self):
        self._sel_start = None
        self._sel_end   = None
        if self._sel_rect_id:
            self.canvas.delete(self._sel_rect_id)
            self._sel_rect_id = None
        self.canvas.delete("sel_hatch")
        self.sel_info_var.set("Kein Bereich ausgewaehlt")
        self.export_drag_btn.config(state=tk.DISABLED)
        if self._export_mode:
            self._toggle_export_mode()

    def _open_bbox_dialog(self):
        """Oeffnet den Koordinaten-Export-Dialog (BBoxExportDialog)."""
        BBoxExportDialog(self)

    # ── Export (Drag-Auswahl) ──────────────────────────────────────────────────

    def _start_export_drag(self):
        """Startet Export fuer die aktuell aufgezogene Drag-Auswahl."""
        if not (self._sel_start and self._sel_end):
            return
        x0, y0 = self._sel_start
        x1, y1 = self._sel_end
        ftx0, fty0 = self._canvas_to_tile(min(x0,x1), min(y0,y1))
        ftx1, fty1 = self._canvas_to_tile(max(x0,x1), max(y0,y1))
        tx0, ty0 = int(math.floor(ftx0)), int(math.floor(fty0))
        tx1, ty1 = int(math.ceil(ftx1)),  int(math.ceil(fty1))
        out_w = int((ftx1-ftx0)*TILE_SIZE)
        out_h = int((fty1-fty0)*TILE_SIZE)
        total = (tx1-tx0) * (ty1-ty0)

        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG-Bild", "*.png"), ("Alle Dateien", "*.*")],
            initialfile=f"karte_{self.provider.replace(' ','_')}_z{self.zoom}.png",
            title="Karte speichern als ..."
        )
        if not save_path:
            return

        dlg = ExportProgressDialog(self, total)
        threading.Thread(target=self._export_bg,
                         args=(save_path, tx0, ty0, tx1, ty1,
                               ftx0, fty0, ftx1, fty1,
                               out_w, out_h, self.zoom, self.provider, dlg),
                         daemon=True).start()

    def _export_bg(self, save_path, tx0, ty0, tx1, ty1,
                   ftx0, fty0, ftx1, fty1, out_w, out_h, zoom, provider, dlg):
        """
        Hintergrund-Thread: Kacheln laden, zusammensetzen, zuschneiden, speichern.
        Unterstuetzt Abbruch via dlg.cancelled. Meldet Fortschritt via after().
        """
        canvas_w  = (tx1-tx0) * TILE_SIZE
        canvas_h  = (ty1-ty0) * TILE_SIZE
        total     = (tx1-tx0) * (ty1-ty0)
        done      = [0]
        max_t     = 2 ** zoom

        # Crop-Offsets: Pixel-Versatz innerhalb des Kachel-Rasters
        cx0 = int((ftx0-tx0) * TILE_SIZE)
        cy0 = int((fty0-ty0) * TILE_SIZE)

        # ── Speicher-effizientes Strip-Processing ─────────────────────────────
        # Anstatt das gesamte Kachel-Raster auf einmal zu erzeugen, wird das
        # Ergebnisbild zeilenweise (strip) aufgebaut. Jede Strip-Zeile wird
        # sofort in das Ausgabebild eingefügt und anschliessend freigegeben.
        # Peak-RAM ≈ (Streifen-Höhe × canvas_w × 3 Bytes) + Ausgabebild.
        STRIP_ROWS = 4   # Kachelzeilen pro Strip (4 × 256 px = 1024 px Höhe)

        result = Image.new("RGB", (out_w, out_h), (20, 20, 35))

        for strip_start in range(ty0, ty1, STRIP_ROWS):
            strip_end = min(strip_start + STRIP_ROWS, ty1)
            strip_h   = (strip_end - strip_start) * TILE_SIZE

            # Einen horizontalen Streifen erzeugen
            strip = Image.new("RGB", (canvas_w, strip_h), (20, 20, 35))

            for ty in range(strip_start, strip_end):
                for tx in range(tx0, tx1):
                    if dlg.cancelled:
                        return
                    tile_img = fetch_tile(provider, tx % max_t, ty, zoom)
                    px = (tx - tx0) * TILE_SIZE
                    py = (ty - strip_start) * TILE_SIZE
                    strip.paste(tile_img.convert("RGB"), (px, py))
                    tile_img.close()   # PIL-Bild sofort freigeben

                    done[0] += 1
                    d, cw, ch = done[0], canvas_w, canvas_h
                    self.after(0, lambda _d=d, _cw=cw, _ch=ch:
                               dlg.update_progress(_d, total, out_w, out_h)
                               if dlg.winfo_exists() else None)

            # Strip in Ausgabebild einkopieren (nur sichtbaren Ausschnitt)
            strip_y_in_canvas = (strip_start - ty0) * TILE_SIZE
            # Überlappung mit dem gewünschten Ausschnitt berechnen
            src_y0 = max(0, cy0 - strip_y_in_canvas)
            src_y1 = min(strip_h, cy0 + out_h - strip_y_in_canvas)
            dst_y0 = max(0, strip_y_in_canvas - cy0)

            if src_y1 > src_y0:
                region = strip.crop((cx0, src_y0, cx0 + out_w, src_y1))
                result.paste(region, (0, dst_y0))
                region.close()

            strip.close()   # Strip-Speicher freigeben

        try:
            result.save(save_path, "PNG")
            fmb = os.path.getsize(save_path) / 1_048_576
            self.after(0, lambda: dlg.destroy() if dlg.winfo_exists() else None)
            self.after(0, lambda: messagebox.showinfo("Export abgeschlossen",
                f"Gespeichert:\n{save_path}\n\n"
                f"Groesse: {out_w} x {out_h} px\n"
                f"Dateigroesse: {fmb:.2f} MB\n"
                f"Kacheln geladen: {done[0]}"))
        except Exception as exc:
            self.after(0, lambda: dlg.destroy() if dlg.winfo_exists() else None)
            self.after(0, lambda: messagebox.showerror("Fehler", str(exc)))

    # ── Pan / Zoom / Render ────────────────────────────────────────────────────

    def _pan(self, dx, dy):
        self.offset_x += dx; self.offset_y += dy
        tx = int(self.offset_x // TILE_SIZE); ty = int(self.offset_y // TILE_SIZE)
        self.tile_x += tx; self.offset_x -= tx * TILE_SIZE
        self.tile_y += ty; self.offset_y -= ty * TILE_SIZE
        self._schedule_render()

    def _wheel(self, e):
        if e.num == 4 or (hasattr(e, "delta") and e.delta > 0): self._zoom_in()
        else: self._zoom_out()

    def _mouse_coords(self, e):
        W, H = self.canvas.winfo_width(), self.canvas.winfo_height()
        if W < 2: return
        fx, fy   = self._canvas_to_tile(e.x, e.y)
        lat, lon = tile2ll(fx, fy, self.zoom)
        lat      = max(-85.05, min(85.05, lat))
        self.coord_var.set(f"  {lat:+.5f} N   {lon:+.7f} E  ")

    def _zoom_in(self):
        if self.zoom < PROVIDERS[self.provider]["max_z"]: self._apply_zoom(self.zoom+1)

    def _zoom_out(self):
        if self.zoom > 2: self._apply_zoom(self.zoom-1)

    def _slider_zoom(self, val):
        z = int(float(val))
        if z != self.zoom: self._apply_zoom(z)

    def _apply_zoom(self, new_z):
        f = 2 ** (new_z - self.zoom)
        self.tile_x = int(self.tile_x * f); self.tile_y = int(self.tile_y * f)
        self.offset_x *= f; self.offset_y *= f
        self.zoom = new_z
        self.zoom_lbl.config(text=str(new_z))
        self.zoom_slider.set(new_z)
        self._tile_photos.clear()
        self._clear_selection()
        self._schedule_render()

    def _set_provider(self, name):
        self.provider = name
        self._update_provider_btns()
        self._tile_photos.clear()
        self._clear_selection()
        self._schedule_render()

    def _clear_cache(self):
        import shutil
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        os.makedirs(CACHE_DIR)
        self._tile_photos.clear()
        self.status_var.set("Cache geleert")
        self._schedule_render()

    def _do_search(self):
        q = self.search_var.get().strip()
        if not q: return
        self.status_var.set(f"Suche: {q} ...")
        threading.Thread(target=self._search_bg, args=(q,), daemon=True).start()

    def _search_bg(self, q):
        result = geocode(q)
        if result:
            lat, lon = result
            self.tile_x, self.tile_y = ll2tile(lat, lon, self.zoom)
            self.offset_x = self.offset_y = 0.0
            self._tile_photos.clear()
            self._clear_selection()
            self.after(0, self._render)
            self.after(0, lambda: self.status_var.set(f"Gefunden: {q}  ({lat:.4f}, {lon:.4f})"))
        else:
            self.after(0, lambda: messagebox.showwarning("Nicht gefunden",
                f'"{q}" konnte nicht gefunden werden.'))
            self.after(0, lambda: self.status_var.set("Nicht gefunden."))

    def _schedule_render(self):
        if self._render_id: self.after_cancel(self._render_id)
        self._render_id = self.after(16, self._render)

    def _render(self):
        self._render_id = None
        c = self.canvas
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        if W < 2 or H < 2: return

        CX, CY  = W/2, H/2
        max_t   = 2 ** self.zoom
        need    = []
        half_w  = math.ceil((CX + abs(self.offset_x)) / TILE_SIZE) + 1
        half_h  = math.ceil((CY + abs(self.offset_y)) / TILE_SIZE) + 1

        for dy in range(-half_h, half_h+2):
            for dx in range(-half_w, half_w+2):
                tx = (self.tile_x + dx) % max_t
                ty =  self.tile_y + dy
                if ty < 0 or ty >= max_t: continue
                px = CX + dx*TILE_SIZE - self.offset_x
                py = CY + dy*TILE_SIZE - self.offset_y
                if px > W+TILE_SIZE or px < -TILE_SIZE*2: continue
                if py > H+TILE_SIZE or py < -TILE_SIZE*2: continue
                key = (self.provider, tx, ty, self.zoom)
                if key in self._tile_photos:
                    c.create_image(int(px), int(py), image=self._tile_photos[key], anchor=tk.NW)
                else:
                    c.create_rectangle(int(px), int(py), int(px)+TILE_SIZE, int(py)+TILE_SIZE,
                                       fill=COLORS["tile_bg"], outline=COLORS["tile_grid"])
                    need.append((tx, ty, key))

        if need:
            self.status_var.set(f"Lade {len(need)} Kacheln ...")
            threading.Thread(target=self._load_bg,
                             args=(need, self.zoom, self.provider), daemon=True).start()
        else:
            self.status_var.set(f"{self.provider}  |  Zoom {self.zoom}  |  RAM-Cache: {len(self._tile_photos)}/{MAX_TILE_CACHE} ({self._tile_photos.memory_mb:.0f} MB)")

        self._draw_scalebar(W, H)
        self._draw_attribution(W, H)
        self._draw_crosshair(W, H)

        if self._sel_start and self._sel_end:
            self._sel_rect_id = None
            self.canvas.delete("sel_hatch")
            self._draw_selection_rect()

    def _draw_scalebar(self, W, H):
        lat1, lon1 = tile2ll(self.tile_x,   self.tile_y, self.zoom)
        lat2, lon2 = tile2ll(self.tile_x+1, self.tile_y, self.zoom)
        mpp = haversine_m(lat1, lon1, lat2, lon2) / TILE_SIZE
        nice = [1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,20000,50000,100000]
        best = min(nice, key=lambda v: abs(v/mpp - 120))
        bpx  = int(best/mpp)
        lbl  = f"{best} m" if best < 1000 else f"{best//1000} km"
        x0, y0 = 20, H-38; x1 = x0+bpx
        self.canvas.create_rectangle(x0-1, y0-1, x1+1, y0+9, fill="#00000088", outline="")
        self.canvas.create_line(x0, y0+4, x1, y0+4, fill="white", width=3)
        self.canvas.create_line(x0, y0, x0, y0+8, fill="white", width=2)
        self.canvas.create_line(x1, y0, x1, y0+8, fill="white", width=2)
        self.canvas.create_text((x0+x1)//2, y0-8, text=lbl, fill="white", font=("Helvetica", 9, "bold"))

    def _draw_attribution(self, W, H):
        attr = PROVIDERS[self.provider]["attr"]
        self.canvas.create_rectangle(W-len(attr)*7-10, H-20, W, H, fill="#00000099", outline="")
        self.canvas.create_text(W-6, H-6, text=attr, anchor=tk.SE, fill="#aabbcc", font=("Helvetica", 9))

    def _draw_crosshair(self, W, H):
        cx, cy, r = W//2, H//2, 10
        self.canvas.create_line(cx-r, cy, cx+r, cy, fill="#ffffff66", width=1)
        self.canvas.create_line(cx, cy-r, cx, cy+r, fill="#ffffff66", width=1)
        self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, outline="#ffffff66", fill="")

    def _load_bg(self, tiles, zoom, provider):
        for tx, ty, key in tiles:
            with self._lock:
                if key in self._loading or key in self._tile_photos: continue
                self._loading.add(key)
            img   = fetch_tile(provider, tx, ty, zoom)
            photo = ImageTk.PhotoImage(img)
            with self._lock:
                self._tile_photos[key] = photo
                self._loading.discard(key)
            self.after(0, self._schedule_render)
        self.after(0, lambda: self.status_var.set(
            f"{provider}  |  Zoom {zoom}  |  RAM-Cache: {len(self._tile_photos)}/{MAX_TILE_CACHE} ({self._tile_photos.memory_mb:.0f} MB)"))


# ──────────────────────────────────────────────────────────────────────────────
#  Einstiegspunkt
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Map Tile Viewer  v4.0")
    print("  Startort: Muenchen  (Zoom 12)")
    print(f"  Cache: {CACHE_DIR}")
    print("=" * 55)
    MapViewer().mainloop()
