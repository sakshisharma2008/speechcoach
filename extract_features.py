
from pathlib import Path

import librosa
import numpy as np
import pandas as pd

# Project paths
audio_path = Path("dataset/audio/ideal/ideal_001.mp3")
output_path = Path("dataset/features/ideal_001_features.csv")

if not audio_path.exists():
    raise FileNotFoundError(f"Audio not found: {audio_path}")

print("Loading audio...")

# Load audio as mono at 22050 Hz
audio, sr = librosa.load(
    str(audio_path),
    sr=22050,
    mono=True
)

duration = len(audio) / sr

print(f"Audio duration: {duration:.2f} seconds")
print("Extracting speech features...")

# 1. Pitch (fundamental frequency), in Hz
pitch = librosa.yin(
    audio,
    fmin=65,
    fmax=400,
    sr=sr
)

valid_pitch = pitch[
    np.isfinite(pitch) &
    (pitch >= 65) &
    (pitch <= 400)
]

mean_pitch = (
    float(np.mean(valid_pitch))
    if len(valid_pitch) else 0.0
)

pitch_variation = (
    float(np.std(valid_pitch))
    if len(valid_pitch) else 0.0
)

# 2. Short-time RMS energy
rms = librosa.feature.rms(y=audio)[0]
mean_energy = float(np.mean(rms))
energy_variation = float(np.std(rms))

# 3. Silence and pause estimate
interval = 512 / sr
quiet_frames = rms < 0.015

# Count transitions from non-quiet to quiet
pause_starts = np.where(
    quiet_frames[1:] & ~quiet_frames[:-1]
)[0] + 1

pause_count = len(pause_starts)
quiet_duration = float(np.sum(quiet_frames) * interval)

# 4. Speaking rate estimate using Whisper transcription
transcript_path = Path(
    "dataset/annotations/ideal_001_transcription.txt"
)

word_count = 0

if transcript_path.exists():
    transcript = transcript_path.read_text(
        encoding="utf-8"
    ).strip()
    word_count = len(transcript.split())

speaking_rate_wpm = (
    word_count / (duration / 60)
    if duration > 0 and word_count > 0
    else 0.0
)

# 5. MFCC acoustic features
mfcc = librosa.feature.mfcc(
    y=audio,
    sr=sr,
    n_mfcc=13
)

# Store summary statistics
features = {
    "sample_id": "ideal_001",
    "label": "ideal",
    "duration_seconds": duration,
    "transcript_word_count": word_count,
    "estimated_speaking_rate_wpm": speaking_rate_wpm,
    "mean_pitch_hz": mean_pitch,
    "pitch_variation_hz": pitch_variation,
    "mean_rms_energy": mean_energy,
    "rms_energy_variation": energy_variation,
    "quiet_time_estimate_seconds": quiet_duration,
    "quiet_transition_count": pause_count,
}

for i in range(mfcc.shape[0]):
    features[f"mfcc_{i + 1}_mean"] = float(
        np.mean(mfcc[i])
    )
    features[f"mfcc_{i + 1}_std"] = float(
        np.std(mfcc[i])
    )

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

pd.DataFrame([features]).to_csv(
    output_path,
    index=False
)

print("\nFeature extraction complete!")
print("Saved to:", output_path)
print("\nKey features:")

for name, value in features.items():
    if isinstance(value, float):
        print(f"{name}: {value:.3f}")
    else:
        print(f"{name}: {value}")
