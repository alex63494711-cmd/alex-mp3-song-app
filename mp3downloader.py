import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess
import os, sys, re, shutil, zipfile
import urllib.request, urllib.parse

VERSION    = "2.1"
APP_NAME   = "MP3 Song App"
GITHUB_RAW = "https://raw.githubusercontent.com/alex63494711-cmd/alex-mp3-song-app/refs/heads/main/mp3downloader.py"
GITHUB_EXE = "https://github.com/alex63494711-cmd/alex-mp3-song-app/releases/latest/download/MP3-Song-App.exe"

IS_EXE   = getattr(sys, 'frozen', False)
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if IS_EXE else __file__))
TOOLS_DIR   = os.path.join(BASE_DIR, "tools")
YTDLP_PATH  = os.path.join(TOOLS_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(TOOLS_DIR, "ffmpeg.exe")
YTDLP_URL   = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL  = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

BG          = "#0d0d12"
CARD        = "#16161f"
ACCENT      = "#a855f7"
ACCENT2     = "#c084fc"
TEXT        = "#f0f0f5"
SUBTEXT     = "#66667a"
BORDER      = "#222230"
BTN_SEC     = "#1e1e2a"
SUCCESS     = "#22c55e"
SUCCESS_DIM = "#14532d"
SPOTIFY_CLR = "#1db954"
CREATE_NO_WINDOW = 0x08000000

def get_icon_path():
    for p in [
        os.path.join(BASE_DIR, "icon.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
    ]:
        if os.path.exists(p): return p
    return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{VERSION}")
        self.minsize(600, 500)
        self.geometry("660x750")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.output_dir  = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        self.quality_var = tk.StringVar(value="0")
        self.url_var     = tk.StringVar()
        self.open_folder = tk.BooleanVar(value=True)
        self.last_file   = None
        self._scroll_target   = 0.0
        self._scroll_animating = False
        self._build_ui()
        self.after(100, self._set_icon)
        self.after(300, self._check_tools)
        self.bind("<Control-v>", self._on_ctrl_v)
        self.bind("<Control-V>", self._on_ctrl_v)
        self.focus_force()

    def _set_icon(self):
        ico = get_icon_path()
        if ico:
            try: self.iconbitmap(ico)
            except: pass

    def _on_ctrl_v(self, event=None):
        try:
            clip = self.clipboard_get().strip()
            if "spotify.com" in clip:
                self.spotify_var.set(clip)
                self._log("🎵 Spotify-Link erkannt – suche auf YouTube...")
                self.after(300, self._spotify_to_yt)
            elif clip.startswith("http"):
                self.url_var.set(clip)
                self._log("📋 Link eingefügt – starte Download...")
                self.after(300, self._start_download)
        except: pass

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._sb_canvas = tk.Canvas(outer, bg=BG, width=10, highlightthickness=0)
        self._sb_canvas.pack(side="right", fill="y")
        self._sb_thumb = self._sb_canvas.create_rectangle(2, 0, 8, 40,
                         fill=ACCENT, outline="", width=0)

        def _update_thumb(*args):
            try: first, last = float(args[0]), float(args[1])
            except: return
            h = self._sb_canvas.winfo_height()
            if h < 2: return
            y0, y1 = int(first*h), int(last*h)
            if y1-y0 < 20: y1 = y0+20
            self._sb_canvas.coords(self._sb_thumb, 2, y0+2, 8, y1-2)
            self._sb_canvas.configure(width=0 if first<=0.0 and last>=1.0 else 10)

        def _sb_click(e):
            h = self._sb_canvas.winfo_height()
            if h >= 2: self._canvas.yview_moveto(e.y / h)
        self._sb_canvas.bind("<Button-1>", _sb_click)
        self._sb_canvas.bind("<B1-Motion>", _sb_click)
        canvas = self._canvas
        canvas.configure(yscrollcommand=_update_thumb)

        self.inner = tk.Frame(canvas, bg=BG)
        self.inner_id = canvas.create_window((0,0), window=self.inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.inner_id, width=e.width))
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            total_h = self.inner.winfo_reqheight()
            view_h  = canvas.winfo_height()
            if total_h <= view_h: return
            step = (e.delta/120)*60/total_h
            self._scroll_target = max(0.0, min(1.0, self._scroll_target - step))
            if not self._scroll_animating:
                self._animate_scroll(canvas)
        canvas.bind_all("<MouseWheel>", _scroll)
        self.after(200, lambda: setattr(self, '_scroll_target', canvas.yview()[0]))
        self._build_content(self.inner)

    def _animate_scroll(self, canvas):
        self._scroll_animating = True
        curr = canvas.yview()[0]
        diff = self._scroll_target - curr
        if abs(diff) < 0.0005:
            canvas.yview_moveto(self._scroll_target)
            self._scroll_animating = False
            return
        canvas.yview_moveto(curr + diff * 0.2)
        self.after(12, lambda: self._animate_scroll(canvas))

    def _build_content(self, p):
        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20,0))
        tk.Label(hdr, text="🎵 MP3 Song App", font=("Segoe UI Black", 20, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.upd_btn = tk.Button(hdr, text="🔄 Update", font=("Segoe UI", 9, "bold"),
                                 bg=BTN_SEC, fg=SUBTEXT,
                                 activebackground=ACCENT, activeforeground="white",
                                 relief="flat", cursor="hand2", bd=0,
                                 command=self._check_update)
        self.upd_btn.pack(side="right", ipadx=10, ipady=5)
        tk.Label(p, text=f"v{VERSION}  –  YouTube · SoundCloud · Spotify · Songname",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w", padx=24, pady=(2,12))

        self._card_url(p)
        self._card_search(p)
        self._card_spotify(p)
        self._card_folder(p)
        self._card_quality(p)
        self._card_settings(p)

        self.dl_btn = tk.Button(p, text="⬇   MP3 herunterladen",
                                font=("Segoe UI", 12, "bold"),
                                bg=ACCENT, fg="white", activebackground=ACCENT2,
                                activeforeground="white", relief="flat",
                                cursor="hand2", height=2, command=self._start_download)
        self.dl_btn.pack(fill="x", padx=24, pady=(6,8))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=CARD, background=ACCENT, thickness=4)
        self.prog = ttk.Progressbar(p, style="TProgressbar", mode="indeterminate")
        self.prog.pack(fill="x", padx=24)

        self.success_frame = tk.Frame(p, bg=SUCCESS_DIM,
                                      highlightthickness=1, highlightbackground=SUCCESS)
        tk.Label(self.success_frame, text="✅  Download fertig!",
                 font=("Segoe UI Black", 14, "bold"), bg=SUCCESS_DIM, fg=SUCCESS).pack(pady=(10,2))
        self.success_path = tk.Label(self.success_frame, text="",
                                     font=("Segoe UI", 9), bg=SUCCESS_DIM, fg=SUCCESS)
        self.success_path.pack(pady=(0,10))

        lf = tk.Frame(p, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="x", padx=24, pady=(10,20))
        tk.Label(lf, text="LOG", font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=10, pady=(6,0))
        self.log = tk.Text(lf, bg=CARD, fg=TEXT, font=("Consolas", 9),
                           relief="flat", bd=0, height=6,
                           insertbackground=ACCENT, wrap="word", state="disabled")
        self.log.pack(fill="x", padx=10, pady=(2,8))
        self.log.tag_configure("green",   foreground=SUCCESS)
        self.log.tag_configure("red",     foreground="#f87171")
        self.log.tag_configure("normal",  foreground=TEXT)
        self.log.tag_configure("spotify", foreground=SPOTIFY_CLR)

    # ── Karten ───────────────────────────────────────────────────────────────
    def _card_url(self, p):
        f = self._card(p, "🔗  YouTube / SoundCloud Link  (oder Strg+V)")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,10))
        tk.Entry(row, textvariable=self.url_var, font=("Segoe UI", 10),
                 bg="#0f0f18", fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        tk.Button(row, text="📋", font=("Segoe UI", 10), bg=BTN_SEC, fg=TEXT,
                  activebackground=ACCENT, activeforeground="white", relief="flat",
                  cursor="hand2", command=lambda: self._paste_to(self.url_var)
                  ).pack(side="left", padx=(5,0), ipady=5, ipadx=8)

    def _card_search(self, p):
        f = self._card(p, "🔍  Songname + Künstler → automatisch suchen & laden")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,6))
        tk.Label(row, text="Song:", font=("Segoe UI", 9), bg=CARD, fg=SUBTEXT, width=7).pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(row, textvariable=self.search_var, font=("Segoe UI", 10),
                 bg="#0f0f18", fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        row2 = tk.Frame(f, bg=CARD); row2.pack(fill="x", padx=12, pady=(4,10))
        tk.Label(row2, text="Künstler:", font=("Segoe UI", 9), bg=CARD, fg=SUBTEXT, width=7).pack(side="left")
        self.artist_var = tk.StringVar()
        tk.Entry(row2, textvariable=self.artist_var, font=("Segoe UI", 10),
                 bg="#0f0f18", fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        tk.Button(row2, text="🔍 Suchen & laden", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", activebackground=ACCENT2, activeforeground="white",
                  relief="flat", cursor="hand2", command=self._search_by_name
                  ).pack(side="left", padx=(8,0), ipady=5, ipadx=12)

    def _card_spotify(self, p):
        f = self._card(p, "🟢  Spotify-Link → findet Song auf YouTube & lädt ihn")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,10))
        self.spotify_var = tk.StringVar()
        tk.Entry(row, textvariable=self.spotify_var, font=("Segoe UI", 10),
                 bg="#0f0f18", fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=SPOTIFY_CLR
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        tk.Button(row, text="📋", font=("Segoe UI", 10), bg=BTN_SEC, fg=TEXT,
                  activebackground=SPOTIFY_CLR, activeforeground="white", relief="flat",
                  cursor="hand2", command=lambda: self._paste_to(self.spotify_var)
                  ).pack(side="left", padx=(5,0), ipady=5, ipadx=8)
        tk.Button(row, text="🎵 Laden", font=("Segoe UI", 10, "bold"),
                  bg=SPOTIFY_CLR, fg="white", activebackground="#17a349",
                  activeforeground="white", relief="flat", cursor="hand2",
                  command=self._spotify_to_yt
                  ).pack(side="left", padx=(5,0), ipady=5, ipadx=12)

    def _card_folder(self, p):
        f = self._card(p, "📁  Speicherordner")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,10))
        tk.Label(row, textvariable=self.output_dir, font=("Segoe UI", 9),
                 bg="#0f0f18", fg=TEXT, anchor="w",
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        tk.Button(row, text="Auswählen", font=("Segoe UI", 9), bg=BTN_SEC, fg=TEXT,
                  activebackground=ACCENT, activeforeground="white", relief="flat",
                  cursor="hand2", command=self._browse
                  ).pack(side="left", padx=(6,0), ipady=5, ipadx=10)

    def _card_quality(self, p):
        f = self._card(p, "🎚️  Qualität")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,10))
        for label, val in [("Beste (320kbps)","0"),("Gut (192kbps)","5"),("Normal (128kbps)","9")]:
            tk.Radiobutton(row, text=label, variable=self.quality_var, value=val,
                           bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                           activeforeground=ACCENT, font=("Segoe UI", 10), cursor="hand2"
                           ).pack(side="left", padx=(0,16))

    def _card_settings(self, p):
        f = self._card(p, "⚙️  Einstellungen")
        row = tk.Frame(f, bg=CARD); row.pack(fill="x", padx=12, pady=(0,10))
        tk.Checkbutton(row, text="📂  Dateimanager nach Download öffnen (Datei markiert)",
                       variable=self.open_folder, bg=CARD, fg=TEXT, selectcolor=BG,
                       activebackground=CARD, activeforeground=ACCENT,
                       font=("Segoe UI", 10), cursor="hand2").pack(anchor="w")

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        f.pack(fill="x", padx=24, pady=(0,8))
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=12, pady=(8,4))
        return f

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
        self.success_path.configure(text=f"📁  {folder}")
        self.success_frame.pack(fill="x", padx=24, pady=(8,0), before=self.prog)
        self.after(6000, self._hide_success)

    def _hide_success(self):
        self.success_frame.pack_forget()

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.dl_btn.configure(state=state,
                              text="⏳  Lädt..." if busy else "⬇   MP3 herunterladen")
        self.upd_btn.configure(state=state)
        if busy: self.prog.configure(mode="indeterminate"); self.prog.start(12)
        else:    self.prog.stop()

    def _open_in_explorer(self, filepath):
        if self.open_folder.get() and filepath and os.path.exists(filepath):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(filepath)],
                             creationflags=CREATE_NO_WINDOW)

    def _youtube_search(self, query):
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://www.youtube.com/results?search_query={q}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        return f"https://www.youtube.com/watch?v={m.group(1)}" if m else None

    # ── Songname suchen ──────────────────────────────────────────────────────
    def _search_by_name(self):
        song   = self.search_var.get().strip()
        artist = self.artist_var.get().strip()
        if not song:
            messagebox.showwarning("Kein Songname", "Bitte einen Songnamen eingeben!")
            return
        query = f"{artist} {song}".strip() if artist else song
        threading.Thread(target=self._do_name_search, args=(query,), daemon=True).start()

    def _do_name_search(self, query):
        self._set_busy(True)
        try:
            self._log(f"🔍 Suche: {query}")
            yt_url = self._youtube_search(query + " official audio")
            if not yt_url:
                self._log("❌ Kein Ergebnis gefunden.", "red"); return
            self._log(f"✅ Gefunden: {yt_url}", "green")
            self.url_var.set(yt_url)
            self.search_var.set(""); self.artist_var.set("")
            self.after(0, self._start_download)
        except Exception as e:
            self._log(f"❌ Fehler: {e}", "red")
        finally:
            self._set_busy(False)

    # ── Spotify ──────────────────────────────────────────────────────────────
    def _spotify_to_yt(self):
        url = self.spotify_var.get().strip()
        if not url or "spotify.com" not in url:
            messagebox.showwarning("Kein Spotify-Link", "Bitte einen Spotify-Link einfügen!")
            return
        threading.Thread(target=self._do_spotify_search, args=(url,), daemon=True).start()

    def _do_spotify_search(self, spotify_url):
        self._set_busy(True)
        try:
            self._log("🎵 Lese Spotify-Link...", "spotify")
            req = urllib.request.Request(spotify_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r"<title>(.*?)</title>", html)
            if not m:
                self._log("❌ Konnte Songtitel nicht lesen.", "red"); return
            song_name = re.sub(r"\s*[|\-–]\s*Spotify.*$", "", m.group(1)).strip()
            self._log(f"🎵 Song: {song_name}", "spotify")
            self._log("🔍 Suche auf YouTube...", "spotify")
            yt_url = self._youtube_search(song_name + " official audio")
            if not yt_url:
                self._log("❌ Kein YouTube-Video gefunden.", "red"); return
            self._log(f"✅ YouTube: {yt_url}", "green")
            self.url_var.set(yt_url); self.spotify_var.set("")
            self.after(0, self._start_download)
        except Exception as e:
            self._log(f"❌ Fehler: {e}", "red")
        finally:
            self._set_busy(False)

    # ── Tools ────────────────────────────────────────────────────────────────
    def _check_tools(self):
        missing = []
        if not os.path.exists(YTDLP_PATH):  missing.append("yt-dlp")
        if not os.path.exists(FFMPEG_PATH): missing.append("ffmpeg")
        if missing:
            self._log(f"⚙  Installiere: {', '.join(missing)}...")
            threading.Thread(target=self._install_tools, daemon=True).start()
        else:
            self._log("✅ Bereit! Strg+V oder Songname eingeben.", "green")

    def _install_tools(self):
        self._set_busy(True)
        os.makedirs(TOOLS_DIR, exist_ok=True)
        try:
            if not os.path.exists(YTDLP_PATH):
                self._log("⬇  yt-dlp wird heruntergeladen...")
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_PATH)
                self._log("✅ yt-dlp installiert.", "green")
            if not os.path.exists(FFMPEG_PATH):
                self._log("⬇  ffmpeg wird heruntergeladen (~80 MB)...")
                zp = os.path.join(TOOLS_DIR, "ffmpeg.zip")
                urllib.request.urlretrieve(FFMPEG_URL, zp)
                self._log("📦 Entpacke ffmpeg...")
                with zipfile.ZipFile(zp, "r") as z:
                    for m in z.namelist():
                        if m.endswith("ffmpeg.exe"):
                            z.extract(m, TOOLS_DIR)
                            shutil.move(os.path.join(TOOLS_DIR, m), FFMPEG_PATH)
                            break
                os.remove(zp)
                for d in os.listdir(TOOLS_DIR):
                    dp = os.path.join(TOOLS_DIR, d)
                    if os.path.isdir(dp): shutil.rmtree(dp, ignore_errors=True)
                self._log("✅ ffmpeg installiert.", "green")
            self._log("🎉 Alles bereit!", "green")
        except Exception as e:
            self._log(f"❌ Fehler: {e}", "red")
        finally:
            self._set_busy(False)

    # ── Update ───────────────────────────────────────────────────────────────
    def _check_update(self):
        self._log("🔄 Suche nach Updates...")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        self._set_busy(True)
        try:
            # Versionsnummer von GitHub lesen
            self._log("🔍 Prüfe GitHub...")
            req = urllib.request.Request(GITHUB_RAW, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                content = r.read().decode("utf-8")
            m = re.search(r'^VERSION\s*=\s*"([^"]+)"', content, re.MULTILINE)
            new_ver = m.group(1) if m else VERSION

            if new_ver == VERSION:
                self._log(f"✅ Bereits aktuell (v{VERSION}).", "green")
                self._set_busy(False)
                return

            self._log(f"🆕 Neue Version v{new_ver} gefunden!")

            if IS_EXE:
                # EXE-Modus: neue EXE von GitHub Releases laden
                self._log("⬇  Lade neue EXE von GitHub (~30 MB)...")
                exe_path  = sys.executable
                tmp_path  = exe_path + ".new"
                old_path  = exe_path + ".old"
                urllib.request.urlretrieve(GITHUB_EXE, tmp_path,
                    reporthook=lambda b,bs,ts: self._log(
                        f"   {min(100,int(b*bs/ts*100)) if ts>0 else '?'}% heruntergeladen...") if b%50==0 else None)
                self._log("✅ Download fertig! Starte neu...", "green")
                # Batch-Script: alte EXE ersetzen + neu starten
                bat = os.path.join(BASE_DIR, "_update.bat")
                with open(bat, "w") as f:
                    f.write(f"""@echo off
timeout /t 2 /nobreak >nul
move /y "{tmp_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
""")
                subprocess.Popen(["cmd", "/c", bat],
                                 creationflags=CREATE_NO_WINDOW,
                                 close_fds=True)
                self.after(500, self.destroy)
            else:
                # Script-Modus: .py Datei ersetzen + neu starten
                py_target = os.path.join(BASE_DIR, "mp3downloader.py")
                with open(py_target, "w", encoding="utf-8") as f:
                    f.write(content)
                self._log(f"✅ v{new_ver} installiert! Starte neu...", "green")
                self.after(800, lambda: (
                    subprocess.Popen([sys.executable, py_target],
                                     creationflags=CREATE_NO_WINDOW),
                    self.destroy()
                ))
        except Exception as e:
            self._log(f"❌ Update-Fehler: {e}", "red")
        finally:
            self._set_busy(False)

    # ── Download ─────────────────────────────────────────────────────────────
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kein Link", "Kein Link gefunden!"); return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("Tools fehlen", "Bitte warten – Tools werden noch installiert.")
            return
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        self._set_busy(True)
        self._hide_success()
        self.last_file = None
        self._log(f"\n▶  Download startet...")
        out = os.path.join(self.output_dir.get(), "%(title)s.%(ext)s")
        cmd = [YTDLP_PATH, "-x", "--audio-format", "mp3",
               "--audio-quality", self.quality_var.get(),
               "--ffmpeg-location", TOOLS_DIR,
               "-o", out, "--no-playlist",
               "--print", "after_move:filepath", url]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace",
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
                self._log(f"\n✅ Fertig! Gespeichert in: {self.output_dir.get()}", "green")
                self.url_var.set("")
                folder, last = self.output_dir.get(), self.last_file
                self.after(0, lambda: self._show_success(folder))
                self.after(500, lambda: self._open_in_explorer(last))
            else:
                self._log("❌ Fehlgeschlagen. Prüfe den Link.", "red")
        except Exception as e:
            self._log(f"❌ Fehler: {e}", "red")
        finally:
            self._set_busy(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
