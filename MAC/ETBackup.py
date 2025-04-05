import os
import shutil
import time
import zipfile
import threading
import json
import webbrowser
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import winreg

SETTINGS_FILE = "etbackup_settings.json"
APP_NAME = "ETBackup"

class ETBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETBackup - EggTimer Folder Backup v1.0")
        self.root.geometry("600x580")

        try:
            self.root.iconbitmap("ETB.ico")
        except Exception:
            pass

        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.interval_minutes = tk.IntVar(value=30)
        self.autorun_enabled = tk.BooleanVar()
        self.autostart_backup = tk.BooleanVar()
        self.minimize_on_start = tk.BooleanVar()
        self.dark_mode_enabled = tk.BooleanVar()
        self.running = False
        self.backup_thread = None

        self.load_settings()
        self._bind_live_settings()
        self.apply_theme()
        self.create_widgets()

        if self.minimize_on_start.get():
            self.root.iconify()

        if self.autorun_enabled.get() and self.autostart_backup.get() and self.source_folder.get() and self.output_folder.get():
            self.start_backup()

    def apply_theme(self):
        if self.dark_mode_enabled.get():
            self.bg_color = '#2e2e2e'
            self.fg_color = '#ffffff'
            self.entry_bg = '#3c3c3c'
            self.log_bg = '#1e1e1e'
        else:
            self.bg_color = '#f0f0f0'
            self.fg_color = '#000000'
            self.entry_bg = '#ffffff'
            self.log_bg = '#f4f4f4'
        self.root.configure(bg=self.bg_color)

    def create_widgets(self):
        frame = tk.Frame(self.root, bg=self.bg_color)
        frame.pack(padx=10, pady=10, fill='both', expand=True)

        tk.Label(frame, text="Source Folder:", bg=self.bg_color, fg=self.fg_color).pack(anchor='w')
        tk.Entry(frame, textvariable=self.source_folder, width=60, bg=self.entry_bg, fg=self.fg_color).pack(fill='x')
        tk.Button(frame, text="Browse", command=self.browse_source).pack(pady=5)

        tk.Label(frame, text="Backup Destination Folder:", bg=self.bg_color, fg=self.fg_color).pack(anchor='w', pady=(10, 0))
        tk.Entry(frame, textvariable=self.output_folder, width=60, bg=self.entry_bg, fg=self.fg_color).pack(fill='x')
        tk.Button(frame, text="Browse", command=self.browse_output).pack(pady=5)

        tk.Label(frame, text="Backup Interval (minutes):", bg=self.bg_color, fg=self.fg_color).pack(anchor='w', pady=(10, 0))
        interval_frame = tk.Frame(frame, bg=self.bg_color)
        interval_frame.pack(anchor='center', pady=(0, 5))
        self.hours_label = tk.Label(interval_frame, text=f"{self.interval_minutes.get() / 60:.2f} hrs", bg=self.bg_color, fg=self.fg_color)
        self.hours_label.pack(side='left', padx=(0, 10))
        tk.Spinbox(interval_frame, from_=30, to=1440, increment=30, textvariable=self.interval_minutes, width=10, bg=self.entry_bg, fg=self.fg_color, command=self.save_settings).pack(side='left')
        tk.Button(interval_frame, text="Set", command=self.apply_interval_update).pack(side='left', padx=5)

        tk.Checkbutton(frame, text="Run at system startup", variable=self.autorun_enabled, command=self.toggle_autorun, bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor='w', pady=(10, 0))
        tk.Checkbutton(frame, text="Auto-start backups on launch", variable=self.autostart_backup, bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor='w')
        tk.Checkbutton(frame, text="Minimize window on startup", variable=self.minimize_on_start, bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor='w')
        tk.Checkbutton(frame, text="Enable Dark Mode", variable=self.dark_mode_enabled, command=self.restart_ui, bg=self.bg_color, fg=self.fg_color, selectcolor=self.bg_color).pack(anchor='w')

        self.log = tk.Text(frame, height=6, state='disabled', bg=self.log_bg, fg=self.fg_color)
        self.log.pack(pady=10, fill='both', expand=True)

        self.status_label = tk.Label(frame, text="Backups Stored: 0 | Space Used: 0 MB", bg=self.bg_color, fg=self.fg_color)
        self.status_label.pack(pady=(0, 10))

        button_frame = tk.Frame(frame, bg=self.bg_color)
        button_frame.pack(pady=5)

        self.start_button = tk.Button(button_frame, text="Start Backup", command=self.start_backup)
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop Backup", command=self.stop_backup, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)

        self.open_output_button = tk.Button(button_frame, text="Open Backup Folder", command=self.open_output_folder)
        self.open_output_button.grid(row=0, column=2, padx=5)

        self.ownership_label = tk.Label(self.root, text="Development v1.0 by github.com/TheRed2685", font=("Arial", 9, "underline"), fg="blue", cursor="hand2", bg=self.bg_color)
        self.ownership_label.pack(side='bottom', pady=5)
        self.ownership_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/TheRed2685"))

        self.update_status()

    def restart_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.apply_theme()
        self.create_widgets()
        self.save_settings()

    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)
            self.save_settings()

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            self.save_settings()
            self.update_status()

    def start_backup(self):
        if not self.source_folder.get() or not self.output_folder.get():
            messagebox.showerror("Error", "Please select both source and destination folders.")
            return

        self.running = True
        self.start_button.config(state='disabled', text='Running...')
        self.stop_button.config(state='normal')
        self.backup_thread = threading.Thread(target=self.backup_loop, daemon=True)
        self.backup_thread.start()
        self.save_settings()

    def stop_backup(self):
        self.running = False
        self.start_button.config(state='normal', text='Start Backup')
        self.stop_button.config(state='disabled')
        self.log_message("Backup stopped.")

    def open_output_folder(self):
        if self.output_folder.get():
            os.startfile(self.output_folder.get())
        else:
            messagebox.showinfo("Info", "No backup folder selected.")

    def backup_loop(self):
        while self.running:
            self.perform_backup()
            try:
                interval = int(self.interval_minutes.get()) * 60
            except tk.TclError:
                interval = 1800  # fallback to 30 minutes
            time.sleep(interval)
        while self.running:
            self.perform_backup()
            time.sleep(interval)

    def perform_backup(self):
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        zip_name = f"ETBackup_{now}.zip"
        zip_path = os.path.join(self.output_folder.get(), zip_name)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for foldername, subfolders, filenames in os.walk(self.source_folder.get()):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, self.source_folder.get())
                        zipf.write(file_path, arcname)
            self.log_message(f"Backup created: {zip_name}")
            self.update_status()
        except Exception as e:
            self.log_message(f"Error during backup: {e}")

    def log_message(self, message):
        self.log.config(state='normal')
        self.log.insert('end', f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log.see('end')
        self.log.config(state='disabled')

    def update_status(self):
        backup_folder = self.output_folder.get()
        if not backup_folder or not os.path.exists(backup_folder):
            self.status_label.config(text="Backups Stored: 0 | Space Used: 0 MB")
            return

        count = 0
        total_size = 0
        for filename in os.listdir(backup_folder):
            if filename.endswith(".zip") and filename.startswith("ETBackup_"):
                count += 1
                total_size += os.path.getsize(os.path.join(backup_folder, filename))

        size_mb = total_size / (1024 * 1024)
        self.status_label.config(text=f"Backups Stored: {count} | Space Used: {size_mb:.2f} MB")

    def toggle_autorun(self):
        exe_path = os.path.abspath(sys.argv[0])
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_ALL_ACCESS) as key:
                if self.autorun_enabled.get():
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
                    self.log_message("Autorun enabled.")
                else:
                    winreg.DeleteValue(key, APP_NAME)
                    self.log_message("Autorun disabled.")
        except Exception as e:
            self.log_message(f"Autorun toggle failed: {e}")

    def apply_interval_update(self):
        self.hours_label.config(text=f"{self.interval_minutes.get() / 60:.2f} hrs")
        self.save_settings()
        self.log_message(f"Backup interval updated to {self.interval_minutes.get()} minutes.")

    def save_settings(self):
        try:
            interval = self.interval_minutes.get()
        except tk.TclError:
            interval = None
        settings = {
            "source_folder": self.source_folder.get(),
            "output_folder": self.output_folder.get(),
            "interval_minutes": interval if interval is not None else 30,
            "autorun_enabled": self.autorun_enabled.get(),
            "autostart_backup": self.autostart_backup.get(),
            "minimize_on_start": self.minimize_on_start.get(),
            "dark_mode_enabled": self.dark_mode_enabled.get()
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)

    def _bind_live_settings(self):
        self.source_folder.trace_add("write", lambda *args: self.save_settings())
        self.output_folder.trace_add("write", lambda *args: self.save_settings())
        self.interval_minutes.trace_add("write", lambda *args: [self.save_settings(), self.hours_label.config(text=f"{self.interval_minutes.get() / 60:.2f} hrs")])
        self.autorun_enabled.trace_add("write", lambda *args: self.save_settings())
        self.autostart_backup.trace_add("write", lambda *args: self.save_settings())
        self.minimize_on_start.trace_add("write", lambda *args: self.save_settings())
        self.dark_mode_enabled.trace_add("write", lambda *args: self.save_settings())

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.source_folder.set(settings.get("source_folder", ""))
                    self.output_folder.set(settings.get("output_folder", ""))
                    self.interval_minutes.set(settings.get("interval_minutes", 30))
                    self.autorun_enabled.set(settings.get("autorun_enabled", False))
                    self.autostart_backup.set(settings.get("autostart_backup", False))
                    self.minimize_on_start.set(settings.get("minimize_on_start", False))
                    self.dark_mode_enabled.set(settings.get("dark_mode_enabled", False))
            except Exception:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ETBackupApp(root)
    root.mainloop()
