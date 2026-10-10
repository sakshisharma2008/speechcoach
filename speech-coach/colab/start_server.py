!pip install -q fastapi uvicorn python-multipart assemblyai gtts

import os
import re
import subprocess
import time
from google.colab import userdata

# ---------- 1) server ka code file me likho ----------
SERVER_CODE = r'''
import base64
import io
import os
import tempfile

import assemblyai as aai
import librosa
import matplotlib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile
from gtts import gTTS

matplotlib.use("Agg")   # server pe graph bina screen ke banane ke liye
import matplotlib.pyplot as plt

aai.settings.api_key = os.environ["ASSEMBLYAI_API_KEY"]
app = FastAPI()

# ---------- IDEAL: ideal speaking range (low, high) ----------
IDEAL = {
    "pitch": (-4, 4),        # semitones, apni median awaaz se
    "energy": (-6, 6),       # dB, apni median loudness se
    "pitch_var": (1.0, 6.0), # kam = monotone, zyada = erratic
    "rate": (1.8, 3.3),      # words per second
}
LABELS = {
    "pitch": "Pitch\n(semitones)",
    "energy": "Energy\n(dB)",
    "pitch_var": "Pitch variation\n(semitones)",
    "rate": "Speech rate\n(words/s)",
}
# (feature, -1 = ideal se kam, +1 = ideal se zyada) -> problem
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
STEP_S = 0.5         # timeline har 0.5 second pe
WINDOW_S = 3.0       # har point ke aas-paas 3 second ka average
MIN_REGION_S = 2.0   # issue kam se kam itni der chale tabhi gino


# ---------- STEP 1: AssemblyAI se sentences + words (time ke sath) ----------
def get_transcript(audio_path, lang):
    config = aai.TranscriptionConfig(language_code=lang)
    transcript = aai.Transcriber().transcribe(audio_path, config=config)
    if transcript.status != aai.TranscriptStatus.completed:
        raise RuntimeError(transcript.error)
    sentences = [{"text": s.text, "start": s.start / 1000, "end": s.end / 1000}
                 for s in transcript.get_sentences()]
    words = [{"start": w.start / 1000} for w in (transcript.words or [])]
    return sentences, words


# ---------- STEP 2: Audio se pitch aur energy nikalo ----------
def extract_curves(audio_path):
    y, sr = librosa.load(audio_path, sr=16000)
    hop = 512
    f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"),
                            fmax=librosa.note_to_hz("C6"), sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    n = min(len(f0), len(rms))
    f0, rms = f0[:n], rms[:n]
    times = librosa.times_like(f0, sr=sr, hop_length=hop)

    pitch = 12 * np.log2(f0 / np.nanmedian(f0))        # apni median awaaz se kitna door
    db = librosa.amplitude_to_db(rms)
    speaking = db > (db.max() - 35)                      # chuppi hata do
    energy = np.where(speaking, db - np.median(db[speaking]), np.nan)
    return {"times": times, "pitch": pitch, "energy": energy, "duration": len(y) / sr}


# ---------- STEP 3a: Har sentence ke numbers ----------
def analyze_sentences(sentences, curves):
    rows = []
    for s in sentences:
        part = (curves["times"] >= s["start"]) & (curves["times"] <= s["end"])
        duration = max(s["end"] - s["start"], 0.1)
        rows.append({
            "sentence": s["text"],
            "start": s["start"],
            "end": s["end"],
            "rate": len(s["text"].split()) / duration,
            "pitch": pd.Series(curves["pitch"][part]).mean(),
            "pitch_var": pd.Series(curves["pitch"][part]).std(),
            "energy": pd.Series(curves["energy"][part]).mean(),
        })
    return rows


def get_tips(row):

    tips = []

    if row["rate"] > IDEAL["rate"][1]:
        tips.append("Speak a little slower and take short pauses between words")

    if row["rate"] < IDEAL["rate"][0]:
        tips.append("Speak a little faster and maintain a smooth flow")

    if row["pitch"] > IDEAL["pitch"][1]:
        tips.append("Your pitch is too high; relax and speak slightly lower")

    if row["pitch"] < IDEAL["pitch"][0]:
        tips.append("Your pitch is too low; add a little more energy")

    if row["energy"] > IDEAL["energy"][1]:
        tips.append("Your voice is too loud; speak a little more softly")

    if row["energy"] < IDEAL["energy"][0]:
        tips.append("Your voice is too quiet; speak a little more clearly and loudly")

    if row["pitch_var"] < IDEAL["pitch_var"][0]:
        tips.append("Your voice sounds monotone; vary your pitch on important words")

    return tips

# ---------- STEP 3b: Feature timeline (graph ke liye) ----------
def build_timeline(curves, words):
    frames = pd.DataFrame({"t": curves["times"], "pitch": curves["pitch"],
                           "energy": curves["energy"]})
    word_starts = np.array([w["start"] for w in words])
    rows = []
    for t in np.arange(0, curves["duration"], STEP_S):
        lo = max(0, t - WINDOW_S / 2)
        hi = min(curves["duration"], t + WINDOW_S / 2)
        win = frames[(frames.t >= lo) & (frames.t < hi)]
        n_words = int(((word_starts >= lo) & (word_starts < hi)).sum())
        rows.append({
            "time": t,
            "pitch": win.pitch.mean(),
            "pitch_var": win.pitch.std(),
            "energy": win.energy.mean(),
            "rate": n_words / (hi - lo),
        })
    return pd.DataFrame(rows)


# ---------- STEP 4: IDEAL se compare -> problem wale regions ----------
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
            while j + 1 < len(flag) and flag[j + 1] == flag[i]:
                j += 1
            start, end = times[i], times[j] + STEP_S
            if end - start >= MIN_REGION_S:
                regions.append({"feature": feature, "direction": int(flag[i]),
                                "from": round(float(start), 1), "to": round(float(end), 1),
                                "issue": ISSUE_TEXT[(feature, int(flag[i]))]})
            i = j + 1
    return sorted(regions, key=lambda r: r["from"])

# ---------- STEP 5: 4-panel graph ----------
def make_graph(timeline, regions, sentences):
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, feature in zip(axes, IDEAL):
        low, high = IDEAL[feature]
        ax.axhspan(low, high, color="green", alpha=0.12, label="IDEAL")
        ax.plot(timeline["time"], timeline[feature], lw=1.8)
        for r in regions:
            if r["feature"] == feature:
                ax.axvspan(r["from"], r["to"], color="red", alpha=0.25)
        ax.set_ylabel(LABELS[feature], fontsize=9)
        ax.grid(alpha=0.3)

    # Sentence numbers (S1, S2...) upar likho taaki list se match ho sake
    for i, s in enumerate(sentences, start=1):
        axes[0].text((s["start"] + s["end"]) / 2, 1.02, f"S{i}", ha="center", fontsize=9,
                     transform=axes[0].get_xaxis_transform())
        for ax in axes:
            ax.axvline(s["start"], color="gray", ls=":", lw=0.8)

    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("Time (seconds)")
    fig.suptitle("Speech feature timeline vs IDEAL  (red = problematic region)", y=1.0)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def clean(value):
    """NaN ko None me badlo taaki JSON me bheja ja sake."""
    return None if pd.isna(value) else round(float(value), 2)


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(file: UploadFile = File(...), lang: str = Form("en")):
    with tempfile.TemporaryDirectory() as folder:
        audio_path = os.path.join(folder, "recording.wav")
        with open(audio_path, "wb") as f:
            f.write(file.file.read())

        sentences, words = get_transcript(audio_path, lang)
        if not sentences:
            return {"transcript": "", "results": [], "regions": [],
                    "graph": None, "ideal_audio": None}

        curves = extract_curves(audio_path)
        rows = analyze_sentences(sentences, curves)
        for r in rows:
            r["tips"] = get_tips(r)

        timeline = build_timeline(curves, words)
        regions = find_regions(timeline)
        graph_b64 = make_graph(timeline, regions, sentences)

        ideal_path = os.path.join(folder, "ideal.mp3")
        gTTS(text=" ".join(s["text"] for s in sentences), lang=lang).save(ideal_path)
        with open(ideal_path, "rb") as f:
            ideal_b64 = base64.b64encode(f.read()).decode()

    results = []
    for r in rows:
        results.append({
            "sentence": r["sentence"],
            "start": clean(r["start"]),
            "end": clean(r["end"]),
            "rate": clean(r["rate"]),
            "pitch": clean(r["pitch"]),
            "pitch_var": clean(r["pitch_var"]),
            "energy": clean(r["energy"]),
            "tips": r["tips"],
        })
    return {
        "transcript": " ".join(s["text"] for s in sentences),
        "results": results,
        "regions": [{"from": r["from"], "to": r["to"], "issue": r["issue"]} for r in regions],
        "graph": graph_b64,
        "ideal_audio": ideal_b64,
    }
'''

with open("server.py", "w") as f:
    f.write(SERVER_CODE)

# ---------- 2) purana server/tunnel band karo (cell dobara chalane par) ----------
subprocess.run("pkill -f uvicorn; pkill -f cloudflared", shell=True)
time.sleep(1)

# ---------- 3) server chalao ----------
os.environ["ASSEMBLYAI_API_KEY"] = userdata.get("ASSEMBLYAI_API_KEY")
subprocess.Popen(["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"])

# ---------- 4) public link banane wala tool (cloudflared) ----------
if not os.path.exists("cloudflared"):
    subprocess.run(["wget", "-q",
                    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                    "-O", "cloudflared"], check=True)
    subprocess.run(["chmod", "+x", "cloudflared"], check=True)
subprocess.Popen("./cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1", shell=True)

# ---------- 5) link nikalo ----------
url = None
for _ in range(40):
    time.sleep(1)
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("tunnel.log").read())
    if m:
        url = m.group(0)
        break

print("✅ Ye URL VS Code app me daalo:", url)
