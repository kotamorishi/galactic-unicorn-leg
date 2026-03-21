"""Sound preset definitions.

Each preset is a list of note dicts played in sequence.
Note dict keys:
    channel     - synth channel (0-based)
    waveform    - "square", "sine", "triangle", "sawtooth", "noise"
    frequency   - Hz
    volume      - 0.0 to 1.0
    attack      - seconds
    decay       - seconds
    sustain     - 0.0 to 1.0
    release     - seconds
    duration_ms - how long to hold the note (ms)
    pause_ms    - pause after note before next (ms)
"""

PRESETS = {
    # --- Notifications ---
    1: {
        "name": "Simple Beep",
        "category": "notification",
        "notes": [
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 150, "pause_ms": 0},
        ],
    },
    2: {
        "name": "Double Beep",
        "category": "notification",
        "notes": [
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 100, "pause_ms": 80},
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 100, "pause_ms": 0},
        ],
    },
    3: {
        "name": "Triple Beep",
        "category": "notification",
        "notes": [
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 80, "pause_ms": 60},
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 80, "pause_ms": 60},
            {"frequency": 880, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.1,
             "duration_ms": 80, "pause_ms": 0},
        ],
    },
    4: {
        "name": "Rising Chime",
        "category": "notification",
        "notes": [
            {"frequency": 523, "waveform": "sine", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.2,
             "duration_ms": 200, "pause_ms": 50},
            {"frequency": 784, "waveform": "sine", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    5: {
        "name": "Falling Chime",
        "category": "notification",
        "notes": [
            {"frequency": 784, "waveform": "sine", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.2,
             "duration_ms": 200, "pause_ms": 50},
            {"frequency": 523, "waveform": "sine", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    6: {
        "name": "Three-tone Chime",
        "category": "notification",
        "notes": [
            {"frequency": 523, "waveform": "sine", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.2,
             "duration_ms": 200, "pause_ms": 30},
            {"frequency": 659, "waveform": "sine", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.2,
             "duration_ms": 200, "pause_ms": 30},
            {"frequency": 784, "waveform": "sine", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },

    # --- Alarms ---
    7: {
        "name": "Alarm (Low)",
        "category": "alarm",
        "notes": [
            {"frequency": 330, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 200, "pause_ms": 200},
            {"frequency": 330, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 200, "pause_ms": 200},
            {"frequency": 330, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 200, "pause_ms": 0},
        ],
    },
    8: {
        "name": "Alarm (High)",
        "category": "alarm",
        "notes": [
            {"frequency": 1047, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 150, "pause_ms": 150},
            {"frequency": 1047, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 150, "pause_ms": 150},
            {"frequency": 1047, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.05, "sustain": 0.8, "release": 0.05,
             "duration_ms": 150, "pause_ms": 0},
        ],
    },
    9: {
        "name": "Siren",
        "category": "alarm",
        "notes": [
            {"frequency": 660, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.1, "decay": 0.1, "sustain": 0.6, "release": 0.1,
             "duration_ms": 300, "pause_ms": 0},
            {"frequency": 880, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.1, "decay": 0.1, "sustain": 0.6, "release": 0.1,
             "duration_ms": 300, "pause_ms": 0},
            {"frequency": 660, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.1, "decay": 0.1, "sustain": 0.6, "release": 0.1,
             "duration_ms": 300, "pause_ms": 0},
            {"frequency": 880, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.1, "decay": 0.1, "sustain": 0.6, "release": 0.1,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    10: {
        "name": "Urgent Alert",
        "category": "alarm",
        "notes": [
            {"frequency": 1200, "waveform": "square", "volume": 0.7,
             "attack": 0.005, "decay": 0.02, "sustain": 0.8, "release": 0.02,
             "duration_ms": 80, "pause_ms": 40},
            {"frequency": 1200, "waveform": "square", "volume": 0.7,
             "attack": 0.005, "decay": 0.02, "sustain": 0.8, "release": 0.02,
             "duration_ms": 80, "pause_ms": 40},
            {"frequency": 1200, "waveform": "square", "volume": 0.7,
             "attack": 0.005, "decay": 0.02, "sustain": 0.8, "release": 0.02,
             "duration_ms": 80, "pause_ms": 40},
            {"frequency": 1200, "waveform": "square", "volume": 0.7,
             "attack": 0.005, "decay": 0.02, "sustain": 0.8, "release": 0.02,
             "duration_ms": 80, "pause_ms": 40},
            {"frequency": 1200, "waveform": "square", "volume": 0.7,
             "attack": 0.005, "decay": 0.02, "sustain": 0.8, "release": 0.02,
             "duration_ms": 80, "pause_ms": 0},
        ],
    },

    # --- Melodies ---
    11: {
        "name": "Westminster Chime",
        "category": "melody",
        "notes": [
            {"frequency": 659, "waveform": "sine", "volume": 0.4,
             "attack": 0.02, "decay": 0.15, "sustain": 0.3, "release": 0.3,
             "duration_ms": 400, "pause_ms": 50},
            {"frequency": 523, "waveform": "sine", "volume": 0.4,
             "attack": 0.02, "decay": 0.15, "sustain": 0.3, "release": 0.3,
             "duration_ms": 400, "pause_ms": 50},
            {"frequency": 587, "waveform": "sine", "volume": 0.4,
             "attack": 0.02, "decay": 0.15, "sustain": 0.3, "release": 0.3,
             "duration_ms": 400, "pause_ms": 50},
            {"frequency": 392, "waveform": "sine", "volume": 0.4,
             "attack": 0.02, "decay": 0.15, "sustain": 0.3, "release": 0.5,
             "duration_ms": 600, "pause_ms": 0},
        ],
    },
    12: {
        "name": "Do Re Mi Fa",
        "category": "melody",
        "notes": [
            {"frequency": 523, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.15,
             "duration_ms": 200, "pause_ms": 30},
            {"frequency": 587, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.15,
             "duration_ms": 200, "pause_ms": 30},
            {"frequency": 659, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.15,
             "duration_ms": 200, "pause_ms": 30},
            {"frequency": 698, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.3,
             "duration_ms": 400, "pause_ms": 0},
        ],
    },
    13: {
        "name": "Fanfare",
        "category": "melody",
        "notes": [
            {"frequency": 523, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.1,
             "duration_ms": 150, "pause_ms": 30},
            {"frequency": 659, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.1,
             "duration_ms": 150, "pause_ms": 30},
            {"frequency": 784, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.05, "sustain": 0.6, "release": 0.1,
             "duration_ms": 150, "pause_ms": 30},
            {"frequency": 1047, "waveform": "square", "volume": 0.6,
             "attack": 0.01, "decay": 0.1, "sustain": 0.7, "release": 0.4,
             "duration_ms": 500, "pause_ms": 0},
        ],
    },
    14: {
        "name": "Music Box",
        "category": "melody",
        "notes": [
            {"frequency": 784, "waveform": "sine", "volume": 0.3,
             "attack": 0.01, "decay": 0.2, "sustain": 0.2, "release": 0.4,
             "duration_ms": 400, "pause_ms": 100},
            {"frequency": 659, "waveform": "sine", "volume": 0.3,
             "attack": 0.01, "decay": 0.2, "sustain": 0.2, "release": 0.4,
             "duration_ms": 400, "pause_ms": 100},
            {"frequency": 784, "waveform": "sine", "volume": 0.3,
             "attack": 0.01, "decay": 0.2, "sustain": 0.2, "release": 0.6,
             "duration_ms": 600, "pause_ms": 0},
        ],
    },

    # --- Sound Effects ---
    15: {
        "name": "Coin",
        "category": "sfx",
        "notes": [
            {"frequency": 988, "waveform": "square", "volume": 0.4,
             "attack": 0.005, "decay": 0.05, "sustain": 0.2, "release": 0.1,
             "duration_ms": 80, "pause_ms": 10},
            {"frequency": 1319, "waveform": "square", "volume": 0.4,
             "attack": 0.005, "decay": 0.1, "sustain": 0.3, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    16: {
        "name": "Power Up",
        "category": "sfx",
        "notes": [
            {"frequency": 392, "waveform": "square", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.05,
             "duration_ms": 100, "pause_ms": 20},
            {"frequency": 523, "waveform": "square", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.05,
             "duration_ms": 100, "pause_ms": 20},
            {"frequency": 659, "waveform": "square", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.05,
             "duration_ms": 100, "pause_ms": 20},
            {"frequency": 784, "waveform": "square", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.05,
             "duration_ms": 100, "pause_ms": 20},
            {"frequency": 1047, "waveform": "square", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    17: {
        "name": "Level Up",
        "category": "sfx",
        "notes": [
            {"frequency": 523, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.05,
             "duration_ms": 80, "pause_ms": 10},
            {"frequency": 659, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.05,
             "duration_ms": 80, "pause_ms": 10},
            {"frequency": 784, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.05,
             "duration_ms": 80, "pause_ms": 10},
            {"frequency": 1047, "waveform": "triangle", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.3, "release": 0.05,
             "duration_ms": 80, "pause_ms": 10},
            {"frequency": 1319, "waveform": "triangle", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.4, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    18: {
        "name": "Error",
        "category": "sfx",
        "notes": [
            {"frequency": 200, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.1,
             "duration_ms": 250, "pause_ms": 50},
            {"frequency": 150, "waveform": "sawtooth", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.2,
             "duration_ms": 350, "pause_ms": 0},
        ],
    },
    19: {
        "name": "Success",
        "category": "sfx",
        "notes": [
            {"frequency": 523, "waveform": "sine", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.1,
             "duration_ms": 120, "pause_ms": 30},
            {"frequency": 659, "waveform": "sine", "volume": 0.4,
             "attack": 0.01, "decay": 0.05, "sustain": 0.4, "release": 0.1,
             "duration_ms": 120, "pause_ms": 30},
            {"frequency": 1047, "waveform": "sine", "volume": 0.5,
             "attack": 0.01, "decay": 0.1, "sustain": 0.5, "release": 0.3,
             "duration_ms": 300, "pause_ms": 0},
        ],
    },
    20: {
        "name": "Click",
        "category": "sfx",
        "notes": [
            {"frequency": 1500, "waveform": "noise", "volume": 0.3,
             "attack": 0.001, "decay": 0.02, "sustain": 0.0, "release": 0.02,
             "duration_ms": 30, "pause_ms": 0},
        ],
    },
}

VALID_WAVEFORMS = ("square", "sine", "triangle", "sawtooth", "noise")


def get_preset(preset_id):
    """Get a preset by ID. Returns None if not found."""
    return PRESETS.get(preset_id)


def get_preset_list():
    """Return list of {id, name, category} for all presets."""
    result = []
    for pid in sorted(PRESETS.keys()):
        p = PRESETS[pid]
        result.append({
            "id": pid,
            "name": p["name"],
            "category": p["category"],
        })
    return result
