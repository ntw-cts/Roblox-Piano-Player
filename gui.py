import os
import threading
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
import playSong
import pyMIDI
import strip

def get_resource_path(relative_path):
    import sys
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Set theme colors and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RobloxAutoPlayerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Roblox Piano Auto-Player")
        self.geometry("1020x660")
        self.resizable(False, False)
        
        # Keep window always on top by default
        self.attributes("-topmost", True)
        
        # Set window icon
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        # Configure layout grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Display Panel
        
        self.selected_midi = None
        self.midi_files = []
        self.total_notes = 0
        self.total_duration = 0.0
        self.hide_scrollbar_timer = None
        
        self.setup_sidebar()
        self.setup_main_panel()
        
        # Start global key listener in the background
        playSong.start_hotkey_listener()
        
        # Register playSong GUI callbacks
        playSong.state_callbacks['play_state'] = lambda is_playing: self.after(0, self.cb_play_state, is_playing)
        playSong.state_callbacks['progress'] = lambda idx, t: self.after(0, self.cb_progress, idx, t)
        playSong.state_callbacks['speed'] = lambda spd: self.after(0, self.cb_speed, spd)
        playSong.state_callbacks['legit_mode'] = lambda active: self.after(0, self.cb_legit_mode, active)
        playSong.state_callbacks['song_loaded'] = lambda fn, notes, dur: self.after(0, self.cb_song_loaded, fn, notes, dur)
        playSong.state_callbacks['exit'] = lambda: self.after(0, self.on_closing)
        
        # Register window close hook
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Scan midi folder and load default file if present
        self.refresh_midi_list()
        
        if os.path.exists("song.txt"):
            try:
                self.load_song_file("song.txt")
            except Exception as e:
                print(f"Warning: Failed to load previous song.txt: {e}")
                try:
                    os.remove("song.txt")
                except Exception:
                    pass
                    
        # Start periodic progress update timer
        self.update_realtime_progress()

    def setup_sidebar(self):
        # Sidebar Container
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#1e293b")
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(3, weight=1) # The MIDI list gets the expanded weight
        
        # Header Label
        title_label = ctk.CTkLabel(
            self.sidebar, 
            text="MIDI FILES", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc"
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Action Buttons Container (Scan / Open)
        self.btn_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.btn_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.btn_container.grid_columnconfigure(0, weight=1)
        self.btn_container.grid_columnconfigure(1, weight=1)
        
        self.refresh_btn = ctk.CTkButton(
            self.btn_container,
            text="Scan Folder",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            corner_radius=8,
            command=self.refresh_midi_list
        )
        self.refresh_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.open_folder_btn = ctk.CTkButton(
            self.btn_container,
            text="Open Folder",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#475569",
            hover_color="#334155",
            corner_radius=8,
            command=self.open_midi_folder
        )
        self.open_folder_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Instruction Subtext
        list_label = ctk.CTkLabel(
            self.sidebar,
            text="Select a MIDI file:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#94a3b8"
        )
        list_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # Scrollable MIDI File List
        self.file_list_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="#0f172a",
            label_text_color="#94a3b8",
            corner_radius=8
        )
        self.file_list_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.file_list_frame.grid_columnconfigure(0, weight=1)
        self.file_buttons = []
        
        # Hide scrollbar initially and bind hover events
        try:
            self.file_list_frame._scrollbar.grid_remove()
            self.file_list_frame._parent_canvas.grid_configure(padx=(4, 4))
        except Exception:
            pass
        self.file_list_frame.bind("<Enter>", self.show_scrollbar, add="+")
        self.file_list_frame.bind("<Leave>", self.hide_scrollbar_delayed, add="+")
        try:
            self.file_list_frame._parent_canvas.bind("<Enter>", self.show_scrollbar, add="+")
            self.file_list_frame._parent_canvas.bind("<Leave>", self.hide_scrollbar_delayed, add="+")
            self.file_list_frame._scrollbar.bind("<Enter>", self.show_scrollbar, add="+")
            self.file_list_frame._scrollbar.bind("<Leave>", self.hide_scrollbar_delayed, add="+")
        except Exception:
            pass
        
        # Strip/Filter Checkbox
        self.piano_only_var = tk.BooleanVar(value=True)
        self.piano_only_cb = ctk.CTkCheckBox(
            self.sidebar,
            text="Piano Tracks Only (Strips other instruments)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            variable=self.piano_only_var,
            fg_color="#3b82f6",
            hover_color="#2563eb"
        )
        self.piano_only_cb.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="w")
        
        # Roblox Focus Only Checkbox
        self.roblox_only_var = tk.BooleanVar(value=True)
        self.roblox_only_cb = ctk.CTkCheckBox(
            self.sidebar,
            text="Roblox Focus Only (Auto-pause if tabbed out)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            variable=self.roblox_only_var,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.toggle_roblox_only
        )
        self.roblox_only_cb.grid(row=5, column=0, padx=20, pady=(5, 10), sticky="w")
        
        # Big Convert and Load Button
        self.load_btn = ctk.CTkButton(
            self.sidebar,
            text="Convert & Load Song",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            corner_radius=8,
            height=40,
            command=self.convert_and_load_selected
        )
        self.load_btn.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="ew")

    def setup_main_panel(self):
        # Main panel container
        self.main_panel = ctk.CTkFrame(self, corner_radius=0, fg_color="#0f172a")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(0, weight=0) # Loaded Song Info Card
        self.main_panel.grid_rowconfigure(1, weight=0) # Control Deck Card
        self.main_panel.grid_rowconfigure(2, weight=1) # Hotkeys Reference Card
        
        # --- 1. Loaded Song Info Card ---
        self.info_card = ctk.CTkFrame(self.main_panel, fg_color="#1e293b", corner_radius=8)
        self.info_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.song_title_label = ctk.CTkLabel(
            self.info_card,
            text="No Song Loaded",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc"
        )
        self.song_title_label.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        
        self.song_detail_label = ctk.CTkLabel(
            self.info_card,
            text="Notes: 0  |  Duration: 0m 0s  |  Status: Idle",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#94a3b8"
        )
        self.song_detail_label.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="w")
        
        # --- 2. Control Deck Card ---
        self.control_card = ctk.CTkFrame(self.main_panel, fg_color="#1e293b", corner_radius=8)
        self.control_card.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # Progress metrics text
        self.progress_label = ctk.CTkLabel(
            self.control_card,
            text="Progress: 0 / 0 notes (0%)  |  Time: 0m 0s / 0m 0s",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f8fafc"
        )
        self.progress_label.grid(row=0, column=0, columnspan=4, padx=15, pady=(15, 5), sticky="w")
        
        # Progress visual bar
        self.progress_bar = ctk.CTkProgressBar(
            self.control_card,
            progress_color="#3b82f6",
            fg_color="#0f172a",
            height=8
        )
        self.progress_bar.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)
        
        self.rewind_btn = ctk.CTkButton(
            self.control_card,
            text="<< Rewind (-10)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#475569",
            hover_color="#334155",
            corner_radius=6,
            height=35,
            state="disabled",
            command=lambda: playSong.seek_by_time(-10)
        )
        self.rewind_btn.grid(row=2, column=0, padx=(15, 5), pady=10, sticky="ew")
        
        self.play_btn = ctk.CTkButton(
            self.control_card,
            text="PLAY",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            corner_radius=6,
            height=35,
            state="disabled",
            command=self.toggle_play
        )
        self.play_btn.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        self.skip_btn = ctk.CTkButton(
            self.control_card,
            text="Skip (+10) >>",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#475569",
            hover_color="#334155",
            corner_radius=6,
            height=35,
            state="disabled",
            command=lambda: playSong.seek_by_time(10)
        )
        self.skip_btn.grid(row=2, column=2, padx=(5, 15), pady=10, sticky="ew")
        
        # Switches Container (Row 2, Column 3, next to play controls)
        self.switches_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.switches_frame.grid(row=2, column=3, padx=15, pady=5, sticky="w")
        
        # Legit Mode Switch
        self.legit_var = tk.BooleanVar(value=False)
        self.legit_switch = ctk.CTkSwitch(
            self.switches_frame,
            text="Legit Mode",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            variable=self.legit_var,
            command=self.toggle_legit_mode,
            progress_color="#10b981"
        )
        self.legit_switch.pack(anchor="w", pady=(0, 2))
        
        # Always on Top Switch
        self.always_on_top_var = tk.BooleanVar(value=True)
        self.always_on_top_switch = ctk.CTkSwitch(
            self.switches_frame,
            text="Always on Top",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top,
            progress_color="#10b981"
        )
        self.always_on_top_switch.pack(anchor="w", pady=(2, 0))
        
        # Speed Adjustment Metrics
        self.speed_label = ctk.CTkLabel(
            self.control_card,
            text="Playback Speed: 1.00x",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#f8fafc"
        )
        self.speed_label.grid(row=3, column=0, padx=15, pady=(10, 15), sticky="w")
        
        self.speed_slider = ctk.CTkSlider(
            self.control_card,
            from_=0.1,
            to=5.0,
            number_of_steps=49,
            progress_color="#3b82f6",
            fg_color="#0f172a",
            button_color="#3b82f6",
            button_hover_color="#2563eb",
            command=self.on_speed_slider_change
        )
        self.speed_slider.grid(row=3, column=1, columnspan=2, padx=5, pady=(10, 15), sticky="ew")
        self.speed_slider.set(1.0)
        
        self.reset_speed_btn = ctk.CTkButton(
            self.control_card,
            text="Reset (1.0x)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#475569",
            hover_color="#334155",
            corner_radius=6,
            width=80,
            command=self.reset_speed
        )
        self.reset_speed_btn.grid(row=3, column=3, padx=15, pady=10, sticky="w")
        
        # Weight setup
        self.control_card.grid_columnconfigure(0, weight=1)
        self.control_card.grid_columnconfigure(1, weight=1)
        self.control_card.grid_columnconfigure(2, weight=1)
        self.control_card.grid_columnconfigure(3, weight=1)
        
        # --- 3. Global Hotkeys Card ---
        self.hotkeys_card = ctk.CTkFrame(self.main_panel, fg_color="#1e293b", corner_radius=8)
        self.hotkeys_card.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        
        # Configure layout for centering inside hotkeys_card
        self.hotkeys_card.grid_columnconfigure(0, weight=1) # Left spacer
        self.hotkeys_card.grid_columnconfigure(1, weight=0) # Keys
        self.hotkeys_card.grid_columnconfigure(2, weight=0) # Description
        self.hotkeys_card.grid_columnconfigure(3, weight=1) # Right spacer
        
        self.hotkeys_card.grid_rowconfigure(0, weight=0) # Title row
        self.hotkeys_card.grid_rowconfigure(1, weight=0, minsize=10) # Top spacer (push list up)
        # Rows 2 to 8 are the hotkeys
        self.hotkeys_card.grid_rowconfigure(9, weight=1) # Bottom spacer for vertical alignment
        
        hk_title = ctk.CTkLabel(
            self.hotkeys_card,
            text="GLOBAL SHORTCUTS (Active while playing in Roblox)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        )
        hk_title.grid(row=0, column=0, columnspan=4, padx=15, pady=(15, 0), sticky="w")
        
        # Reference items
        hotkeys_list = [
            ("DELETE", "Play / Pause playback toggle"),
            ("INSERT", "Legit Mode toggle (introduces human timing variance)"),
            ("HOME", "Rewind 10 seconds"),
            ("END", "Skip 10 seconds"),
            ("PAGE UP", "Increase playback speed"),
            ("PAGE DOWN", "Decrease playback speed"),
            ("ESC", "Emergency Stop (Double-press to close)")
        ]
        
        for idx, (key, desc) in enumerate(hotkeys_list):
            key_label = ctk.CTkLabel(
                self.hotkeys_card,
                text=key,
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                text_color="#3b82f6",
                anchor="e",
                width=80
            )
            key_label.grid(row=idx+2, column=1, padx=(0, 10), pady=3, sticky="e")
            
            desc_label = ctk.CTkLabel(
                self.hotkeys_card,
                text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#cbd5e1"
            )
            desc_label.grid(row=idx+2, column=2, padx=10, pady=3, sticky="w")

    def refresh_midi_list(self):
        midi_dir = Path("midi")
        if not midi_dir.exists():
            midi_dir.mkdir(exist_ok=True)
            
        # Retrieve all .mid files
        mid_files = sorted([f for f in midi_dir.iterdir() if f.suffix.lower() == '.mid'])
        
        # Clean current buttons list
        for btn in self.file_buttons:
            btn.destroy()
        self.file_buttons = []
        
        if not mid_files:
            no_midi_lbl = ctk.CTkLabel(
                self.file_list_frame,
                text="No MIDI files found.\nPut MIDI files in 'midi/' folder",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#ef4444"
            )
            no_midi_lbl.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            no_midi_lbl.bind("<Enter>", self.show_scrollbar, add="+")
            no_midi_lbl.bind("<Leave>", self.hide_scrollbar_delayed, add="+")
            self.file_buttons.append(no_midi_lbl)
            self.selected_midi = None
            return
            
        # Build button elements
        for idx, path in enumerate(mid_files):
            display_name = path.stem if len(path.stem) <= 45 else path.stem[:42] + "..."
            btn = ctk.CTkButton(
                self.file_list_frame,
                text=display_name,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color="#334155",
                hover_color="#475569",
                corner_radius=6,
                anchor="w",
                command=lambda p=path: self.select_midi(p)
            )
            btn.midi_path = path
            btn.grid(row=idx, column=0, padx=5, pady=4, sticky="ew")
            btn.bind("<Enter>", self.show_scrollbar, add="+")
            btn.bind("<Leave>", self.hide_scrollbar_delayed, add="+")
            self.file_buttons.append(btn)
            
        # Select first MIDI item automatically
        if mid_files:
            self.select_midi(mid_files[0])

    def open_midi_folder(self):
        try:
            os.startfile("midi")
        except Exception:
            pass

    def select_midi(self, path):
        self.selected_midi = path
        # Toggle highlight colors
        for btn in self.file_buttons:
            if isinstance(btn, ctk.CTkButton):
                if getattr(btn, 'midi_path', None) == path:
                    btn.configure(fg_color="#3b82f6", hover_color="#2563eb")
                else:
                    btn.configure(fg_color="#334155", hover_color="#475569")

    def convert_and_load_selected(self):
        if not self.selected_midi:
            return
            
        midi_path = str(self.selected_midi)
        piano_only = self.piano_only_var.get()
        
        # Pause active song
        playSong.set_playing(False)
        
        # Disable button and mark state
        self.load_btn.configure(text="Converting...", fg_color="#eab308", hover_color="#ca8a04", state="disabled")
        self.song_title_label.configure(text="Converting MIDI...")
        
        def run_conversion():
            try:
                target_path = midi_path
                temp_path = None
                if piano_only:
                    target_path = strip.strip_midi(midi_path)
                    temp_path = target_path
                
                # Parse MIDI events using pyMIDI
                midi_obj = pyMIDI.MidiFile(target_path)
                midi_obj.save_song("song.txt")
                midi_obj.save_sheet("sheetConversion.txt")
                
                if not midi_obj.success:
                    raise Exception("pyMIDI conversion returned unsuccessful status.")
                
                # Clean up the temp stripped midi file to prevent folder clutter
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                
                display_name = Path(midi_path).name
                self.after(0, self.on_conversion_success, "song.txt", display_name)
            except Exception as e:
                self.after(0, self.on_conversion_error, str(e))
                
        threading.Thread(target=run_conversion, daemon=True).start()

    def on_conversion_success(self, filename, display_name):
        self.load_btn.configure(text="Convert & Load Song", fg_color="#10b981", hover_color="#059669", state="normal")
        success = playSong.load_song(filename, display_name=display_name)
        if not success:
            self.song_title_label.configure(text="Failed to parse converted song")
            
    def on_conversion_error(self, err_msg):
        self.load_btn.configure(text="Convert & Load Song", fg_color="#10b981", hover_color="#059669", state="normal")
        self.song_title_label.configure(text="Conversion Error")
        self.song_detail_label.configure(text=f"Error: {err_msg[:40]}...")

    def load_song_file(self, filename):
        playSong.load_song(filename)

    def toggle_play(self):
        if playSong.isPlaying or playSong.paused_by_focus_loss:
            playSong.set_playing(False)
        else:
            playSong.set_playing(True)
        
    def toggle_always_on_top(self):
        self.attributes("-topmost", self.always_on_top_var.get())
        
    def toggle_roblox_only(self):
        playSong.set_roblox_focus_only(self.roblox_only_var.get())
        
    def toggle_legit_mode(self):
        playSong.set_legit_mode(self.legit_var.get())
        
    def on_speed_slider_change(self, value):
        playSong.set_speed(value)
        
    def reset_speed(self):
        playSong.set_speed(playSong.origionalPlaybackSpeed)
        self.speed_slider.set(playSong.origionalPlaybackSpeed)

    # --- Thread-Safe playSong.py Callback Receivers ---
    def cb_play_state(self, is_playing):
        if is_playing:
            self.play_btn.configure(text="PAUSE", fg_color="#ef4444", hover_color="#dc2626")
            self.update_status_badge("Playing")
        else:
            if playSong.paused_by_focus_loss:
                self.play_btn.configure(text="PAUSE", fg_color="#ef4444", hover_color="#dc2626")
                self.update_status_badge("Suspended (Waiting for Roblox Focus)")
            else:
                self.play_btn.configure(text="PLAY", fg_color="#10b981", hover_color="#059669")
                self.update_status_badge("Paused" if playSong.storedIndex > 0 else "Idle")
            
    def cb_progress(self, stored_index, elapsed_time):
        self.total_notes = len(playSong.infoTuple[2]) if (playSong.infoTuple and len(playSong.infoTuple) > 2) else 0
        if self.total_notes > 0:
            percentage = int((stored_index / self.total_notes) * 100)
        else:
            percentage = 0
            
        elapsed_mins, elapsed_secs = divmod(elapsed_time, 60)
        total_mins, total_secs = divmod(self.total_duration, 60)
        
        self.progress_label.configure(
            text=f"Progress: {stored_index} / {self.total_notes} notes ({percentage}%)  |  "
                 f"Time: {int(elapsed_mins)}m {int(elapsed_secs)}s / {int(total_mins)}m {int(total_secs)}s"
        )
        
        if self.total_notes > 0:
            self.progress_bar.set(stored_index / self.total_notes)
        else:
            self.progress_bar.set(0)
            
    def cb_speed(self, speed):
        self.speed_label.configure(text=f"Playback Speed: {speed:.2f}x")
        self.speed_slider.set(speed)
        
    def cb_legit_mode(self, active):
        self.legit_var.set(active)
        
    def cb_song_loaded(self, filename, total_notes, total_duration):
        self.total_notes = total_notes
        self.total_duration = total_duration
        
        total_mins, total_secs = divmod(total_duration, 60)
        
        name = Path(filename).name
        if name.lower().endswith(".mid"):
            name = name[:-4]
        if name.endswith("_piano_only"):
            name = name[:-11]
            
        if name == "song.txt":
            name = "Previously Loaded Song"
            
        if total_notes == 0:
            name = "No Song Loaded"
            self.play_btn.configure(state="disabled")
            self.rewind_btn.configure(state="disabled")
            self.skip_btn.configure(state="disabled")
        else:
            self.play_btn.configure(state="normal")
            self.rewind_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")
            
        self.song_title_label.configure(text=name)
        self.update_status_badge("Idle")
        
        self.progress_label.configure(
            text=f"Progress: 0 / {total_notes} notes (0%)  |  "
                 f"Time: 0m 0s / {int(total_mins)}m {int(total_secs)}s"
        )
        self.progress_bar.set(0)
        
        # Update Reset button text with the original playback speed
        self.reset_speed_btn.configure(text=f"Reset ({playSong.origionalPlaybackSpeed:.1f}x)")
        
    def update_status_badge(self, status):
        self.song_detail_label.configure(
            text=f"Notes: {self.total_notes}  |  Duration: {int(self.total_duration // 60)}m {int(self.total_duration % 60)}s  |  Status: {status}"
        )

    def update_realtime_progress(self):
        import time
        if playSong.isPlaying and not playSong.paused_by_focus_loss:
            # Calculate real-time elapsed time
            elapsed_time = playSong.elapsedTime
            if playSong.last_note_time > 0:
                elapsed_since_last_note = (time.time() - playSong.last_note_time) * playSong.playback_speed
                elapsed_time += elapsed_since_last_note
                
            elapsed_mins, elapsed_secs = divmod(elapsed_time, 60)
            total_mins, total_secs = divmod(self.total_duration, 60)
            
            # Update only the time part of the label to keep it smooth
            stored_index = playSong.storedIndex
            percentage = int((stored_index / self.total_notes) * 100) if self.total_notes > 0 else 0
            self.progress_label.configure(
                text=f"Progress: {stored_index} / {self.total_notes} notes ({percentage}%)  |  "
                     f"Time: {int(elapsed_mins)}m {int(elapsed_secs)}s / {int(total_mins)}m {int(total_secs)}s"
            )
        self.after(100, self.update_realtime_progress)

    def show_scrollbar(self, event=None):
        if hasattr(self, 'hide_scrollbar_timer') and self.hide_scrollbar_timer is not None:
            self.after_cancel(self.hide_scrollbar_timer)
            self.hide_scrollbar_timer = None
        try:
            first, last = self.file_list_frame._scrollbar.get()
            if last - first < 0.99:
                self.file_list_frame._scrollbar.grid()
                self.file_list_frame._parent_canvas.grid_configure(padx=(4, 0))
        except Exception:
            pass

    def hide_scrollbar_delayed(self, event=None):
        if hasattr(self, 'hide_scrollbar_timer') and self.hide_scrollbar_timer is not None:
            self.after_cancel(self.hide_scrollbar_timer)
        self.hide_scrollbar_timer = self.after(150, self.do_hide_scrollbar)

    def do_hide_scrollbar(self):
        self.hide_scrollbar_timer = None
        try:
            self.file_list_frame._scrollbar.grid_remove()
            self.file_list_frame._parent_canvas.grid_configure(padx=(4, 4))
        except Exception:
            pass

    def on_closing(self):
        playSong.set_playing(False)
        if playSong.hotkey_listener:
            playSong.hotkey_listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = RobloxAutoPlayerGUI()
    app.mainloop()
