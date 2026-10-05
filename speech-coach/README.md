# 🎤 Speech Coach

Record your voice, get a breakdown of how you spoke, and hear a corrected version.

**Pipeline:** record audio → AssemblyAI (timestamped transcript) → pitch / energy / speech rate
(librosa) → feature timeline → compare with IDEAL → find deviation regions → explain the flaw →
generate an ideal-delivery audio (gTTS).

## Architecture

```
Streamlit frontend (your laptop, mic)  ──audio──►  FastAPI backend (Google Colab + public tunnel)
                                       ◄─JSON+PNG─
```

```
speech-coach/
├── backend/    FastAPI server (analysis, graph, ideal audio)
├── frontend/   Streamlit app (record, show results)
└── colab/      Cell that clones this repo and starts the backend on Colab
```

## 1. Start the backend (Google Colab)

1. In Colab, add a secret named `ASSEMBLYAI_API_KEY` (🔑 sidebar) and enable notebook access.
2. Edit `REPO` in `colab/start_server.py` to your repo URL.
3. Paste that file into one Colab cell and run it.
4. Copy the `https://....trycloudflare.com` URL it prints.

The URL changes every time you rerun the cell, and it works only while the Colab cell is running.

## 2. Run the frontend (local)

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Paste the backend URL into the sidebar, record 3-4 sentences, and press **Analyze**.

## Tuning

The `IDEAL` dictionary in `backend/server.py` holds the acceptable ranges
(pitch, energy, pitch variation, speech rate). The defaults are reasonable starting points,
not validated targets, so adjust them to your needs.

## Notes

- Never commit your API key. It is read from the `ASSEMBLYAI_API_KEY` environment variable.
- The "ideal" audio is an AI voice (gTTS), not your own voice.
