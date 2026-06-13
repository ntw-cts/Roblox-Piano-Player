import pyMIDI
import threading
import random
from pynput.keyboard import Key, Controller, Listener
import time

global isPlaying
global infoTuple
global storedIndex
global playback_speed
global elapsedTime
global origionalPlaybackSpeed
global speedMultiplier
global legitModeActive
global heldNotes
global robloxFocusOnly
global playback_start_time
global roblox_has_been_focused
global paused_by_focus_loss
global last_note_time
global song_display_name

isPlaying = False
legitModeActive = False
robloxFocusOnly = True
playback_start_time = 0.0
roblox_has_been_focused = False
paused_by_focus_loss = False

storedIndex = 0
elapsedTime = 0
origionalPlaybackSpeed = 1.0
speedMultiplier = 2.0
heldNotes = {}
last_note_time = 0.0
song_display_name = None

active_timers = []
active_timers_lock = threading.Lock()

def start_timer(delay, target, args=None):
    if args is None:
        args = []
    timer = threading.Timer(delay, target, args)
    timer.daemon = True
    with active_timers_lock:
        global active_timers
        active_timers = [t for t in active_timers if t.is_alive()]
        active_timers.append(timer)
    timer.start()
    return timer

def cancel_all_timers():
    global active_timers
    with active_timers_lock:
        for timer in active_timers:
            timer.cancel()
        active_timers = []

def release_all_held_keys():
    global heldNotes
    for key in list(heldNotes.keys()):
        releaseLetter(key)
    heldNotes = {}

def set_roblox_focus_only(active):
    global robloxFocusOnly
    robloxFocusOnly = active
    print(f"Roblox Focus Only set to {robloxFocusOnly}")

# GUI Callbacks
state_callbacks = {
    'play_state': None,      # callback(is_playing: bool)
    'progress': None,        # callback(stored_index: int, elapsed_time: float)
    'speed': None,           # callback(speed: float)
    'legit_mode': None,      # callback(active: bool)
    'song_loaded': None      # callback(song_name: str, total_notes: int, total_duration: float)
}

def trigger_callback(name, *args):
    cb = state_callbacks.get(name)
    if cb:
        try:
            cb(*args)
        except Exception:
            pass

def set_playing(play_state, by_focus_loss=False):
    global isPlaying, playback_start_time, roblox_has_been_focused, paused_by_focus_loss, last_note_time
    if isPlaying == play_state:
        if not play_state and not by_focus_loss:
            if paused_by_focus_loss:
                paused_by_focus_loss = False
                trigger_callback('play_state', isPlaying)
        return
    isPlaying = play_state
    
    if isPlaying:
        paused_by_focus_loss = False
    else:
        paused_by_focus_loss = by_focus_loss
        
    trigger_callback('play_state', isPlaying)
    if isPlaying:
        playback_start_time = time.time()
        roblox_has_been_focused = False
        if robloxFocusOnly:
            print("Waiting for Roblox focus...")
            last_note_time = 0.0
            wait_for_roblox_focus()
        else:
            print("Playing...")
            last_note_time = time.time()
            playNextNote()
    else:
        print("Stopping...")
        cancel_all_timers()
        release_all_held_keys()
        last_note_time = 0.0

def wait_for_roblox_focus():
    global isPlaying, playback_start_time, roblox_has_been_focused, last_note_time
    if not isPlaying:
        return
        
    import sys
    if sys.platform == "win32":
        import ctypes
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            active_title = buff.value
            
            is_roblox = "Roblox" in active_title and "Auto-Player" not in active_title
            
            if is_roblox:
                roblox_has_been_focused = True
                print("Roblox focused. Starting playback...")
                last_note_time = time.time()
                playNextNote()
                return
        except Exception:
            pass
            
    # Timeout after 8 seconds of inactivity (never focusing Roblox)
    if time.time() - playback_start_time > 8.0:
        print("Timeout waiting for Roblox focus. Pausing.")
        set_playing(False)
        return
        
    # Poll focus every 100ms
    start_timer(0.1, wait_for_roblox_focus)

def wait_to_resume_focus():
    global isPlaying, paused_by_focus_loss
    if not paused_by_focus_loss or isPlaying:
        return
        
    import sys
    if sys.platform == "win32":
        import ctypes
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            active_title = buff.value
            
            is_roblox = "Roblox" in active_title and "Auto-Player" not in active_title
            
            if is_roblox:
                print("Roblox refocused. Auto-resuming...")
                paused_by_focus_loss = False
                set_playing(True)
                return
        except Exception:
            pass
            
    # Poll focus every 100ms
    start_timer(0.1, wait_to_resume_focus)

def set_speed(new_speed):
    global playback_speed
    playback_speed = float(new_speed)
    print(f"Playback speed set to {playback_speed:.2f}x")
    trigger_callback('speed', playback_speed)

def set_legit_mode(active):
    global legitModeActive
    legitModeActive = active
    status = "ON" if legitModeActive else "OFF"
    print(f"Legit Mode turned {status}")
    trigger_callback('legit_mode', legitModeActive)

def set_index(index):
    global storedIndex, infoTuple, last_note_time, isPlaying
    if not infoTuple or len(infoTuple) <= 2:
        return
    notes = infoTuple[2]
    storedIndex = max(0, min(index, len(notes)))
    recalculateElapsedTime()
    if isPlaying:
        last_note_time = time.time()
    else:
        last_note_time = 0.0
    print(f"Seeked to note index: {storedIndex}")
    trigger_callback('progress', storedIndex, elapsedTime)

def recalculateElapsedTime():
    global elapsedTime, storedIndex, infoTuple
    if infoTuple and len(infoTuple) > 2:
        notes = infoTuple[2]
        elapsedTime = sum(floorToZero(n[0]) for n in notes[:storedIndex])

conversionCases = {'!': '1', '@': '2', '£': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0'}

keyboardController = Controller()

key_delete = 'delete'
key_shift = 'shift'
key_end = 'end'
key_home = 'home'
key_load = 'f5'
key_speed_up = 'page_up'
key_slow_down = 'page_down'
key_legit_mode = 'insert'

def runPyMIDI():
    try:
        pyMIDI.main()
    except Exception as e:
        print(f"pyMIDI.py was interrupted or encountered an error: {e}")

def toggleLegitMode(event):
    global legitModeActive
    set_legit_mode(not legitModeActive)

def calculateTotalDuration(notes):
    total_duration = sum([note[0] for note in notes])
    return total_duration

def onDelPress():
    global isPlaying
    set_playing(not isPlaying)

def isShifted(charIn):
    asciiValue = ord(charIn)
    if asciiValue >= 65 and asciiValue <= 90:
        return True
    if charIn in "!@#$%^&*()_+{}|:\"<>?":
        return True
    return False

def speedUp(event):
    global playback_speed
    set_speed(playback_speed * speedMultiplier)

def slowDown(event):
    global playback_speed
    set_speed(playback_speed / speedMultiplier)

def pressLetter(strLetter):
    if isShifted(strLetter):
        if strLetter in conversionCases:
            strLetter = conversionCases[strLetter]
        keyboardController.release(strLetter.lower())
        keyboardController.press(Key.shift)
        keyboardController.press(strLetter.lower())
        keyboardController.release(Key.shift)
    else:
        keyboardController.release(strLetter)
        keyboardController.press(strLetter)
    return
    
def releaseLetter(strLetter):
    if isShifted(strLetter):
        if strLetter in conversionCases:
            strLetter = conversionCases[strLetter]
        keyboardController.release(strLetter.lower())
    else:
        keyboardController.release(strLetter)
    return
    
def processFile(filename="song.txt"):
    global playback_speed, song_display_name
    song_display_name = None
    with open(filename, "r") as macro_file:
        lines = macro_file.read().split("\n")
        tOffsetSet = False
        tOffset = 0

        if len(lines) > 0 and "=" in lines[0]:
            try:
                playback_speed = float(lines[0].split("=")[1])
                print("Playback speed is set to %.2f" % playback_speed)
            except ValueError:
                print("Error: Invalid playback speed value")
                return None
        else:
            print("Error: Invalid playback speed format")
            return None

        tempo = None
        processedNotes = []
        
        for line in lines[1:]:
            if line.startswith("#original_midi="):
                song_display_name = line.split("=", 1)[1].strip()
                continue
            if 'tempo' in line:
                try:
                    tempo = 60 / float(line.split("=")[1])
                except ValueError:
                    print("Error: Invalid tempo value")
                    return None
            else:
                l = line.split(" ")
                if len(l) < 2:
                    continue
                try:
                    waitToPress = float(l[0])
                    notes = l[1]
                    processedNotes.append([waitToPress, notes])
                    if not tOffsetSet:
                        tOffset = waitToPress
                        tOffsetSet = True
                except ValueError:
                    print("Error: Invalid note format")
                    continue

        if tempo is None:
            print("Error: Tempo not specified")
            return None

    return [tempo, tOffset, processedNotes, []]

def floorToZero(i):
    if i > 0:
        return i
    else:
        return 0

# for this method, we instead use delays as l[0] and work using indexes with delays instead of time
# we'll use recursion and threading to press keys
def parseInfo():
    tempo = infoTuple[0]
    notes = infoTuple[2][1:]
    
    if len(notes) == 0:
        return []
    
    # parse time between each note
    # while loop is required because we are editing the array as we go
    i = 0
    while i < len(notes) - 1:
        note = notes[i]
        nextNote = notes[i + 1]
        if "tempo" in note[1]:
            tempo = 60 / float(note[1].split("=")[1])
            notes.pop(i)

            note = notes[i]
            if i < len(notes) - 1:
                nextNote = notes[i + 1]
        else:
            note[0] = (nextNote[0] - note[0]) * tempo
            i += 1

    # let's just hold the last note for 1 second because we have no data on it
    notes[len(notes) - 1][0] = 1.00

    return notes

def adjustTempoForCurrentNote():
    global isPlaying, storedIndex, playback_speed, elapsedTime, legitModeActive
    if len(infoTuple) > 3:
        tempo_changes = infoTuple[3]

        for change in tempo_changes:
            if change[0] == storedIndex:
                new_tempo = change[1]
                set_speed(new_tempo / origionalPlaybackSpeed)

def playNextNote():
    global isPlaying, storedIndex, playback_speed, elapsedTime, legitModeActive, heldNotes, robloxFocusOnly, paused_by_focus_loss, last_note_time

    # Focus check - pause if Roblox is not the active window
    if isPlaying and robloxFocusOnly:
        import sys
        if sys.platform == "win32":
            import ctypes
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                active_title = buff.value
                
                is_roblox = "Roblox" in active_title and "Auto-Player" not in active_title
                
                if not is_roblox:
                    print(f"Focus lost: Active window is '{active_title}'. Auto-pausing.")
                    set_playing(False, by_focus_loss=True)
                    wait_to_resume_focus()
                    return
            except Exception:
                pass

    adjustTempoForCurrentNote()
    
    notes = infoTuple[2]
    total_duration = calculateTotalDuration(notes)

    if isPlaying and storedIndex < len(notes):
        noteInfo = notes[storedIndex]
        delay = floorToZero(noteInfo[0])
        note_keys = noteInfo[1]
        
        last_note_time = time.time()
        
        # Legit Mode
        if legitModeActive:
            delay_variation = random.uniform(0.90, 1.10)
            delay *= delay_variation

            if random.random() < 0.05:
                if random.random() < 0.5 and len(note_keys) > 1:
                    note_keys = note_keys[1:]
                else:
                    if storedIndex == 0 or notes[storedIndex - 1][0] > 0.3:
                        delay += random.uniform(0.1, 0.5)

        recalculateElapsedTime()

        # Press or release keys based on the presence of "~"
        if "~" in note_keys:
            for n in note_keys.replace("~", ""):
                releaseLetter(n)
                if n in heldNotes:
                    del heldNotes[n]
        else:
            for n in note_keys:
                pressLetter(n)
                heldNotes[n] = noteInfo[0]

            # Schedule release of held notes
            start_timer(noteInfo[0] / playback_speed, releaseHeldNotes, [note_keys])

        if "~" not in note_keys:
            elapsed_mins, elapsed_secs = divmod(elapsedTime, 60)
            total_mins, total_secs = divmod(total_duration, 60)
            print(f"[{int(elapsed_mins)}m {int(elapsed_secs)}s/{int(total_mins)}m {int(total_secs)}s] {note_keys}")
            trigger_callback('progress', storedIndex, elapsedTime)

        storedIndex += 1
        if delay == 0:
            playNextNote()
        else:
            start_timer(delay / playback_speed, playNextNote)
    elif storedIndex >= len(notes):
        isPlaying = False
        storedIndex = 0
        elapsedTime = 0
        trigger_callback('play_state', False)
        trigger_callback('progress', storedIndex, elapsedTime)

def releaseHeldNotes(note_keys):
    global heldNotes
    for n in note_keys:
        if n in heldNotes:
            releaseLetter(n)
            if n in heldNotes:
                del heldNotes[n]

def seek_by_time(offset):
    global storedIndex, elapsedTime, infoTuple, isPlaying, last_note_time
    if not infoTuple or len(infoTuple) <= 2:
        return
    notes = infoTuple[2]
    
    # Calculate current elapsed time
    recalculateElapsedTime()
    current_t = elapsedTime
    if isPlaying and last_note_time > 0:
        elapsed_since_last_note = (time.time() - last_note_time) * playback_speed
        current_t += elapsed_since_last_note
        
    target_t = max(0.0, current_t + offset)
    
    best_index = 0
    best_diff = float('inf')
    accumulated = 0.0
    
    for idx, note in enumerate(notes):
        diff = abs(accumulated - target_t)
        if diff < best_diff:
            best_diff = diff
            best_index = idx
        accumulated += floorToZero(note[0])
        
    # Check the end of song
    diff = abs(accumulated - target_t)
    if diff < best_diff:
        best_diff = diff
        best_index = len(notes)
        
    total_duration = calculateTotalDuration(notes)
    if target_t >= total_duration:
        set_playing(False)
        set_index(0)
    else:
        set_index(best_index)

def rewind(KeyboardEvent):
    seek_by_time(-10)

def skip(KeyboardEvent):
    seek_by_time(10)

def onKeyPress(key):
    global isPlaying, storedIndex, playback_speed, legitModeActive

    try:
        if key == Key.delete:
            onDelPress()
        elif key == Key.home:
            seek_by_time(-10)
        elif key == Key.end:
            seek_by_time(10)
        elif key == Key.page_up:
            speedUp(None)
        elif key == Key.page_down:
            slowDown(None)
        elif key == Key.insert:
            toggleLegitMode(None)
        elif key == Key.f5:
            runPyMIDI()
        elif key == Key.esc:
            print("Emergency stop triggered. Exiting...")
            release_all_held_keys()
            import os
            os._exit(0)
    except AttributeError:
        pass

def printControls():
    title = "Controls"
    controls = [
        ("DELETE", "Play/Pause"),
        ("HOME", "Rewind"),
        ("END", "Advance"),
        ("PAGE UP", "Speed Up"),
        ("PAGE DOWN", "Slow Down"),
        ("INSERT", "Toggle Legit Mode"),
        ("F5", "Load New Song (NOT RECOMMENDED)"),
        ("ESC", "Exit")
    ]

    print(f"\n{'=' * 20}\n{title.center(20)}\n{'=' * 20}")

    for key, action in controls:
        print(f"{key.ljust(10)} : {action}")

    print(f"{'=' * 20}\n")

def load_song(filename, display_name=None):
    global infoTuple, storedIndex, elapsedTime, playback_speed, origionalPlaybackSpeed, song_display_name
    infoTuple = processFile(filename)
    if infoTuple is None:
        return False
    infoTuple[2] = parseInfo()
    storedIndex = 0
    elapsedTime = 0
    
    origionalPlaybackSpeed = playback_speed
    total_duration = calculateTotalDuration(infoTuple[2])
    total_notes = len(infoTuple[2])
    
    if display_name is None:
        if song_display_name:
            from pathlib import Path
            display_name = Path(song_display_name).stem
        else:
            from pathlib import Path
            display_name = Path(filename).name
        
    trigger_callback('song_loaded', display_name, total_notes, total_duration)
    trigger_callback('progress', storedIndex, elapsedTime)
    trigger_callback('speed', playback_speed)
    return True

hotkey_listener = None

def start_hotkey_listener():
    global hotkey_listener
    if hotkey_listener is None:
        hotkey_listener = Listener(on_press=onKeyPress)
        hotkey_listener.start()

def main():
    global isPlaying, infoTuple, playback_speed

    infoTuple = processFile()
    if infoTuple is None:
        return

    infoTuple[2] = parseInfo()

    printControls()

    with Listener(on_press=onKeyPress) as listener:
        listener.join()
            
if __name__ == "__main__":
    main()
