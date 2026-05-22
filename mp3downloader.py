import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess
import os
import sys
import urllib.request
import zipfile

# ── Pfade ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
TOOLS_DIR   = os.path.join(BASE_DIR, "tools")
YTDLP_PATH  = os.path.join(TOOLS_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(TOOLS_DIR, "ffmpeg.exe")

YTDLP_URL  = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# ── Design ─────────────────────────────────────────────────────────────────
BG       = "#111116"
CARD     = "#1a1a22"
ACCENT   = "#ff3c5f"
ACCENT2  = "#ff7043"
TEXT     = "#f0f0f5"
SUBTEXT  = "#888899"
BORDER   = "#2a2a38"
SUCCESS  = "#00e676"
FONT_BIG = ("Segoe UI", 22, "bold")
FONT_MED = ("Segoe UI", 11)
FONT_SM  = ("Segoe UI", 9)
FONT_LOG = ("Consolas", 9)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT → MP3")
        self.geometry("620x580")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        self._build_ui()
        self.after(200, self._check_tools)

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=30, pady=(28, 0))
        tk.Label(hdr, text="YT → MP3", font=("Segoe UI Black", 28, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(hdr, text="  downloader", font=("Segoe UI", 16),
                 bg=BG, fg=SUBTEXT).pack(side="left", pady=(8,0))

        tk.Label(self, text="YouTube-Link einfügen und MP3 laden – fertig.",
                 font=FONT_SM, bg=BG, fg=SUBTEXT).pack(anchor="w", padx=30, pady=(2,18))

        # URL Card
        self._card_url()
        # Folder Card
        self._card_folder()
        # Download Button
        self.dl_btn = tk.Button(self, text="⬇  MP3 herunterladen",
                                font=("Segoe UI", 13, "bold"),
                                bg=ACCENT, fg="white", activebackground=ACCENT2,
                                activeforeground="white", relief="flat",
                                cursor="hand2", height=2,
                                command=self._start_download)
        self.dl_btn.pack(fill="x", padx=30, pady=(6, 14))

        # Progress
        self.prog_var = tk.DoubleVar()
        self.prog = ttk.Progressbar(self, variable=self.prog_var, maximum=100,
                                    mode="indeterminate")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=CARD, background=ACCENT,
                         thickness=4)
        self.prog.pack(fill="x", padx=30)

        # Log
        log_frame = tk.Frame(self, bg=CARD, bd=0, highlightthickness=1,
                              highlightbackground=BORDER)
        log_frame.pack(fill="both", expand=True, padx=30, pady=(14, 24))

        tk.Label(log_frame, text="LOG", font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=10, pady=(8,0))

        self.log = tk.Text(log_frame, bg=CARD, fg=TEXT, font=FONT_LOG,
                           relief="flat", bd=0, height=9,
                           insertbackground=ACCENT, wrap="word",
                           state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        sb = tk.Scrollbar(log_frame, command=self.log.yview, bg=CARD,
                          troughcolor=CARD, width=6)
        self.log.configure(yscrollcommand=sb.set)

    def _card_url(self):
        frame = tk.Frame(self, bg=CARD, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        frame.pack(fill="x", padx=30, pady=(0, 10))
        tk.Label(frame, text="YouTube URL", font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=14, pady=(10, 2))

        inner = tk.Frame(frame, bg=CARD)
        inner.pack(fill="x", padx=14, pady=(0, 12))

        self.url_var = tk.StringVar()
        entry = tk.Entry(inner, textvariable=self.url_var,
                         font=("Segoe UI", 11), bg="#22222e", fg=TEXT,
                         insertbackground=TEXT, relief="flat",
                         bd=0, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)

        paste_btn = tk.Button(inner, text="📋 Einfügen",
                              font=FONT_SM, bg=BORDER, fg=TEXT,
                              activebackground=ACCENT, activeforeground="white",
                              relief="flat", cursor="hand2",
                              command=self._paste_url)
        paste_btn.pack(side="left", padx=(8, 0), ipady=6, ipadx=8)

    def _card_folder(self):
        frame = tk.Frame(self, bg=CARD, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        frame.pack(fill="x", padx=30, pady=(0, 10))
        tk.Label(frame, text="Speicherordner", font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=SUBTEXT).pack(anchor="w", padx=14, pady=(10, 2))

        inner = tk.Frame(frame, bg=CARD)
        inner.pack(fill="x", padx=14, pady=(0, 12))

        dir_lbl = tk.Label(inner, textvariable=self.output_dir,
                           font=("Segoe UI", 10), bg="#22222e", fg=TEXT,
                           anchor="w", relief="flat",
                           highlightthickness=1, highlightbackground=BORDER)
        dir_lbl.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)

        browse_btn = tk.Button(inner, text="📁 Auswählen",
                               font=FONT_SM, bg=BORDER, fg=TEXT,
                               activebackground=ACCENT, activeforeground="white",
                               relief="flat", cursor="hand2",
                               command=self._browse)
        browse_btn.pack(side="left", padx=(8, 0), ipady=6, ipadx=8)

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _paste_url(self):
        try:
            self.url_var.set(self.clipboard_get())
        except:
            pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get())
        if d:
            self.output_dir.set(d)

    def _log(self, msg, color=TEXT):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, busy):
        self.dl_btn.configure(state="disabled" if busy else "normal",
                              text="⏳ Lädt..." if busy else "⬇  MP3 herunterladen")
        if busy:
            self.prog.configure(mode="indeterminate")
            self.prog.start(12)
        else:
            self.prog.stop()
            self.prog_var.set(0)

    # ── Tools installieren ──────────────────────────────────────────────────
    def _check_tools(self):
        missing = []
        if not os.path.exists(YTDLP_PATH):  missing.append("yt-dlp")
        if not os.path.exists(FFMPEG_PATH): missing.append("ffmpeg")
        if missing:
            self._log(f"⚙  Fehlende Tools: {', '.join(missing)} – werden automatisch installiert...")
            threading.Thread(target=self._install_tools, daemon=True).start()
        else:
            self._log("✅ yt-dlp und ffmpeg sind bereit.")

    def _install_tools(self):
        self._set_busy(True)
        os.makedirs(TOOLS_DIR, exist_ok=True)
        try:
            if not os.path.exists(YTDLP_PATH):
                self._log("⬇  Lade yt-dlp herunter...")
                urllib.request.urlretrieve(YTDLP_URL, YTDLP_PATH)
                self._log("✅ yt-dlp installiert.")

            if not os.path.exists(FFMPEG_PATH):
                self._log("⬇  Lade ffmpeg herunter (ca. 80 MB, bitte warten)...")
                zip_path = os.path.join(TOOLS_DIR, "ffmpeg.zip")
                urllib.request.urlretrieve(FFMPEG_URL, zip_path)
                self._log("📦 Entpacke ffmpeg...")
                with zipfile.ZipFile(zip_path, "r") as z:
                    for member in z.namelist():
                        if member.endswith("ffmpeg.exe"):
                            z.extract(member, TOOLS_DIR)
                            extracted = os.path.join(TOOLS_DIR, member)
                            os.rename(extracted, FFMPEG_PATH)
                            break
                os.remove(zip_path)
                # Aufräumen leerer Ordner
                for d in os.listdir(TOOLS_DIR):
                    p = os.path.join(TOOLS_DIR, d)
                    if os.path.isdir(p):
                        import shutil; shutil.rmtree(p, ignore_errors=True)
                self._log("✅ ffmpeg installiert.")

            self._log("🎉 Alles bereit! URL einfügen und loslegen.")
        except Exception as e:
            self._log(f"❌ Fehler bei Installation: {e}")
        finally:
            self._set_busy(False)

    # ── Download ────────────────────────────────────────────────────────────
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kein Link", "Bitte einen YouTube-Link einfügen!")
            return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("Tools fehlen", "yt-dlp wird noch installiert – bitte kurz warten.")
            return
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        self._set_busy(True)
        self._log(f"\n▶  Starte Download:\n   {url}")
        out_template = os.path.join(self.output_dir.get(), "%(title)s.%(ext)s")
        cmd = [
            YTDLP_PATH,
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "--ffmpeg-location", TOOLS_DIR,
            "-o", out_template,
            "--no-playlist",
            url
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self._log(line)
            proc.wait()
            if proc.returncode == 0:
                self._log(f"\n✅ Fertig! Datei gespeichert in:\n   {self.output_dir.get()}")
                self.url_var.set("")
            else:
                self._log("❌ Download fehlgeschlagen. Prüfe den Link.")
        except Exception as e:
            self._log(f"❌ Fehler: {e}")
        finally:
            self._set_busy(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()
