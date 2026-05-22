import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess
import os
import sys
import urllib.request
import zipfile
import webbrowser
import shutil

VERSION    = "1.1"
APP_NAME   = "Alex MP3 Song App"
GITHUB_RAW = "https://raw.githubusercontent.com/alex63494711-cmd/alex-mp3-song-app/refs/heads/main/mp3downloader.py"

BASE_DIR    = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
TOOLS_DIR   = os.path.join(BASE_DIR, "tools")
YTDLP_PATH  = os.path.join(TOOLS_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(TOOLS_DIR, "ffmpeg.exe")

YTDLP_URL  = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

BG      = "#0d0d12"
CARD    = "#16161f"
ACCENT  = "#7c3aed"
ACCENT2 = "#9d5ff5"
TEXT    = "#f0f0f5"
SUBTEXT = "#66667a"
BORDER  = "#222230"
BTN_SEC = "#1e1e2a"
SUCCESS = "#22c55e"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{VERSION}")
        self.geometry("640x640")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        self._build_ui()
        self.after(300, self._check_tools)

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=28, pady=(24, 0))

        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="🎵 Alex", font=("Segoe UI Black", 24, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(left, text=" MP3 Song App", font=("Segoe UI", 16),
                 bg=BG, fg=TEXT).pack(side="left", pady=(6,0))

        # Update Button
        self.upd_btn = tk.Button(hdr, text="🔄 Update",
                                 font=("Segoe UI", 9, "bold"),
                                 bg=BTN_SEC, fg=SUBTEXT,
                                 activebackground=ACCENT, activeforeground="white",
                                 relief="flat", cursor="hand2", bd=0,
                                 command=self._check_update)
        self.upd_btn.pack(side="right", ipadx=12, ipady=6)

        tk.Label(self, text=f"v{VERSION}  –  YouTube & SoundCloud → MP3",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w", padx=28, pady=(3, 16))

        self._card_url()
        self._card_folder()
        self._card_quality()

        # Download Button
        self.dl_btn = tk.Button(self, text="⬇   MP3 herunterladen",
                                font=("Segoe UI", 13, "bold"),
                                bg=ACCENT, fg="white",
                                activebackground=ACCENT2, activeforeground="white",
                                relief="flat", cursor="hand2", height=2,
                                command=self._start_download)
        self.dl_btn.pack(fill="x", padx=28, pady=(8, 10))

        # Progressbar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("A.TProgressbar", troughcolor=CARD, background=ACCENT, thickness=4)
        self.prog = ttk.Progressbar(self, style="A.TProgressbar", mode="indeterminate")
        self.prog.pack(fill="x", padx=28)

        # Log
        lf = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="both", expand=True, padx=28, pady=(12, 24))
        tk.Label(lf, text="LOG", font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=12, pady=(8, 0))
        self.log = tk.Text(lf, bg=CARD, fg=TEXT, font=("Consolas", 9),
                           relief="flat", bd=0, height=8,
                           insertbackground=ACCENT, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=12, pady=(2, 10))

    def _card_url(self):
        f = self._card("YouTube / SoundCloud URL")
        inner = tk.Frame(f, bg=CARD)
        inner.pack(fill="x", padx=14, pady=(0, 12))
        self.url_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.url_var, font=("Segoe UI", 11),
                 bg="#0f0f18", fg=TEXT, insertbackground=TEXT,
                 relief="flat", highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        tk.Button(inner, text="📋 Einfügen", font=("Segoe UI", 9),
                  bg=BTN_SEC, fg=TEXT, activebackground=ACCENT,
                  activeforeground="white", relief="flat", cursor="hand2",
                  command=self._paste).pack(side="left", padx=(8,0), ipady=6, ipadx=10)

    def _card_folder(self):
        f = self._card("Speicherordner")
        inner = tk.Frame(f, bg=CARD)
        inner.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(inner, textvariable=self.output_dir, font=("Segoe UI", 10),
                 bg="#0f0f18", fg=TEXT, anchor="w",
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        tk.Button(inner, text="📁 Auswählen", font=("Segoe UI", 9),
                  bg=BTN_SEC, fg=TEXT, activebackground=ACCENT,
                  activeforeground="white", relief="flat", cursor="hand2",
                  command=self._browse).pack(side="left", padx=(8,0), ipady=6, ipadx=10)

    def _card_quality(self):
        f = self._card("Qualität")
        inner = tk.Frame(f, bg=CARD)
        inner.pack(fill="x", padx=14, pady=(0, 12))
        self.quality_var = tk.StringVar(value="0")
        opts = [("Beste (320kbps)", "0"), ("Gut (192kbps)", "5"), ("Normal (128kbps)", "9")]
        for label, val in opts:
            tk.Radiobutton(inner, text=label, variable=self.quality_var, value=val,
                           bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                           activeforeground=ACCENT, font=("Segoe UI", 10),
                           cursor="hand2").pack(side="left", padx=(0, 18))

    def _card(self, title):
        f = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        f.pack(fill="x", padx=28, pady=(0, 10))
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=14, pady=(10, 4))
        return f

    # ── Actions ──────────────────────────────────────────────────────────────
    def _paste(self):
        try: self.url_var.set(self.clipboard_get())
        except: pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get())
        if d: self.output_dir.set(d)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, busy, btn_text="⬇   MP3 herunterladen"):
        state = "disabled" if busy else "normal"
        self.dl_btn.configure(state=state, text="⏳  Lädt..." if busy else btn_text)
        self.upd_btn.configure(state=state)
        if busy: self.prog.configure(mode="indeterminate"); self.prog.start(12)
        else:    self.prog.stop()

    # ── Tools ────────────────────────────────────────────────────────────────
    def _check_tools(self):
        missing = []
        if not os.path.exists(YTDLP_PATH):  missing.append("yt-dlp")
        if not os.path.exists(FFMPEG_PATH): missing.append("ffmpeg")
        if missing:
            self._log(f"⚙  Installiere: {', '.join(missing)}...")
            threading.Thread(target=self._install_tools, daemon=True).start()
        else:
            self._log("✅ Bereit! Link einfügen und loslegen.")

    def _install_tools(self):
        self._set_busy(True)
        os.makedirs(TOOLS_DIR, exist_ok=True)
        try:
            if not os.path.exists(YTDLP_PATH):
                self._log("⬇  yt-dlp wird heruntergeladen...")
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_PATH)
                self._log("✅ yt-dlp installiert.")
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
                    p = os.path.join(TOOLS_DIR, d)
                    if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
                self._log("✅ ffmpeg installiert.")
            self._log("🎉 Alles bereit!")
        except Exception as e:
            self._log(f"❌ Fehler: {e}")
        finally:
            self._set_busy(False)

    # ── Update ───────────────────────────────────────────────────────────────
    def _check_update(self):
        self._log("🔄 Suche nach Updates...")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        self._set_busy(True)
        try:
            self._log(f"⬇  Lade neue Version von GitHub...")
            tmp = os.path.join(BASE_DIR, "mp3downloader_new.py")
            urllib.request.urlretrieve(GITHUB_RAW, tmp)

            # Versionsnummer aus neuer Datei lesen
            new_ver = VERSION
            with open(tmp, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VERSION"):
                        new_ver = line.split('"')[1]
                        break

            if new_ver == VERSION:
                os.remove(tmp)
                self._log(f"✅ Du hast bereits die neueste Version (v{VERSION})!")
            else:
                # Aktuelle Datei ersetzen
                current = os.path.abspath(__file__) if not getattr(sys, 'frozen', False) else None
                if current:
                    shutil.move(tmp, current)
                    self._log(f"✅ Update auf v{new_ver} erfolgreich!")
                    self._log("⚠  Bitte EXE neu bauen: build_exe.bat doppelklicken.")
                    messagebox.showinfo("Update", f"v{new_ver} heruntergeladen!\n\nJetzt build_exe.bat ausführen für die neue EXE.")
                else:
                    os.remove(tmp)
                    self._log(f"ℹ  Neue Version v{new_ver} verfügbar!")
                    self._log("   Lade mp3downloader.py von GitHub und baue EXE neu.")
                    messagebox.showinfo("Update verfügbar", f"Version v{new_ver} ist verfügbar!\n\nLade mp3downloader.py von GitHub herunter\nund führe build_exe.bat aus.")
        except Exception as e:
            self._log(f"❌ Update-Fehler: {e}")
        finally:
            self._set_busy(False)

    # ── Download ─────────────────────────────────────────────────────────────
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kein Link", "Bitte einen YouTube oder SoundCloud Link einfügen!")
            return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("Tools fehlen", "Bitte warten – Tools werden noch installiert.")
            return
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        self._set_busy(True)
        self._log(f"\n▶  Download startet...")
        out = os.path.join(self.output_dir.get(), "%(title)s.%(ext)s")
        cmd = [
            YTDLP_PATH,
            "-x", "--audio-format", "mp3",
            "--audio-quality", self.quality_var.get(),
            "--ffmpeg-location", TOOLS_DIR,
            "-o", out,
            "--no-playlist",
            url
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                if line.strip(): self._log(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self._log(f"\n✅ Fertig! Gespeichert in:\n   {self.output_dir.get()}")
                self.url_var.set("")
            else:
                self._log("❌ Fehlgeschlagen. Prüfe den Link.")
        except Exception as e:
            self._log(f"❌ Fehler: {e}")
        finally:
            self._set_busy(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
