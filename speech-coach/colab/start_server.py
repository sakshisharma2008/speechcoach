
# ============================================================
# SPEECH COACH AI — FINAL COLAB BACKEND
# Original features preserved + startup/debugging fixes
# ============================================================

!pip -q install fastapi uvicorn python-multipart assemblyai gtts librosa matplotlib numpy pandas soundfile

import os
import re
import sys
import time
import subprocess
from pathlib import Path
from google.colab import userdata

def show_meter(title, value, low, high, unit, description):
    st.markdown(f"### {title}")

    if value is None:
        st.info("Meter unavailable for this recording.")
        return

    value = float(value)

    # Keep the visual position inside the meter's range.
    display_value = max(low, min(high, value))
    percentage = (display_value - low) / (high - low) * 100

    st.markdown(
        f"""
        <div style="
            background:#e5e7eb;
            height:14px;
            border-radius:20px;
            overflow:hidden;
            margin:8px 0;
        ">
            <div style="
                width:{percentage:.1f}%;
                height:14px;
                background:#7c3aed;
                border-radius:20px;
            "></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"**Measured:** {value:.2f} {unit}  \n"
        f"**Target range:** {low}–{high} {unit}  \n"
        f"{description}"
    )


# ------------------------------------------------------------
# 1. ASSEMBLYAI API KEY
# Add ASSEMBLYAI_API_KEY in Colab Secrets before running.
# Never put the key directly in public code.
# ------------------------------------------------------------

api_key = userdata.get("ASSEMBLYAI_API_KEY")
if not api_key:
    raise ValueError(
        "ASSEMBLYAI_API_KEY missing. Open Colab Secrets, "
        "add the key, enable notebook access, and rerun."
    )

os.environ["ASSEMBLYAI_API_KEY"] = api_key

# ------------------------------------------------------------
# 2. ORIGINAL BACKEND + FIXES
# ------------------------------------------------------------

SERVER_CODE = r'''
import base64
import io
import os
import tempfile
import traceback

import assemblyai as aai
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS

# ---------------- APP ----------------

API_KEY = os.environ.get("ASSEMBLYAI_API_KEY")
if not API_KEY:
    raise RuntimeError("ASSEMBLYAI_API_KEY is missing.")

aai.settings.api_key = API_KEY

app = FastAPI(title="Speech Coach AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- IDEAL RANGES ----------------

IDEAL = {
    "pitch": (-4, 4),
    "energy": (-6, 6),
    "pitch_var": (1.0, 6.0),
    "rate": (1.8, 3.3),
}

LABELS = {
    "pitch": "Pitch\n(semitones)",
    "energy": "Energy\n(dB)",
    "pitch_var": "Pitch variation\n(semitones)",
    "rate": "Speech rate\n(words/s)",
}

ISSUE_TEXT = {
    ("pitch", 1): "Your voice is too high (may sound tense/anxious)",
    ("pitch", -1): "Your voice is too low (may sound tired/unsure)",
    ("energy", 1): "Your voice is too loud (may sound forceful)",
    ("energy", -1): "Your voice is too quiet (may be difficult to hear)",
    ("pitch_var", -1): "Monotone: your voice stays almost the same",
    ("pitch_var", 1): "Too much variation in your voice",
    ("rate", 1): "You are speaking too fast",
    ("rate", -1): "Too slow / long hesitations",
}

STEP_S = 0.5
WINDOW_S = 3.0
MIN_REGION_S = 2.0


# ---------------- STEP 1: TRANSCRIPTION ----------------

def get_transcript(audio_path, lang):
    print("DEBUG: Starting transcription", flush=True)
    print("DEBUG: Audio size:", os.path.getsize(audio_path), flush=True)
    print("DEBUG: Language:", lang, flush=True)

    config = aai.TranscriptionConfig(language_code=lang)
    transcript = aai.Transcriber().transcribe(
        audio_path,
        config=config
    )

    print("DEBUG: Status:", transcript.status, flush=True)
    print("DEBUG: Error:", transcript.error, flush=True)
    print("DEBUG: Transcript:", repr(transcript.text), flush=True)

    if transcript.status != aai.TranscriptStatus.completed:
        raise RuntimeError(
            f"AssemblyAI transcription failed: {transcript.error}"
        )

    sentences = [
        {
            "text": s.text,
            "start": s.start / 1000.0,
            "end": s.end / 1000.0
        }
        for s in transcript.get_sentences()
    ]

    words = [
        {"start": w.start / 1000.0}
        for w in (transcript.words or [])
    ]

    print("DEBUG: Sentence count:", len(sentences), flush=True)
    print("DEBUG: Word count:", len(words), flush=True)

    # Keep transcript if sentence segmentation returns nothing.
    if not sentences and transcript.text:
        sentences = [{
            "text": transcript.text,
            "start": 0.0,
            "end": 0.0
        }]

    return sentences, words


# ---------------- STEP 2: AUDIO FEATURES ----------------

def extract_curves(audio_path):
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    if len(y) == 0:
        raise ValueError("No readable audio found in uploaded file.")

    hop = 512

    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sr,
        hop_length=hop
    )

    rms = librosa.feature.rms(
        y=y,
        frame_length=2048,
        hop_length=hop
    )[0]

    n = min(len(f0), len(rms))
    f0 = np.asarray(f0[:n], dtype=float)
    rms = np.asarray(rms[:n], dtype=float)

    times = librosa.times_like(
        f0,
        sr=sr,
        hop_length=hop
    )

    valid_pitch = f0[np.isfinite(f0) & (f0 > 0)]

    if len(valid_pitch):
        median_pitch = np.median(valid_pitch)
        pitch = 12 * np.log2(f0 / median_pitch)
    else:
        pitch = np.full(len(f0), np.nan)

    pitch[~np.isfinite(pitch)] = np.nan

    db = librosa.amplitude_to_db(
        rms,
        ref=1.0
    )

    speaking = np.isfinite(db) & (db > db.max() - 35)

    if np.any(speaking):
        energy = np.where(
            speaking,
            db - np.median(db[speaking]),
            np.nan
        )
    else:
        energy = np.full(len(db), np.nan)

    return {
        "times": times,
        "pitch": pitch,
        "energy": energy,
        "duration": len(y) / sr
    }


# ---------------- STEP 3A: SENTENCE ANALYSIS ----------------

def analyze_sentences(sentences, curves):
    rows = []

    for s in sentences:
        start = float(s["start"])
        end = float(s["end"])

        # Avoid invalid intervals for a fallback transcript.
        if end <= start:
            end = min(
                curves["duration"],
                start + 1.0
            )

        part = (
            (curves["times"] >= start)
            & (curves["times"] <= end)
        )

        duration = max(end - start, 0.1)

        pitch_values = curves["pitch"][part]
        energy_values = curves["energy"][part]

        rows.append({
            "sentence": s["text"],
            "start": start,
            "end": end,
            "rate": len(s["text"].split()) / duration,
            "pitch": (
                float(np.nanmean(pitch_values))
                if np.isfinite(pitch_values).any()
                else np.nan
            ),
            "pitch_var": (
                float(np.nanstd(pitch_values, ddof=1))
                if np.isfinite(pitch_values).sum() > 1
                else np.nan
            ),
            "energy": (
                float(np.nanmean(energy_values))
                if np.isfinite(energy_values).any()
                else np.nan
            ),
        })

    return rows


def get_tips(row):
    tips = []

    if row["rate"] > IDEAL["rate"][1]:
        tips.append(
            "Speak a little slower and take short pauses between words"
        )
    elif row["rate"] < IDEAL["rate"][0]:
        tips.append(
            "Speak a little faster and maintain a smooth flow"
        )

    if pd.notna(row["pitch"]):
        if row["pitch"] > IDEAL["pitch"][1]:
            tips.append(
                "Your pitch is high; relax and speak naturally"
            )
        elif row["pitch"] < IDEAL["pitch"][0]:
            tips.append(
                "Your pitch is low; add natural vocal energy"
            )

    if pd.notna(row["energy"]):
        if row["energy"] > IDEAL["energy"][1]:
            tips.append(
                "Your voice is loud; try a more comfortable volume"
            )
        elif row["energy"] < IDEAL["energy"][0]:
            tips.append(
                "Project your voice more clearly"
            )

    if pd.notna(row["pitch_var"]):
        if row["pitch_var"] < IDEAL["pitch_var"][0]:
            tips.append(
                "Vary your pitch on important words to sound less monotone"
            )
        elif row["pitch_var"] > IDEAL["pitch_var"][1]:
            tips.append(
                "Aim for more controlled pitch variation"
            )

    if not tips:
        tips.append(
            "Keep practising and maintain a natural speaking style"
        )

    return tips


# ---------------- STEP 3B: TIMELINE ----------------

def build_timeline(curves, words):
    frames = pd.DataFrame({
        "t": curves["times"],
        "pitch": curves["pitch"],
        "energy": curves["energy"]
    })

    word_starts = np.array(
        [w["start"] for w in words],
        dtype=float
    )

    rows = []

    for t in np.arange(0, curves["duration"], STEP_S):
        lo = max(0.0, t - WINDOW_S / 2)
        hi = min(
            curves["duration"],
            t + WINDOW_S / 2
        )

        win = frames[
            (frames["t"] >= lo)
            & (frames["t"] < hi)
        ]

        duration = max(hi - lo, 0.1)

        n_words = int(
            (
                (word_starts >= lo)
                & (word_starts < hi)
            ).sum()
        )

        rows.append({
            "time": t,
            "pitch": win["pitch"].mean(),
            "pitch_var": win["pitch"].std(),
            "energy": win["energy"].mean(),
            "rate": n_words / duration
        })

    return pd.DataFrame(rows)


# ---------------- STEP 4: PROBLEM REGIONS ----------------

def find_regions(timeline):
    regions = []
    times = timeline["time"].to_numpy()

    for feature, (low, high) in IDEAL.items():
        values = timeline[feature].to_numpy()

        flag = np.zeros(len(values), dtype=int)
        flag[values < low] = -1
        flag[values > high] = 1

        i = 0

        while i < len(flag):
            if flag[i] == 0:
                i += 1
                continue

            j = i

            while (
                j + 1 < len(flag)
                and flag[j + 1] == flag[i]
            ):
                j += 1

            start = times[i]
            end = times[j] + STEP_S

            if end - start >= MIN_REGION_S:
                regions.append({
                    "feature": feature,
                    "direction": int(flag[i]),
                    "from": round(float(start), 1),
                    "to": round(float(end), 1),
                    "issue": ISSUE_TEXT[
                        (feature, int(flag[i]))
                    ]
                })

            i = j + 1

    return sorted(
        regions,
        key=lambda region: region["from"]
    )


# ---------------- STEP 5: FOUR-PANEL GRAPH ----------------

def make_graph(timeline, regions, sentences):
    fig, axes = plt.subplots(
        4, 1,
        figsize=(10, 9),
        sharex=True
    )

    for ax, feature in zip(axes, IDEAL):
        low, high = IDEAL[feature]

        ax.axhspan(
            low, high,
            color="green",
            alpha=0.12,
            label="IDEAL"
        )

        ax.plot(
            timeline["time"],
            timeline[feature],
            linewidth=1.8
        )

        for region in regions:
            if region["feature"] == feature:
                ax.axvspan(
                    region["from"],
                    region["to"],
                    color="red",
                    alpha=0.25
                )

        ax.set_ylabel(LABELS[feature], fontsize=9)
        ax.grid(alpha=0.3)

    for i, sentence in enumerate(sentences, start=1):
        midpoint = (
            sentence["start"] + sentence["end"]
        ) / 2

        axes[0].text(
            midpoint, 1.02,
            f"S{i}",
            ha="center",
            fontsize=9,
            transform=axes[0].get_xaxis_transform()
        )

        for ax in axes:
            ax.axvline(
                sentence["start"],
                color="gray",
                linestyle=":",
                linewidth=0.8
            )

    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("Time (seconds)")

    fig.suptitle(
        "Speech feature timeline vs IDEAL "
        "(red = potentially problematic region)",
        y=1.0
    )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=110,
        bbox_inches="tight"
    )
    plt.close(fig)

    return base64.b64encode(
        buf.getvalue()
    ).decode("utf-8")


def clean(value):
    if value is None or pd.isna(value):
        return None

    return round(float(value), 2)


# ---------------- HEALTH CHECK ----------------

@app.get("/")
def home():
    return {"status": "ok", "message": "Speech Coach API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------- MAIN ANALYSIS ENDPOINT ----------------

@app.post("/analyze")
def analyze(
    file: UploadFile = File(...),
    lang: str = Form("en")
):
    try:
        # Read upload once and validate it.
        file_bytes = file.file.read()

        print(
            "DEBUG: Filename:", file.filename,
            "Content type:", file.content_type,
            "Bytes:", len(file_bytes),
            flush=True
        )

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio is empty."
            )

        # Preserve the actual extension where possible.
        extension = os.path.splitext(
            file.filename or "recording.wav"
        )[1].lower()

        if extension not in {
            ".wav", ".mp3", ".m4a", ".mp4",
            ".webm", ".ogg", ".flac"
        }:
            extension = ".wav"

        with tempfile.TemporaryDirectory() as folder:
            audio_path = os.path.join(
                folder,
                "recording" + extension
            )

            with open(audio_path, "wb") as f:
                f.write(file_bytes)

            print(
                "DEBUG: Saved size:",
                os.path.getsize(audio_path),
                flush=True
            )

            sentences, words = get_transcript(
                audio_path, lang
            )

            if not sentences:
                return {
                    "transcript": "",
                    "results": [],
                    "regions": [],
                    "graph": None,
                    "ideal_audio": None,
                    "error": "No speech detected. Please try recording again."
                }

            curves = extract_curves(audio_path)
            rows = analyze_sentences(sentences, curves)

            for row in rows:
                row["tips"] = get_tips(row)

            timeline = build_timeline(curves, words)
            regions = find_regions(timeline)
            graph_b64 = make_graph(
                timeline, regions, sentences
            )

            # Generate ideal reference audio.
            ideal_b64 = None

            try:
                ideal_path = os.path.join(
                    folder, "ideal.mp3"
                )

                gTTS(
                    text=" ".join(
                        s["text"] for s in sentences
                    ),
                    lang=lang
                ).save(ideal_path)

                with open(ideal_path, "rb") as f:
                    ideal_b64 = base64.b64encode(
                        f.read()
                    ).decode("utf-8")

            except Exception as exc:
                print(
                    "DEBUG: gTTS failed:",
                    repr(exc),
                    flush=True
                )

            results = []

            for row in rows:
                results.append({
                    "sentence": row["sentence"],
                    "start": clean(row["start"]),
                    "end": clean(row["end"]),
                    "rate": clean(row["rate"]),
                    "pitch": clean(row["pitch"]),
                    "pitch_var": clean(row["pitch_var"]),
                    "energy": clean(row["energy"]),
                    "tips": row["tips"],
                })

            response = {
                "transcript": " ".join(
                    s["text"] for s in sentences
                ),
                "results": results,
                "regions": [
                    {
                        "from": region["from"],
                        "to": region["to"],
                        "issue": region["issue"]
                    }
                    for region in regions
                ],
                "graph": graph_b64,
                "ideal_audio": ideal_b64,
            }

            print(
                "DEBUG: Returning results:",
                len(results),
                flush=True
            )

            return response

    except HTTPException:
        raise

    except Exception as exc:
        print(
            "ERROR in /analyze:",
            repr(exc),
            flush=True
        )
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Speech analysis failed: {str(exc)}"
        )
'''

with open("server.py", "w", encoding="utf-8") as f:
    f.write(SERVER_CODE)

print("✅ server.py created")


# ------------------------------------------------------------
# 3. START FASTAPI WITHOUT PKILL
# ------------------------------------------------------------

# Stop previously launched processes from this notebook, if any.
for process_name in ("server_process", "tunnel_process"):
    old_process = globals().get(process_name)

    if old_process is not None and old_process.poll() is None:
        old_process.terminate()
        try:
            old_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            old_process.kill()

# Avoid port conflicts from stale processes.
subprocess.run(
    ["bash", "-lc", "fuser -k 8000/tcp >/dev/null 2>&1 || true"],
    check=False
)

server_log = open("server.log", "w", buffering=1)

server_process = subprocess.Popen(
    [
        sys.executable, "-m", "uvicorn",
        "server:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ],
    stdout=server_log,
    stderr=subprocess.STDOUT
)

import urllib.request

api_ready = False

for attempt in range(30):
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/health",
            timeout=2
        ) as response:
            if response.status == 200:
                api_ready = True
                break
    except Exception:
        time.sleep(1)

if not api_ready:
    print("❌ FastAPI failed to start. Server logs:")
    print(Path("server.log").read_text(errors="ignore")[-6000:])
    raise RuntimeError("Fix the server error shown above before continuing.")

print("✅ FastAPI started successfully")

# ---------- VOICE METERS ----------
if result and result.get("results"):
    st.markdown("---")
    st.header("🎙️ Voice Performance Meters")

    sentence_results = result["results"]

    # Average measured energy across sentences.
    energy_values = [
        float(row["energy"])
        for row in sentence_results
        if row.get("energy") is not None
    ]

    # Existing backend rate is words per second.
    rate_values = [
        float(row["rate"])
        for row in sentence_results
        if row.get("rate") is not None
    ]

    col1, col2 = st.columns(2)

    with col1:
        avg_energy = (
            sum(energy_values) / len(energy_values)
            if energy_values else None
        )

        show_meter(
            title="🔊 Voice Energy",
            value=avg_energy,
            low=-6,
            high=6,
            unit="dB",
            description=(
                "Relative energy: the target range is -6 to +6 dB."
            )
        )

    with col2:
        avg_rate = (
            sum(rate_values) / len(rate_values)
            if rate_values else None
        )

        show_meter(
            title="⚡ Speaking Speed",
            value=avg_rate,
            low=1.8,
            high=3.3,
            unit="words/s",
            description=(
                "Target pace: 1.8–3.3 words per second."
            )
        )

result = st.session_state.get("speech_result")

# ------------------------------------------------------------
# 4. START CLOUDFLARE TUNNEL
# ------------------------------------------------------------

cloudflared_path = "/content/cloudflared"

if not os.path.exists(cloudflared_path):
    import urllib.request

    urllib.request.urlretrieve(
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        cloudflared_path
    )

os.chmod(cloudflared_path, 0o755)

tunnel_log = open("tunnel.log", "w", buffering=1)

tunnel_process = subprocess.Popen(
    [
        cloudflared_path,
        "tunnel",
        "--url", "http://127.0.0.1:8000",
        "--no-autoupdate"
    ],
    stdout=tunnel_log,
    stderr=subprocess.STDOUT
)

public_url = None

for attempt in range(60):
    time.sleep(2)

    log_text = Path("tunnel.log").read_text(
        encoding="utf-8",
        errors="ignore"
    )

    matches = re.findall(
        r"https://[a-zA-Z0-9-]+\.trycloudflare\.com",
        log_text
    )

    if matches:
        public_url = matches[-1]
        break

if not public_url:
    print("❌ Cloudflare URL not found. Tunnel logs:")
    print(Path("tunnel.log").read_text(errors="ignore")[-5000:])
    raise RuntimeError("Cloudflare tunnel failed to start.")

print("\n" + "=" * 55)
print("🎉 SPEECH COACH BACKEND IS READY")
print("BACKEND_URL =", public_url)
print("Health check =", public_url + "/health")
print("Analysis endpoint =", public_url + "/analyze")
print("=" * 55)
print("\nKeep this Colab session running.")
print("If the URL changes, update BACKEND_URL in Streamlit Secrets.")
