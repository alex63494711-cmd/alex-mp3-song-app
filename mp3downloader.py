import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, subprocess, os, sys, re, shutil, zipfile
import urllib.request, urllib.parse

VERSION    = "3.2"
APP_NAME   = "WaveLoad"
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
ACCENT_L = "#a78bfa"
ACCENT_D = "#6d28d9"
GREEN    = "#10b981"
GREEN_L  = "#34d399"
SPOTIFY  = "#1db954"
TEXT     = "#f1f0ff"
TEXT2    = "#a0a0c0"
TEXT3    = "#5a5a8a"
RED      = "#f87171"
CREATE_NO_WINDOW = 0x08000000

def get_icon_path():
    for p in [os.path.join(BASE_DIR, "icon.ico")]:
        if os.path.exists(p): return p
    return None

def mk_btn(parent, text, cmd, bg=ACCENT, fg=TEXT, hover=ACCENT_L,
           font=("Segoe UI", 10, "bold"), px=16, py=7):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  activebackground=hover, activeforeground=fg,
                  font=font, relief="flat", bd=0, cursor="hand2",
                  padx=px, pady=py)
    b.bind("<Enter>", lambda e, b=b: b.configure(bg=hover))
    b.bind("<Leave>", lambda e, b=b, c=bg: b.configure(bg=c))
    return b

class GlowEntry(tk.Frame):
    def __init__(self, parent, var, accent=ACCENT):
        super().__init__(parent, bg=parent["bg"])
        self._b = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        self._b.pack(fill="x", expand=True)
        self._e = tk.Entry(self._b, textvariable=var, font=("Segoe UI", 10),
                           bg=CARD2, fg=TEXT, insertbackground=TEXT,
                           relief="flat", bd=0)
        self._e.pack(fill="x", ipady=9, ipadx=10)
        self._e.bind("<FocusIn>",  lambda e: self._b.configure(bg=accent))
        self._e.bind("<FocusOut>", lambda e: self._b.configure(bg=BORDER))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.minsize(620, 520)
        self.geometry("700x760")
        self.resizable(True, True)
        self.configure(bg=BG)
        # Outer wrapper auch BG damit Panel-Hintergrund stimmt
        self.update_idletasks()
        self.output_dir  = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        self.quality_var = tk.StringVar(value="0")
        self.url_var     = tk.StringVar()
        self.open_folder = tk.BooleanVar(value=True)
        self.last_file   = None
        self._sy = 0.0
        self._sa = False
        self._dy0 = None
        self._dv0 = None
        self._panel_anim = False
        self._panel_visible = False
        self._panel_alpha = 0.0   # 0.0 = geschlossen, 1.0 = offen
        self._build_ui()
        self.after(100, self._set_icon)
        self.after(400, self._check_tools)
        self.bind("<Control-v>", self._ctrl_v)
        self.bind("<Control-V>", self._ctrl_v)
        self.focus_force()

    def _set_icon(self):
        ico = get_icon_path()
        if ico:
            try: self.iconbitmap(ico)
            except: pass

    def _ctrl_v(self, e=None):
        try:
            c = self.clipboard_get().strip()
            if "spotify.com" in c:
                self.sp_var.set(c)
                self._log("Spotify erkannt – suche...", "accent")
                self.after(300, self._do_spotify_btn)
            elif c.startswith("http"):
                self.url_var.set(c)
                self._log("Link erkannt – lade...", "accent")
                self.after(300, self._start_dl)
        except: pass

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True)

        self._cvs = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        self._cvs.pack(side="left", fill="both", expand=True)

        self._sbc = tk.Canvas(wrap, bg=BG, width=8, highlightthickness=0)
        self._sbc.pack(side="right", fill="y", padx=(0, 2))
        self._th = self._sbc.create_rectangle(1, 2, 7, 50, fill=ACCENT, outline="")

        def _yscroll(first, last):
            try: f, l = float(first), float(last)
            except: return
            h = self._sbc.winfo_height()
            if h < 4: return
            y0 = max(2, int(f * h))
            y1 = min(h - 2, int(l * h))
            if y1 - y0 < 20: y1 = y0 + 20
            self._sbc.coords(self._th, 1, y0, 7, y1)
            self._sbc.configure(width=0 if (f <= 0.0 and l >= 1.0) else 9)

        def _sb_press(e):
            self._dy0 = e.y
            self._dv0 = self._cvs.yview()[0]
        def _sb_drag(e):
            if self._dy0 is None: return
            h = self._sbc.winfo_height()
            if h < 4: return
            pos = max(0.0, min(1.0, self._dv0 + (e.y - self._dy0) / h))
            self._cvs.yview_moveto(pos); self._sy = pos
        def _sb_release(e):
            self._dy0 = None; self._dv0 = None

        self._sbc.bind("<ButtonPress-1>",   _sb_press)
        self._sbc.bind("<B1-Motion>",       _sb_drag)
        self._sbc.bind("<ButtonRelease-1>", _sb_release)
        self._cvs.configure(yscrollcommand=_yscroll)

        self.inner = tk.Frame(self._cvs, bg=BG)
        self._win  = self._cvs.create_window((0, 0), window=self.inner, anchor="nw")
        self._cvs.bind("<Configure>",
            lambda e: self._cvs.itemconfig(self._win, width=e.width))
        self.inner.bind("<Configure>",
            lambda e: self._cvs.configure(scrollregion=self._cvs.bbox("all")))

        def _wheel(e):
            total = self.inner.winfo_reqheight()
            vh    = self._cvs.winfo_height()
            if total <= vh: return
            self._sy = max(0.0, min(1.0, self._sy - (e.delta/120)*80/total))
            if not self._sa: self._smooth()
        self._cvs.bind_all("<MouseWheel>", _wheel)
        self.after(300, lambda: setattr(self, '_sy', self._cvs.yview()[0]))

        self._build_main(self.inner)

        # Settings panel direkt auf Root (kein Canvas-Scroll-Problem)
        # bg=BG damit kein schwarzer Rand sichtbar ist
        self._spanel = tk.Frame(self, bg=CARD2,
                                highlightthickness=1, highlightbackground=ACCENT)
        self._build_settings(self._spanel)

    def _smooth(self):
        self._sa = True
        cur  = self._cvs.yview()[0]
        diff = self._sy - cur
        if abs(diff) < 0.0004:
            self._cvs.yview_moveto(self._sy); self._sa = False; return
        self._cvs.yview_moveto(cur + diff * 0.18)
        self.after(11, self._smooth)

    # ── Settings Panel Animation ──────────────────────────────────────────────
    def _build_settings(self, p):
        # Header
        hdr = tk.Frame(p, bg=CARD2)
        hdr.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(hdr, text="Einstellungen",
                 font=("Segoe UI Black", 15), bg=CARD2, fg=TEXT).pack(side="left")
        mk_btn(hdr, "✕", self._close_settings,
               bg=CARD, fg=TEXT2, hover=RED,
               font=("Segoe UI", 11, "bold"), px=10, py=4
               ).pack(side="right")

        tk.Frame(p, bg=ACCENT, height=1).pack(fill="x", padx=0, pady=(0,4))

        body = tk.Frame(p, bg=CARD2)
        body.pack(fill="both", expand=True, padx=20, pady=(8,20))

        # Ordner
        tk.Label(body, text="Speicherordner",
                 font=("Segoe UI", 10, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,6))
        fr = tk.Frame(body, bg=CARD2); fr.pack(fill="x", pady=(0,18))
        tk.Label(fr, textvariable=self.output_dir,
                 font=("Segoe UI", 9), bg=CARD, fg=TEXT2, anchor="w",
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", fill="x", expand=True, ipady=9, ipadx=10)
        mk_btn(fr, "Auswählen", self._browse,
               font=("Segoe UI", 9, "bold"), px=12, py=7
               ).pack(side="left", padx=(10,0))

        # Qualität
        tk.Label(body, text="Audioqualität",
                 font=("Segoe UI", 10, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,8))
        qr = tk.Frame(body, bg=CARD2); qr.pack(fill="x", pady=(0,18))
        for lbl, val, clr in [
            ("320 kbps  Beste", "0", ACCENT_L),
            ("192 kbps  Gut",   "5", TEXT2),
            ("128 kbps  Normal","9", TEXT3),
        ]:
            f = tk.Frame(qr, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
            f.pack(side="left", padx=(0,8))
            tk.Radiobutton(f, text=lbl, variable=self.quality_var, value=val,
                           bg=CARD, fg=clr, selectcolor=BG,
                           activebackground=CARD, activeforeground=ACCENT_L,
                           font=("Segoe UI", 10), cursor="hand2"
                           ).pack(padx=10, pady=8)

        # Dateimanager
        tk.Label(body, text="Nach Download",
                 font=("Segoe UI", 10, "bold"), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", pady=(0,8))
        tk.Checkbutton(body,
                       text="  Dateimanager öffnen mit Datei markiert",
                       variable=self.open_folder, bg=CARD2, fg=TEXT2,
                       selectcolor=BG, activebackground=CARD2,
                       activeforeground=ACCENT_L,
                       font=("Segoe UI", 10), cursor="hand2"
                       ).pack(anchor="w")

    def _open_settings(self):
        if self._panel_anim or self._panel_visible: return
        self._panel_visible = True
        self._spanel.place(relx=0.5, rely=0.5, anchor="center", width=10, height=10)
        self._spanel.lift()
        self._anim_open(0)

    @staticmethod
    def _ease_out_back(t):
        # Bounce leicht über Ziel hinaus dann zurück
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * ((t - 1) ** 3) + c1 * ((t - 1) ** 2)

    @staticmethod
    def _ease_in_back(t):
        c1 = 1.70158
        c3 = c1 + 1
        return c3 * t * t * t - c1 * t * t

    def _anim_open(self, frame):
        total  = 30          # ~500ms bei 16ms pro Frame
        pw, ph = 500, 400
        if frame > total:
            self._panel_anim = False
            self._spanel.place(relx=0.5, rely=0.5, anchor="center",
                               width=pw, height=ph)
            return
        self._panel_anim = True
        t  = frame / total
        e  = self._ease_out_back(t)
        w  = max(2, int(pw * e))
        h  = max(2, int(ph * e))
        self._spanel.place(relx=0.5, rely=0.5, anchor="center", width=w, height=h)
        self.after(16, lambda: self._anim_open(frame + 1))

    def _close_settings(self):
        if self._panel_anim: return
        self._anim_close(0)

    def _anim_close(self, frame):
        total  = 20          # ~330ms – schneller schließen
        pw, ph = 500, 400
        if frame > total:
            self._panel_anim  = False
            self._panel_visible = False
            self._spanel.place_forget()
            return
        self._panel_anim = True
        t  = frame / total
        e  = self._ease_in_back(t)          # zieht sich kurz auf, dann weg
        e  = max(0.0, 1.0 - e)              # von 1 → 0
        w  = max(2, int(pw * e))
        h  = max(2, int(ph * e))
        self._spanel.place(relx=0.5, rely=0.5, anchor="center", width=w, height=h)
        self.after(16, lambda: self._anim_close(frame + 1))

    # ── Haupt-Inhalt ─────────────────────────────────────────────────────────
    def _build_main(self, p):
        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x", padx=28, pady=(28,0))
        lft = tk.Frame(hdr, bg=BG); lft.pack(side="left")
        tk.Label(lft, text="🎵", font=("Segoe UI", 28), bg=BG, fg=ACCENT
                 ).pack(side="left")
        nf = tk.Frame(lft, bg=BG); nf.pack(side="left", padx=(10,0))
        tk.Label(nf, text=APP_NAME,
                 font=("Segoe UI Black", 22, "bold"), bg=BG, fg=TEXT
                 ).pack(anchor="w")
        tk.Label(nf, text="MP3 Downloader",
                 font=("Segoe UI", 9), bg=BG, fg=TEXT3).pack(anchor="w")

        rgt = tk.Frame(hdr, bg=BG); rgt.pack(side="right", anchor="n", pady=4)
        mk_btn(rgt, "Update", self._check_update,
               bg=CARD2, fg=TEXT2, hover=ACCENT,
               font=("Segoe UI", 9, "bold"), px=12, py=6
               ).pack(side="left", padx=(0,6))
        mk_btn(rgt, "⚙", self._open_settings,
               bg=CARD2, fg=TEXT, hover=ACCENT,
               font=("Segoe UI", 12), px=10, py=5
               ).pack(side="left")
        tk.Label(rgt, text=f"v{VERSION}", font=("Segoe UI", 8),
                 bg=BG, fg=TEXT3).pack(pady=(4,0))

        tk.Label(p, text="  YouTube · SoundCloud · Spotify · Songname  ",
                 font=("Segoe UI", 9), bg=CARD2, fg=TEXT2
                 ).pack(anchor="w", padx=28, pady=(8,18))

        self._sec_url(p)
        self._sec_search(p)
        self._sec_spotify(p)

        df = tk.Frame(p, bg=BG); df.pack(fill="x", padx=28, pady=(10,8))
        self.dl_btn = mk_btn(df, "  MP3 herunterladen", self._start_dl,
                             font=("Segoe UI Black", 13), px=20, py=14)
        self.dl_btn.pack(fill="x")

        self.prog = ttk.Progressbar(p, mode="indeterminate")
        self.prog.pack(fill="x", padx=28, pady=(0,4))

        self.ok_frame = tk.Frame(p, bg="#0d2818",
                                 highlightthickness=1, highlightbackground=GREEN)
        tk.Label(self.ok_frame, text="Download fertig!",
                 font=("Segoe UI Black", 14, "bold"),
                 bg="#0d2818", fg=GREEN_L).pack(pady=(12,2))
        self.ok_path = tk.Label(self.ok_frame, text="",
                                font=("Segoe UI", 9), bg="#0d2818", fg=GREEN)
        self.ok_path.pack(pady=(0,12))

        lf = tk.Frame(p, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="x", padx=28, pady=(6,28))
        lh = tk.Frame(lf, bg=CARD); lh.pack(fill="x", padx=12, pady=(8,0))
        tk.Label(lh, text="●", font=("Segoe UI", 8), bg=CARD, fg=GREEN
                 ).pack(side="left")
        tk.Label(lh, text="  LOG", font=("Segoe UI", 8, "bold"),
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
    def _sec_url(self, p):
        f = self._sec(p, "YouTube / SoundCloud", "Link einfügen oder Strg+V")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", padx=14, pady=(0,12))
        GlowEntry(r, self.url_var).pack(side="left", fill="x", expand=True)
        mk_btn(r, "Einfügen", lambda: self._paste(self.url_var),
               bg=CARD2, fg=TEXT2, hover=ACCENT,
               font=("Segoe UI", 9, "bold"), px=12, py=8
               ).pack(side="left", padx=(8,0))

    def _sec_search(self, p):
        f = self._sec(p, "Song suchen", "Name + Künstler direkt laden")
        r1 = tk.Frame(f, bg=CARD); r1.pack(fill="x", padx=14, pady=(0,6))
        tk.Label(r1, text="Song", font=("Segoe UI", 9), bg=CARD,
                 fg=TEXT3, width=7, anchor="w").pack(side="left")
        self.search_var = tk.StringVar()
        GlowEntry(r1, self.search_var).pack(side="left", fill="x", expand=True)
        r2 = tk.Frame(f, bg=CARD); r2.pack(fill="x", padx=14, pady=(4,12))
        tk.Label(r2, text="Künstler", font=("Segoe UI", 9), bg=CARD,
                 fg=TEXT3, width=7, anchor="w").pack(side="left")
        self.artist_var = tk.StringVar()
        GlowEntry(r2, self.artist_var).pack(side="left", fill="x", expand=True)
        mk_btn(r2, "Suchen & laden", self._search_btn,
               font=("Segoe UI", 9, "bold"), px=12, py=8
               ).pack(side="left", padx=(10,0))

    def _sec_spotify(self, p):
        f = self._sec(p, "Spotify", "Link einfügen, Song wird auf YouTube gesucht")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", padx=14, pady=(0,12))
        self.sp_var = tk.StringVar()
        GlowEntry(r, self.sp_var, accent=SPOTIFY).pack(side="left", fill="x", expand=True)
        mk_btn(r, "Einfügen", lambda: self._paste(self.sp_var),
               bg=CARD2, fg=TEXT2, hover=SPOTIFY,
               font=("Segoe UI", 9), px=10, py=8
               ).pack(side="left", padx=(8,0))
        mk_btn(r, "Laden", self._do_spotify_btn,
               bg=SPOTIFY, fg=TEXT, hover="#17a349",
               font=("Segoe UI", 9, "bold"), px=12, py=8
               ).pack(side="left", padx=(8,0))

    def _sec(self, p, title, sub):
        outer = tk.Frame(p, bg=CARD,
                         highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="x", padx=28, pady=(0,10))
        hdr = tk.Frame(outer, bg=CARD2); hdr.pack(fill="x")
        tk.Label(hdr, text=f"  {title}",
                 font=("Segoe UI", 10, "bold"), bg=CARD2, fg=TEXT
                 ).pack(side="left", pady=8)
        tk.Label(hdr, text=sub, font=("Segoe UI", 9),
                 bg=CARD2, fg=TEXT3).pack(side="left", padx=(4,0))
        tk.Frame(outer, bg=ACCENT, height=1).pack(fill="x")
        return outer

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _paste(self, var):
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

    def _show_ok(self, folder):
        self.ok_path.configure(text=f"  {folder}")
        self.ok_frame.pack(fill="x", padx=28, pady=(8,0), before=self.prog)
        self.after(6000, self._hide_ok)

    def _hide_ok(self):
        try: self.ok_frame.pack_forget()
        except: pass

    def _busy(self, on):
        self.dl_btn.configure(
            state="disabled" if on else "normal",
            text="  Lädt..." if on else "  MP3 herunterladen")
        if on: self.prog.configure(mode="indeterminate"); self.prog.start(12)
        else:  self.prog.stop()

    def _open_explorer(self, fp):
        if self.open_folder.get() and fp and os.path.exists(fp):
            subprocess.Popen(["explorer","/select,",os.path.normpath(fp)],
                             creationflags=CREATE_NO_WINDOW)

    def _yt_search(self, q):
        req = urllib.request.Request(
            "https://www.youtube.com/results?search_query="+urllib.parse.quote(q),
            headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        return f"https://www.youtube.com/watch?v={m.group(1)}" if m else None

    def _search_btn(self):
        s = self.search_var.get().strip()
        if not s:
            messagebox.showwarning("Kein Name","Bitte Songname eingeben!"); return
        a = self.artist_var.get().strip()
        threading.Thread(target=self._search_thread,
                         args=(f"{a} {s}".strip(),), daemon=True).start()

    def _search_thread(self, q):
        self._busy(True)
        try:
            self._log(f"Suche: {q}", "accent")
            url = self._yt_search(q+" official audio")
            if not url:
                self._log("Nichts gefunden.", "red"); return
            self._log(f"Gefunden: {url}", "green")
            self.url_var.set(url)
            self.search_var.set(""); self.artist_var.set("")
            self.after(0, self._start_dl)
        except Exception as e:
            self._log(f"Fehler: {e}", "red")
        finally:
            self._busy(False)

    def _do_spotify_btn(self):
        url = self.sp_var.get().strip()
        if not url or "spotify.com" not in url:
            messagebox.showwarning("Kein Link","Bitte Spotify-Link einfügen!"); return
        threading.Thread(target=self._spotify_thread, args=(url,), daemon=True).start()

    def _spotify_thread(self, surl):
        self._busy(True)
        try:
            self._log("Lese Spotify...", "accent")
            req = urllib.request.Request(surl, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r"<title>(.*?)</title>", html)
            if not m:
                self._log("Titel nicht lesbar.", "red"); return
            name = re.sub(r"\s*[|\-–]\s*Spotify.*$","",m.group(1)).strip()
            self._log(f"Song: {name}", "accent")
            url = self._yt_search(name+" official audio")
            if not url:
                self._log("Kein YouTube-Treffer.", "red"); return
            self._log(f"Gefunden: {url}", "green")
            self.url_var.set(url); self.sp_var.set("")
            self.after(0, self._start_dl)
        except Exception as e:
            self._log(f"Fehler: {e}", "red")
        finally:
            self._busy(False)

    def _check_tools(self):
        missing = [n for n,p in [("yt-dlp",YTDLP_PATH),("ffmpeg",FFMPEG_PATH)]
                   if not os.path.exists(p)]
        if missing:
            self._log(f"Installiere: {', '.join(missing)}...", "accent")
            threading.Thread(target=self._install_tools, daemon=True).start()
        else:
            self._log("Bereit!  Strg+V = sofort herunterladen", "green")

    def _install_tools(self):
        self._busy(True)
        os.makedirs(TOOLS_DIR, exist_ok=True)
        try:
            if not os.path.exists(YTDLP_PATH):
                self._log("yt-dlp wird heruntergeladen...")
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_PATH)
                self._log("yt-dlp OK", "green")
            if not os.path.exists(FFMPEG_PATH):
                self._log("ffmpeg wird heruntergeladen (~80 MB)...")
                zp = os.path.join(TOOLS_DIR,"ffmpeg.zip")
                urllib.request.urlretrieve(FFMPEG_URL, zp)
                self._log("Entpacke ffmpeg...")
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
                self._log("ffmpeg OK", "green")
            self._log("Alles bereit!", "green")
        except Exception as e:
            self._log(f"Fehler: {e}", "red")
        finally:
            self._busy(False)

    def _check_update(self):
        self._log("Suche Updates...", "accent")
        threading.Thread(target=self._update_thread, daemon=True).start()

    def _update_thread(self):
        self._busy(True)
        try:
            req = urllib.request.Request(GITHUB_RAW, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                content = r.read().decode("utf-8")
            m = re.search(r'^VERSION\s*=\s*"([^"]+)"', content, re.MULTILINE)
            nv = m.group(1) if m else VERSION
            if nv == VERSION:
                self._log(f"Aktuell (v{VERSION})", "green")
                self._busy(False); return
            self._log(f"Neue Version v{nv} gefunden!", "accent")
            if IS_EXE:
                self._log("Lade neue EXE...")
                exe = sys.executable; tmp = exe+".new"
                urllib.request.urlretrieve(GITHUB_EXE, tmp)
                bat = os.path.join(BASE_DIR,"_upd.bat")
                with open(bat,"w") as f:
                    f.write(f'@echo off\ntimeout /t 2 /nobreak >nul\n'
                            f'move /y "{tmp}" "{exe}"\nstart "" "{exe}"\ndel "%~f0"\n')
                subprocess.Popen(["cmd","/c",bat], creationflags=CREATE_NO_WINDOW)
                self.after(500, self.destroy)
            else:
                py = os.path.join(BASE_DIR,"mp3downloader.py")
                with open(py,"w",encoding="utf-8") as f: f.write(content)
                self._log(f"v{nv} installiert! Starte neu...", "green")
                self.after(800, lambda: (
                    subprocess.Popen([sys.executable,py],creationflags=CREATE_NO_WINDOW),
                    self.destroy()))
        except Exception as e:
            self._log(f"Update-Fehler: {e}", "red")
        finally:
            self._busy(False)

    def _start_dl(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kein Link","Bitte Link einfügen!"); return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("Tools fehlen","Kurz warten – Tools werden installiert.")
            return
        threading.Thread(target=self._dl_thread, args=(url,), daemon=True).start()

    def _dl_thread(self, url):
        self._busy(True); self._hide_ok(); self.last_file = None
        self._log("Download startet...", "accent")
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
                self._log(f"Fertig!  →  {self.output_dir.get()}", "green")
                self.url_var.set("")
                f, l = self.output_dir.get(), self.last_file
                self.after(0,   lambda: self._show_ok(f))
                self.after(500, lambda: self._open_explorer(l))
            else:
                self._log("Fehlgeschlagen. Link prüfen.", "red")
        except Exception as e:
            self._log(f"Fehler: {e}", "red")
        finally:
            self._busy(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
