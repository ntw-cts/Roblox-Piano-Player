# 🎹 Roblox Piano Auto-Player

A sophisticated, modern desktop auto-player client designed for automated, high-precision MIDI playback on virtual pianos in **Roblox**. 

Built with a modern dark-themed interface using **CustomTkinter**, this application simulates keystrokes from any standard MIDI file, allowing you to play complex arrangements flawlessly. It features robust time-based seeking, customizable playback speed, anti-cheat protection options, and global hotkeys.

---

## ✨ Features

- **Sleek Modern UI**: Fully responsive Dark Mode UI built with CustomTkinter.
- **Dual Playback Modes**:
  - **Auto Mode**: Maximum performance playback for complex, fast-tempo MIDI tracks.
  - **Legit Mode**: Adds randomized timing micro-delays between note strikes to emulate natural human touch and avoid anti-cheat/macro detection.
- **Active Window Filter (Roblox Only)**: Restricts keystroke simulation to trigger only when the Roblox game client is the active foreground window.
- **Always on Top Toggle**: Keeps the controller window pinned above your Roblox client for seamless performance management.
- **Smart Song Search & Playlist**: Dynamically loads files from the `midi/` directory, featuring a live search filter.
- **Real-time Playback Status**: Visual progress bar tracking current playhead position, time elapsed, total duration, and total MIDI note count.
- **Precise Speed Control**: Dynamically speed up or slow down song playback from `0.1x` to `5.0x` speed.
- **Time-based Seeking**: Instantly jump forward or backward by `10 seconds` using the UI buttons or global hotkeys.
- **Persistent Song Cache**: Automatically saves the last loaded song path to `song.txt` and recovers the original MIDI filename upon relaunch.

---

## ⌨️ Global Hotkeys

You can control playback globally at any time, even while focused inside the Roblox window:

| Hotkey | Action |
| :--- | :--- |
| **`DELETE`** | Play / Pause playback |
| **`INSERT`** | Toggle **Legit Mode** (anti-cheat protection) |
| **`HOME`** | **Rewind 10 seconds** in current song |
| **`END`** | **Skip 10 seconds** forward in current song |
| **`ESCAPE`** | **Emergency Kill** (instantly terminates the program) |

---

## 📂 Project Structure

```
├── gui.py                      # CustomTkinter graphical interface and hotkey mappings
├── playSong.py                 # Core playback engine, time-seeking, and key simulation
├── pyMIDI.py                   # MIDI parser, key-mapping, and sheet conversion
├── strip.py                    # MIDI track filter (filters non-piano tracks)
└── requirements.txt            # Python package dependencies
```

---

## 🚀 Getting Started

### Method 1: Using the Pre-compiled Executable (Recommended)
1. Go to the **Releases** tab of this GitHub repository and download the latest `RobloxPianoPlayer.exe` executable.
2. Move the downloaded `.exe` file to any folder on your computer.
3. Run `RobloxPianoPlayer.exe`. It will automatically create a `midi` folder right next to itself on its first launch.
4. Put your `.mid` files inside that newly created `midi` folder, click **Scan Folder** in the app, and you are ready to play!

### Method 2: Running from Source
To run or develop the project from source, you need **Python 3.10+** installed:

1. Clone or download this repository.
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Create a folder named `midi` in the root directory and place your `.mid` files inside it.
4. Run the GUI:

   ```bash
   python gui.py
   ```

---

## 🛠️ Compiling to a Standalone Executable
If you modify the source code and want to compile a new `.exe`, run PyInstaller using:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name=RobloxPianoPlayer gui.py
```


---

## 🤝 Credits & Licensing

### Attribution
The core auto-play engine and keyboard layout simulation are built upon and adapted from the original open-source play engine created by **[jOaawd/Roblox-Python-AutoPlayer](https://github.com/jOaawd/Roblox-Python-AutoPlayer)**. 

### License Notice
Please note that the original repository by `jOaawd` does not contain an explicit open-source license file. As a result, default copyright laws apply ("All Rights Reserved" by the original author). 

This project and its modifications are shared publicly under GitHub's standard Terms of Service (permitting viewing and personal/educational forks). Users are advised to use this tool solely for **educational, testing, and personal recreation purposes**.

---

## ⚠️ Disclaimer
This software is intended for personal and educational use. Automatically simulating keyboard inputs in online multiplayer games may violate their Terms of Service. Use responsibly. The developers assume no liability for account suspensions or actions taken by game administrators.
