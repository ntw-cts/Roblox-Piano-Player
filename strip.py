import mido
import glob
import sys
from pathlib import Path

# Keywords that are considered "piano-like" (case-insensitive)
PIANO_KEYWORDS = [
    'piano', 'keyboard', 'keys', 'grand', 'upright',
    'clav', 'clavier', 'pno', 'kbrd', 'pianoforte',
    'electric piano', 'e-piano', 'ep ', 'rhodes', 'wurlitzer',
    'organ', 'hammond', 'pipe organ', 'church organ', 'org',
]

def is_piano_track(track_name: str) -> bool:
    name = track_name.lower().strip()
    return any(kw in name for kw in PIANO_KEYWORDS)

def strip_midi(input_path: str) -> str:
    mid = mido.MidiFile(input_path)
    new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat, type=mid.type)

    kept = []

    # Track 0 always kept (tempo map / metadata)
    if len(mid.tracks) > 0:
        new_mid.tracks.append(mid.tracks[0])

    for track in mid.tracks[1:]:
        track_name = track.name if hasattr(track, 'name') else ''
        if is_piano_track(track_name):
            new_mid.tracks.append(track)
            kept.append(repr(track_name))

    # Fallback: if no piano-like tracks were matched, keep all tracks
    if not kept:
        new_mid.tracks = list(mid.tracks)
        kept = [repr(track.name if hasattr(track, 'name') else '') for track in mid.tracks[1:]]

    # Build output filename next to the original file
    src = Path(input_path)
    out_path = src.parent / f"{src.stem}_piano_only{src.suffix}"
    new_mid.save(str(out_path))

    status = f"  kept tracks: {', '.join(kept)}" if kept else "  WARNING: no piano-like tracks found — only metadata track saved"
    print(f"[OK] {src.name}\n{status}\n  -> {out_path.name}")
    return str(out_path)

def main():
    # Accept paths/globs from CLI args, or fall back to asking the user
    patterns = sys.argv[1:] if len(sys.argv) > 1 else None

    if not patterns:
        raw = input("Enter MIDI file path(s) or glob (e.g. D:\\midi\\*.mid): ").strip()
        patterns = [raw]

    files = []
    for pattern in patterns:
        matched = glob.glob(pattern, recursive=True)
        if matched:
            files.extend(matched)
        else:
            # Treat as literal path if glob finds nothing
            files.append(pattern)

    files = list(dict.fromkeys(files))  # deduplicate, preserve order

    if not files:
        print("No files found.")
        return

    print(f"\nProcessing {len(files)} file(s)...\n")
    for f in files:
        try:
            strip_midi(f)
        except FileNotFoundError:
            print(f"[SKIP] File not found: {f}")
        except Exception as e:
            print(f"[ERR]  {f}: {e}")

if __name__ == "__main__":
    main()
