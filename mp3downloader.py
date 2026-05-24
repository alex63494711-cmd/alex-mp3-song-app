import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, subprocess, os, sys, re, shutil, zipfile
import urllib.request, urllib.parse

VERSION    = "2.5"
APP_NAME   = "WaveLoad"
APP_SUB    = "MP3 Downloader"
GITHUB_RAW = "https://raw.githubusercontent.com/alex63494711-cmd/alex-mp3-song-app/refs/heads/main/mp3downloader.py"
GITHUB_EXE = "https://github.com/alex63494711-cmd/alex-mp3-song-app/releases/latest/download/WaveLoad.exe"

IS_EXE   = getattr(sys, 'frozen', False)
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if IS_EXE else __file__))
TOOLS_DIR   = os.path.join(BASE_DIR, "tools")
YTDLP_PATH  = os.path.join(TOOLS_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(TOOLS_DIR, "ffmpeg.exe")
YTDLP_URL   = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL  = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

BG       = "#08080f"
CARD     = "#12121e"
CARD2    = "#1a1a2e"
BORDER   = "#2a2a4a"
ACCENT   = "#8b5cf6"
ACCENT_G = "#6d28d9"
ACCENT_L = "#a78bfa"
GREEN    = "#10b981"
GREEN_L  = "#34d399"
SPOTIFY  = "#1db954"
SPOTIFY_L= "#22c55e"
TEXT     = "#f1f0ff"
TEXT2    = "#a0a0c0"
TEXT3    = "#5a5a8a"
RED      = "#f87171"
CREATE_NO_WINDOW = 0x08000000

def get_icon_path():
    for p in [os.path.join(BASE_DIR,"icon.ico"),
              os.path.join(os.path.dirname(os.path.abspath(
                  sys.executable if IS_EXE else __file__)),"icon.ico")]:
        if os.path.exists(p): return p
    return None

def btn(parent, text, cmd, bg=ACCENT, fg=TEXT, hbg=ACCENT_L,
        font=("Segoe UI", 10, "bold"), padx=18, pady=8, **kw):
    """Einfacher flacher Button – kein Canvas, keine Bugs."""
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, activebackground=hbg, activeforeground=fg,
                  font=font, relief="flat", bd=0, cursor="hand2",
                  padx=padx, pady=pady, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=hbg))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b

class GlowEntry(tk.Frame):
    def __init__(self, parent, textvariable, accent=ACCENT, **kw):
        super().__init__(parent, bg=parent["bg"])
        self._border = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        self._border.pack(fill="x", expand=True)
        self._entry = tk.Entry(self._border, textvariable=textvariable,
                               font=("Segoe UI", 10), bg=CARD2, fg=TEXT,
                               insertbackground=TEXT, relief="flat", bd=0)
        self._entry.pack(fill="x", ipady=9, ipadx=10)
        self._entry.bind("<FocusIn>",  lambda e: self._border.configure(bg=accent))
        self._entry.bind("<FocusOut>", lambda e: self._border.configure(bg=BORDER))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.minsize(620, 520)
        self.geometry("700x760")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.output_dir   = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        self.quality_var  = tk.StringVar(value="0")
        self.url_var      = tk.StringVar()
        self.open_folder  = tk.BooleanVar(value=True)
        self.last_file    = None
        self._scroll_y    = 0.0
        self._scroll_anim = False
        self._drag_y0     = None
        self._drag_v0     = None
        self._settings_open = False
        self._build_ui()
        self.after(100, self._set_icon)
        self.after(400, self._check_tools)
        self.bind("<Control-v>", self._on_ctrl_v)
        self.bind("<Control-V>", self._on_ctrl_v)
        self.focus_force()

    def _set_icon(self):
        ico = get_icon_path()
        if ico:
            try: self.iconbitmap(ico)
            except: pass

    def _on_ctrl_v(self, e=None):
        try:
            clip = self.clipboard_get().strip()
            if "spotify.com" in clip:
                self.spotify_var.set(clip)
                self._log("🟢 Spotify erkannt – suche...", "accent")
                self.after(300, self._spotify_to_yt)
            elif clip.startswith("http"):
                self.url_var.set(clip)
                self._log("📋 Link erkannt – starte Download...", "accent")
                self.after(300, self._start_download)
        except: pass

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._main = tk.Frame(self, bg=BG)
        self._main.pack(fill="both", expand=True)

        self._cvs = tk.Canvas(self._main, bg=BG, highlightthickness=0)
        self._cvs.pack(side="left", fill="both", expand=True)

        self._sbc = tk.Canvas(self._main, bg=BG, width=8, highlightthickness=0)
        self._sbc.pack(side="right", fill="y", padx=(0,2))
        self._thumb = self._sbc.create_rectangle(1, 0, 7, 50,
                      fill=ACCENT, outline="")

        def _yscroll(first, last):
            try: f, l = float(first), float(last)
            except: return
            h = self._sbc.winfo_height()
            if h < 4: return
            y0 = max(2, int(f*h))
            y1 = min(h-2, int(l*h))
            if y1-y0 < 24: y1 = y0+24
            self._sbc.coords(self._thumb, 1, y0, 7, y1)
            self._sbc.configure(width=0 if f<=0.0 and l>=1.0 else 9)

        self._cvs.configure(yscrollcommand=_yscroll)

        def _sb_press(e):
            self._drag_y0 = e.y
            self._drag_v0 = self._cvs.yview()[0]
        def _sb_motion(e):
            if self._drag_y0 is None: return
            h = self._sbc.winfo_height()
            if h < 4: return
            delta = (e.y - self._drag_y0) / h
            pos = max(0.0, min(1.0, self._drag_v0 + delta))
            self._cvs.yview_moveto(pos)
            self._scroll_y = pos
        def _sb_release(e):
            self._drag_y0 = None; self._drag_v0 = None

        self._sbc.bind("<ButtonPress-1>",   _sb_press)
        self._sbc.bind("<B1-Motion>",       _sb_motion)
        self._sbc.bind("<ButtonRelease-1>", _sb_release)

        self.inner = tk.Frame(self._cvs, bg=BG)
        self._win  = self._cvs.create_window((0,0), window=self.inner, anchor="nw")
        self._cvs.bind("<Configure>",
            lambda e: self._cvs.itemconfig(self._win, width=e.width))
        self.inner.bind("<Configure>",
            lambda e: self._cvs.configure(scrollregion=self._cvs.bbox("all")))

        def _mwheel(e):
            total = self.inner.winfo_reqheight()
            view  = self._cvs.winfo_height()
            if total <= view: return
            step = (e.delta/120)*80/total
            self._scroll_y = max(0.0, min(1.0, self._scroll_y - step))
            if not self._scroll_anim: self._smooth(self._cvs)
        self._cvs.bind_all("<MouseWheel>", _mwheel)
        self.after(300, lambda: setattr(self,'_scroll_y', self._cvs.yview()[0]))

        self._build_content(self.inner)

        # Einstellungen-Panel (unsichtbar über allem)
        self._spanel = tk.Frame(self, bg=CARD2,
            highlightthickness=1, highlightbackground=ACCENT)
        self._build_settings(self._spanel)

    def _smooth(self, cvs):
        self._scroll_anim = True
        cur  = cvs.yview()[0]
        diff = self._scroll_y - cur
        if abs(diff) < 0.0004:
            cvs.yview_moveto(self._scroll_y)
            self._scroll_anim = False; return
        cvs.yview_moveto(cur + diff*0.18)
        self.after(11, lambda: self._smooth(cvs))

    # ── Einstellungen Panel ───────────────────────────────────────────────────
    def _build_settings(self, panel):
        hdr = tk.Frame(panel, bg=CARD2)
        hdr.pack(fill="x", padx=20, pady=(16,8))
        tk.Label(hdr, text="⚙️  Einstellungen",
                 font=("Segoe UI Black", 14, "bold"), bg=CARD2, fg=TEXT
                 ).pack(side="left")
        btn(hdr, "✕  Schließen", self._toggle_settings,
            bg=CARD, fg=TEXT2, hbg=RED,
            font=("Segoe UI", 9, "bold"), padx=12, pady=6
            ).pack(side="right")

        tk.Frame(panel, bg=ACCENT, height=1).pack(fill="x")

        body = tk.Frame(panel, bg=CARD2)
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Speicherordner
        tk.Label(body, text="📁  Speicherordner",
                 font=("Segoe UI", 11, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,6))
        row = tk.Frame(body, bg=CARD2); row.pack(fill="x", pady=(0,20))
        tk.Label(row, textvariable=self.output_dir,
                 font=("Segoe UI", 9), bg=CARD, fg=TEXT2, anchor="w",
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", fill="x", expand=True, ipady=10, ipadx=10)
        btn(row, "📂  Auswählen", self._browse,
            bg=ACCENT, fg=TEXT, hbg=ACCENT_L,
            font=("Segoe UI", 9, "bold"), padx=12, pady=8
            ).pack(side="left", padx=(10,0))

        # Qualität
        tk.Label(body, text="🎚️  Audioqualität",
                 font=("Segoe UI", 11, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,8))
        qrow = tk.Frame(body, bg=CARD2); qrow.pack(fill="x", pady=(0,20))
        for label, val, clr in [
            ("🔥  320 kbps  Beste",  "0", ACCENT_L),
            ("👍  192 kbps  Gut",    "5", TEXT2),
            ("📉  128 kbps  Normal", "9", TEXT3),
        ]:
            f = tk.Frame(qrow, bg=CARD, highlightthickness=1,
                         highlightbackground=BORDER)
            f.pack(side="left", padx=(0,8))
            tk.Radiobutton(f, text=label, variable=self.quality_var, value=val,
                           bg=CARD, fg=clr, selectcolor=BG,
                           activebackground=CARD, activeforeground=ACCENT_L,
                           font=("Segoe UI", 10), cursor="hand2"
                           ).pack(padx=10, pady=8)

        # Dateimanager
        tk.Label(body, text="🗂️  Nach Download",
                 font=("Segoe UI", 11, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,8))
        tk.Checkbutton(body,
            text="  Dateimanager öffnen mit Datei markiert",
            variable=self.open_folder, bg=CARD2, fg=TEXT2, selectcolor=BG,
            activebackground=CARD2, activeforeground=ACCENT_L,
            font=("Segoe UI", 10), cursor="hand2"
            ).pack(anchor="w")

    def _toggle_settings(self):
        self._settings_open = not self._settings_open
        if self._settings_open:
            self._spanel.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            self._spanel.lift()
        else:
            self._spanel.place_forget()

    # ── Hauptinhalt ──────────────────────────────────────────────────────────
    def _build_content(self, p):
        # Header
        hdr = tk.Frame(p, bg=BG); hdr.pack(fill="x", padx=28, pady=(28,0))
        left = tk.Frame(hdr, bg=BG); left.pack(side="left")
        tk.Label(left, text="🎵", font=("Segoe UI", 30), bg=BG, fg=ACCENT
                 ).pack(side="left")
        nf = tk.Frame(left, bg=BG); nf.pack(side="left", padx=(10,0))
        tk.Label(nf, text=APP_NAME,
                 font=("Segoe UI Black", 24, "bold"), bg=BG, fg=TEXT
                 ).pack(anchor="w")
        tk.Label(nf, text=APP_SUB,
                 font=("Segoe UI", 9), bg=BG, fg=TEXT3).pack(anchor="w")

        # Buttons oben rechts
        right = tk.Frame(hdr, bg=BG); right.pack(side="right", anchor="n", pady=4)
        btn(right, "🔄  Update", self._check_update,
            bg=CARD2, fg=TEXT2, hbg=ACCENT,
            font=("Segoe UI", 9, "bold"), padx=12, pady=6
            ).pack(side="left", padx=(0,8))
        btn(right, "⚙️", self._toggle_settings,
            bg=CARD2, fg=TEXT, hbg=ACCENT,
            font=("Segoe UI", 13), padx=10, pady=5
            ).pack(side="left")
        tk.Label(right, text=f"v{VERSION}", font=("Segoe UI", 8),
                 bg=BG, fg=TEXT3).pack(side="left", padx=(8,0), pady=(6,0))

        tk.Label(p, text="  YouTube · SoundCloud · Spotify · Songname  ",
                 font=("Segoe UI", 9), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", padx=28, pady=(6,18))

        self._section_url(p)
        self._section_search(p)
        self._section_spotify(p)

        # Download Button
        dl_outer = tk.Frame(p, bg=BG); dl_outer.pack(fill="x", padx=28, pady=(10,10))
        self.dl_btn = btn(dl_outer, "⬇   MP3 herunterladen", self._start_download,
                          bg=ACCENT, fg=TEXT, hbg=ACCENT_L,
                          font=("Segoe UI Black", 13), padx=0, pady=14)
        self.dl_btn.pack(fill="x")

        # Progressbar
        style = ttk.Style(); style.theme_use("default")
        style.configure("W.TProgressbar", troughcolor=CARD, background=ACCENT, thickness=3)
        self.prog = ttk.Progressbar(p, style="W.TProgressbar", mode="indeterminate")
        self.prog.pack(fill="x", padx=28)

        # Erfolgs-Banner
        self.ok_frame = tk.Frame(p, bg="#0d2818",
                                 highlightthickness=1, highlightbackground=GREEN)
        tk.Label(self.ok_frame, text="✅  Download fertig!",
                 font=("Segoe UI Black", 14, "bold"), bg="#0d2818", fg=GREEN_L
                 ).pack(pady=(12,2))
        self.ok_path = tk.Label(self.ok_frame, text="",
                                font=("Segoe UI", 9), bg="#0d2818", fg=GREEN)
        self.ok_path.pack(pady=(0,12))

        # Log
        lf = tk.Frame(p, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="x", padx=28, pady=(10,28))
        lhdr = tk.Frame(lf, bg=CARD); lhdr.pack(fill="x", padx=12, pady=(8,0))
        tk.Label(lhdr, text="●", font=("Segoe UI", 8), bg=CARD, fg=GREEN
                 ).pack(side="left")
        tk.Label(lhdr, text="  LOG", font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=TEXT3).pack(side="left")
        self.log = tk.Text(lf, bg=CARD, fg=TEXT2, font=("Consolas", 9),
                           relief="flat", bd=0, height=6,
                           insertbackground=ACCENT, wrap="word", state="disabled")
        self.log.pack(fill="x", padx=12, pady=(4,10))
        self.log.tag_configure("green",  foreground=GREEN_L)
        self.log.tag_configure("red",    foreground=RED)
        self.log.tag_configure("accent", foreground=ACCENT_L)
        self.log.tag_configure("normal", foreground=TEXT2)

    # ── Sections ─────────────────────────────────────────────────────────────
    def _section_url(self, p):
        f = self._section(p, "🔗", "YouTube / SoundCloud", "Link einfügen oder Strg+V")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=14, pady=(0,12))
        GlowEntry(row, self.url_var).pack(side="left", fill="x", expand=True)
        btn(row, "📋 Einfügen", lambda: self._paste_to(self.url_var),
            bg=CARD2, fg=TEXT2, hbg=ACCENT,
            font=("Segoe UI", 9), padx=12, pady=8
            ).pack(side="left", padx=(8,0))

    def _section_search(self, p):
        f = self._section(p, "🔍", "Song suchen", "Name + Künstler → direkt laden")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=14, pady=(0,6))
        tk.Label(row, text="Song", font=("Segoe UI", 9),
                 bg=CARD, fg=TEXT3, width=7, anchor="w").pack(side="left")
        self.search_var = tk.StringVar()
        GlowEntry(row, self.search_var).pack(side="left", fill="x", expand=True)
        row2 = tk.Frame(f, bg=CARD); row2.pack(fill="x", padx=14, pady=(6,12))
        tk.Label(row2, text="Künstler", font=("Segoe UI", 9),
                 bg=CARD, fg=TEXT3, width=7, anchor="w").pack(side="left")
        self.artist_var = tk.StringVar()
        GlowEntry(row2, self.artist_var).pack(side="left", fill="x", expand=True)
        btn(row2, "🔍 Suchen & laden", self._search_by_name,
            bg=ACCENT, fg=TEXT, hbg=ACCENT_L,
            font=("Segoe UI", 9, "bold"), padx=12, pady=8
            ).pack(side="left", padx=(10,0))

    def _section_spotify(self, p):
        f = self._section(p, "🟢", "Spotify", "Link einfügen → findet Song auf YouTube")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=14, pady=(0,12))
        self.spotify_var = tk.StringVar()
        GlowEntry(row, self.spotify_var, accent=SPOTIFY
                  ).pack(side="left", fill="x", expand=True)
        btn(row, "📋 Einfügen", lambda: self._paste_to(self.spotify_var),
            bg=CARD2, fg=TEXT2, hbg=SPOTIFY,
            font=("Segoe UI", 9), padx=12, pady=8
            ).pack(side="left", padx=(8,0))
        btn(row, "🎵 Laden", self._spotify_to_yt,
            bg=SPOTIFY, fg=TEXT, hbg=SPOTIFY_L,
            font=("Segoe UI", 9, "bold"), padx=12, pady=8
            ).pack(side="left", padx=(8,0))

    def _section(self, parent, icon, title, subtitle):
        outer = tk.Frame(parent, bg=CARD,
                         highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="x", padx=28, pady=(0,10))
        hdr = tk.Frame(outer, bg=CARD2); hdr.pack(fill="x")
        tk.Label(hdr, text=f"  {icon}  {title}",
                 font=("Segoe UI", 10, "bold"), bg=CARD2, fg=TEXT
                 ).pack(side="left", pady=8)
        if subtitle:
            tk.Label(hdr, text=subtitle, font=("Segoe UI", 9),
                     bg=CARD2, fg=TEXT3).pack(side="left", padx=(4,0))
        tk.Frame(outer, bg=ACCENT, height=1).pack(fill="x")
        return outer

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _paste_to(self, var):
        try: var.set(self.clipboard_get().strip())
        except: pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get())
        if d: self.output_dir.set(d)

    def _log(self, msg, tag="normal"):
        self.log.configure(state="normal")
        self.log.insert("end", msg+"\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_success(self, folder):
        self.ok_path.configure(text=f"📁  {folder}")
        self.ok_frame.pack(fill="x", padx=28, pady=(8,0), before=self.prog)
        self.after(6000, self._hide_success)

    def _hide_success(self):
        try: self.ok_frame.pack_forget()
        except: pass

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.dl_btn.configure(state=state,
            text="⏳  Lädt..." if busy else "⬇   MP3 herunterladen")
        if busy: self.prog.configure(mode="indeterminate"); self.prog.start(12)
        else:    self.prog.stop()

    def _open_in_explorer(self, fp):
        if self.open_folder.get() and fp and os.path.exists(fp):
            subprocess.Popen(["explorer","/select,",os.path.normpath(fp)],
                             creationflags=CREATE_NO_WINDOW)

    def _youtube_search(self, query):
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        return f"https://www.youtube.com/watch?v={m.group(1)}" if m else None

    # ── Song suchen ──────────────────────────────────────────────────────────
    def _search_by_name(self):
        song = self.search_var.get().strip()
        if not song:
            messagebox.showwarning("Kein Name","Bitte Songname eingeben!"); return
        artist = self.artist_var.get().strip()
        threading.Thread(target=self._do_search,
                         args=(f"{artist} {song}".strip(),), daemon=True).start()

    def _do_search(self, query):
        self._set_busy(True)
        try:
            self._log(f"🔍 Suche: {query}", "accent")
            url = self._youtube_search(query + " official audio")
            if not url:
                self._log("❌ Nichts gefunden.", "red"); return
            self._log(f"✅ {url}", "green")
            self.url_var.set(url)
            self.search_var.set(""); self.artist_var.set("")
            self.after(0, self._start_download)
        except Exception as e:
            self._log(f"❌ {e}", "red")
        finally:
            self._set_busy(False)

    # ── Spotify ──────────────────────────────────────────────────────────────
    def _spotify_to_yt(self):
        url = self.spotify_var.get().strip()
        if not url or "spotify.com" not in url:
            messagebox.showwarning("Kein Link","Bitte Spotify-Link einfügen!"); return
        threading.Thread(target=self._do_spotify, args=(url,), daemon=True).start()

    def _do_spotify(self, surl):
        self._set_busy(True)
        try:
            self._log("🟢 Lese Spotify...", "accent")
            req = urllib.request.Request(surl, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r"<title>(.*?)</title>", html)
            if not m:
                self._log("❌ Titel nicht lesbar.", "red"); return
            name = re.sub(r"\s*[|\-–]\s*Spotify.*$","",m.group(1)).strip()
            self._log(f"🎵 Song: {name}", "accent")
            url = self._youtube_search(name + " official audio")
            if not url:
                self._log("❌ Kein YouTube-Treffer.", "red"); return
            self._log(f"✅ {url}", "green")
            self.url_var.set(url); self.spotify_var.set("")
            self.after(0, self._start_download)
        except Exception as e:
            self._log(f"❌ {e}", "red")
        finally:
            self._set_busy(False)

    # ── Tools ────────────────────────────────────────────────────────────────
    def _check_tools(self):
        missing = [t for t,p in [("yt-dlp",YTDLP_PATH),("ffmpeg",FFMPEG_PATH)]
                   if not os.path.exists(p)]
        if missing:
            self._log(f"⚙  Installiere: {', '.join(missing)}...", "accent")
            threading.Thread(target=self._install_tools, daemon=True).start()
        else:
            self._log("✅ Bereit!  Strg+V = sofort herunterladen", "green")

    def _install_tools(self):
        self._set_busy(True)
        os.makedirs(TOOLS_DIR, exist_ok=True)
        try:
            if not os.path.exists(YTDLP_PATH):
                self._log("⬇  yt-dlp...")
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_PATH)
                self._log("✅ yt-dlp OK", "green")
            if not os.path.exists(FFMPEG_PATH):
                self._log("⬇  ffmpeg (~80 MB)...")
                zp = os.path.join(TOOLS_DIR,"ffmpeg.zip")
                urllib.request.urlretrieve(FFMPEG_URL, zp)
                self._log("📦 Entpacke...")
                with zipfile.ZipFile(zp) as z:
                    for m in z.namelist():
                        if m.endswith("ffmpeg.exe"):
                            z.extract(m, TOOLS_DIR)
                            shutil.move(os.path.join(TOOLS_DIR,m), FFMPEG_PATH)
                            break
                os.remove(zp)
                for d in os.listdir(TOOLS_DIR):
                    dp = os.path.join(TOOLS_DIR,d)
                    if os.path.isdir(dp): shutil.rmtree(dp,ignore_errors=True)
                self._log("✅ ffmpeg OK", "green")
            self._log("🎉 Alles bereit!", "green")
        except Exception as e:
            self._log(f"❌ {e}", "red")
        finally:
            self._set_busy(False)

    # ── Update ───────────────────────────────────────────────────────────────
    def _check_update(self):
        self._log("🔄 Suche Updates...", "accent")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        self._set_busy(True)
        try:
            req = urllib.request.Request(GITHUB_RAW, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                content = r.read().decode("utf-8")
            m = re.search(r'^VERSION\s*=\s*"([^"]+)"', content, re.MULTILINE)
            new_ver = m.group(1) if m else VERSION
            if new_ver == VERSION:
                self._log(f"✅ Aktuell (v{VERSION})", "green")
                self._set_busy(False); return
            self._log(f"🆕 v{new_ver} verfügbar!", "accent")
            if IS_EXE:
                self._log("⬇  Lade neue EXE...")
                exe = sys.executable; tmp = exe+".new"
                urllib.request.urlretrieve(GITHUB_EXE, tmp)
                bat = os.path.join(BASE_DIR,"_upd.bat")
                with open(bat,"w") as f:
                    f.write(f'@echo off\ntimeout /t 2 /nobreak >nul\nmove /y "{tmp}" "{exe}"\nstart "" "{exe}"\ndel "%~f0"\n')
                subprocess.Popen(["cmd","/c",bat], creationflags=CREATE_NO_WINDOW)
                self.after(500, self.destroy)
            else:
                py = os.path.join(BASE_DIR,"mp3downloader.py")
                with open(py,"w",encoding="utf-8") as f: f.write(content)
                self._log(f"✅ v{new_ver} installiert!", "green")
                self.after(800, lambda: (
                    subprocess.Popen([sys.executable, py], creationflags=CREATE_NO_WINDOW),
                    self.destroy()))
        except Exception as e:
            self._log(f"❌ {e}", "red")
        finally:
            self._set_busy(False)

    # ── Download ─────────────────────────────────────────────────────────────
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kein Link","Bitte Link einfügen!"); return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("Tools fehlen","Kurz warten – Tools werden installiert.")
            return
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        self._set_busy(True)
        self._hide_success()
        self.last_file = None
        self._log("\n▶  Download startet...", "accent")
        out = os.path.join(self.output_dir.get(),"%(title)s.%(ext)s")
        cmd = [YTDLP_PATH,"-x","--audio-format","mp3",
               "--audio-quality",self.quality_var.get(),
               "--ffmpeg-location",TOOLS_DIR,
               "-o",out,"--no-playlist",
               "--print","after_move:filepath",url]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace",
                                    creationflags=CREATE_NO_WINDOW)
            for line in proc.stdout:
                line = line.rstrip()
                if not line: continue
                if os.path.sep in line and line.endswith(".mp3"):
                    self.last_file = line.strip()
                else:
                    self._log(line)
            proc.wait()
            if proc.returncode == 0:
                self._log(f"\n✅ Fertig!  →  {self.output_dir.get()}", "green")
                self.url_var.set("")
                folder, last = self.output_dir.get(), self.last_file
                self.after(0,   lambda: self._show_success(folder))
                self.after(500, lambda: self._open_in_explorer(last))
            else:
                self._log("❌ Fehlgeschlagen. Link prüfen.", "red")
        except Exception as e:
            self._log(f"❌ {e}", "red")
        finally:
            self._set_busy(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
