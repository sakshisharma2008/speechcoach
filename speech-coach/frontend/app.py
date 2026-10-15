import base64
import html
import os

import requests
import streamlit as st

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Speech Coach AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------- BACKEND CONFIG ----------------
BACKEND_URL = st.secrets.get("BACKEND_URL", "").rstrip("/")


# ---------------- WARM LIGHT-BROWN THEME ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #FAF7F2 0%, #F0E6D8 100%);
    color: #3E3028;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

.hero {
    background: linear-gradient(120deg, #5C4033, #8B654A, #B08968);
    padding: 30px;
    border-radius: 22px;
    color: #FFFFFF;
    margin-bottom: 25px;
    box-shadow: 0 8px 25px rgba(92, 64, 51, 0.18);
}

.hero h1 {
    color: #FFFFFF;
    font-size: 36px;
    margin-bottom: 8px;
}

.hero p {
    color: #F5EBDD;
    font-size: 16px;
    margin-bottom: 0;
}

.section-title {
    color: #5C4033;
    font-size: 23px;
    font-weight: 700;
    margin-top: 15px;
    margin-bottom: 12px;
}

div[data-testid="stMetric"] {
    background: #FFFCF8;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #E4D3C1;
    box-shadow: 0 4px 15px rgba(92, 64, 51, 0.06);
}

div[data-testid="stMetricLabel"] {
    color: #806B5A;
}

div[data-testid="stMetricValue"] {
    color: #5C4033;
}

.stButton > button {
    background: linear-gradient(90deg, #795548, #A47148);
    color: #FFFFFF;
    border: 1px solid #795548;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: 600;
    width: 100%;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: #5C4033;
    color: #FFFFFF;
    border-color: #5C4033;
}

div[data-testid="stExpander"] {
    background: #FFFCF8;
    border-radius: 12px;
    border: 1px solid #E4D3C1;
}

div[data-testid="stAudioInput"] {
    background: #FFFCF8;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #E4D3C1;
}

.stProgress > div > div > div > div {
    background-color: #A47148;
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #E4D3C1;
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HERO ----------------
st.markdown(
    """
    <div class="hero">
        <h1>🎙️ Speech Coach AI</h1>
        <p>
            Improve your speaking skills with speech speed measurement,
            sentence analysis and personalized feedback.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- DATASET: IDEAL REFERENCE ----------
st.markdown("---")
st.header("📚 Dataset Reference Speech")

ideal_audio_path = "dataset/audio/ideal/ideal_001.mp3"
annotation_path = "dataset/annotations/ideal_001.txt"

if os.path.exists(ideal_audio_path):
    st.caption("Ideal reference recording")
    st.audio(ideal_audio_path, format="audio/mp3")
else:
    st.warning(
        "Ideal reference audio not found. "
        "Check the dataset path in your repository."
    )

if os.path.exists(annotation_path):
    with open(annotation_path, "r", encoding="utf-8") as annotation_file:
        ideal_annotation = annotation_file.read()

    with st.expander("View ideal reference transcript"):
        st.text(ideal_annotation)
else:
    st.caption("Reference annotation file was not found.")

# ---------------- RECORD OR UPLOAD SPEECH ----------------
st.markdown(
    '<div class="section-title">🎤 Record Your Speech</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <p class="muted">
        Record your speech or upload an audio file to receive personalized feedback.
    </p>
    """,
    unsafe_allow_html=True,
)

audio_file = st.audio_input("Record your voice")

st.markdown(
    '<div class="muted">Or upload a recording</div>',
    unsafe_allow_html=True,
)
uploaded_file = st.file_uploader(
    "Choose an audio file",
    type=["wav", "mp3", "m4a", "ogg", "webm"],
    label_visibility="collapsed",
)

selected_audio = audio_file if audio_file is not None else uploaded_file

# ---------------- ANALYZE SPEECH ----------------
if st.button("✨ Analyze My Speech", use_container_width=True):
    if selected_audio is None:
        st.warning("Please record your speech or upload an audio file first.")
    elif not BACKEND_URL:
        st.error(
            "Backend URL is not configured. Add BACKEND_URL "
            "to your Streamlit Community Cloud Secrets."
        )
    else:
        try:
            with st.spinner("Analyzing your speech... Please wait."):
                audio_bytes = selected_audio.getvalue()
                filename = getattr(selected_audio, "name", None) or "recording.wav"
                mime_type = (
                    getattr(selected_audio, "type", None)
                    or "application/octet-stream"
                )

                response = requests.post(
                    f"{BACKEND_URL}/analyze",
                    files={"file": (filename, audio_bytes, mime_type)},
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()

                if not isinstance(result, dict):
                    raise ValueError("The backend did not return a JSON object.")

                st.session_state["speech_result"] = result

        except requests.exceptions.Timeout:
            st.session_state.pop("speech_result", None)
            st.error(
                "Analysis timed out. Check that your backend is running "
                "and try again."
            )
        except requests.exceptions.ConnectionError:
            st.session_state.pop("speech_result", None)
            st.error(
                "Could not connect to the backend. Check BACKEND_URL "
                "and make sure your backend or Cloudflare tunnel is active."
            )
        except requests.exceptions.HTTPError as exc:
            st.session_state.pop("speech_result", None)
            st.error(f"Backend returned an HTTP error: {exc}")
            if "response" in locals():
                with st.expander("View error details"):
                    st.code(response.text[:5000])
        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            st.session_state.pop("speech_result", None)
            st.error(f"Could not read the backend response: {exc}")
        except Exception as exc:
            st.session_state.pop("speech_result", None)
            st.error(f"Analysis failed: {exc}")

# ---------------- DISPLAY RESULTS ----------------
result = st.session_state.get("speech_result")

if result:
    st.markdown("---")
    st.markdown(
        '<div class="section-title">📊 Your Speech Analysis</div>',
        unsafe_allow_html=True,
    )

    transcript = result.get("transcript") or ""
    sentence_results = result.get("results") or []
    regions = result.get("regions") or []
    graph = result.get("graph")

    if not transcript and not sentence_results:
        st.error(
            "⚠️ The backend received a request but returned no speech "
            "analysis. Please check the backend logs."
        )
        st.info(
            "Your dashboard is working. The transcription or audio "
            "processing step needs debugging."
        )

    # Transcript
    st.markdown("### 📝 Transcript")
    if transcript:
        st.markdown(
            '<div class="custom-card"><p>'
            + html.escape(str(transcript))
            + "</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No transcript was returned by the backend.")

    # Overall metrics
    overall_metrics = [
        ("score", "Speech Score"),
        ("speech_rate", "Speech Rate"),
        ("duration", "Duration"),
    ]
    available_metrics = [
        (label, result[key])
        for key, label in overall_metrics
        if key in result
        and result[key] is not None
        and not isinstance(result[key], (dict, list, bool))
    ]

    if available_metrics:
        st.markdown("### 📌 Overview")
        metric_columns = st.columns(len(available_metrics))
        for column, (label, value) in zip(metric_columns, available_metrics):
            column.metric(label, value)

    # Sentence-by-sentence analysis
    st.markdown("### 🎯 Sentence-wise Analysis")
    if sentence_results:
        sentence_metrics = [
            ("rate", "Speaking Rate"),
            ("pitch", "Pitch"),
            ("pitch_var", "Pitch Variation"),
            ("energy", "Energy"),
        ]

        for index, item in enumerate(sentence_results, start=1):
            if not isinstance(item, dict):
                continue

            with st.container(border=True):
                st.markdown(f"**Sentence {index}**")
                sentence = item.get("sentence", "Sentence unavailable")
                st.write(sentence)

                start = item.get("start")
                end = item.get("end")
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    st.caption(f"Timestamp: {start:.2f}s – {end:.2f}s")

                available = [
                    (label, item[key])
                    for key, label in sentence_metrics
                    if isinstance(item.get(key), (int, float))
                    and not isinstance(item.get(key), bool)
                ]
                if available:
                    metric_columns = st.columns(len(available))
                    for column, (label, value) in zip(metric_columns, available):
                        column.metric(label, f"{value:.2f}")

                tips = item.get("tips", [])
                if isinstance(tips, str):
                    tips = [tips]
                if tips:
                    st.markdown("**💡 Improvement Tips**")
                    for tip in tips:
                        st.write(f"• {tip}")
    else:
        st.caption("Sentence-level metrics will appear when returned by the backend.")

    # Detected issues and timestamps
    st.markdown("### ⚠️ Areas to Improve")
    if regions:
        for region in regions:
            if not isinstance(region, dict):
                continue
            start = region.get("from", region.get("start", 0))
            end = region.get("to", region.get("end", 0))
            issue = region.get("issue", "Review this section")
            st.markdown(
                f"""
                <div class="custom-card">
                    <p><strong>⏱️ {html.escape(str(start))}s – {html.escape(str(end))}s</strong></p>
                    <p>{html.escape(str(issue))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No issue regions were returned by the backend.")

    # Graph returned by the backend
    st.markdown("### 📈 Speech Analysis Graph")
    if graph:
        try:
            graph_string = str(graph)
            if graph_string.startswith("data:image"):
                graph_string = graph_string.split(",", 1)[1]
            graph_bytes = base64.b64decode(graph_string, validate=True)
            st.image(graph_bytes, use_container_width=True)
        except Exception:
            st.warning("The backend returned graph data, but it could not be displayed as an image.")
    else:
        st.caption("The graph will appear when the backend generates it.")

    # Other feedback fields, if provided
    for key, title in [
        ("feedback", "💡 Additional Feedback"),
        ("analysis", "🔍 Additional Analysis"),
    ]:
        value = result.get(key)
        if value:
            st.markdown(f"### {title}")
            if isinstance(value, str):
                st.write(value)
            elif isinstance(value, list):
                for entry in value:
                    st.write(f"• {entry}")
            elif isinstance(value, dict):
                for label, detail in value.items():
                    st.markdown(f"**{str(label).replace('_', ' ').title()}**")
                    st.write(detail)

# ---------------- FOOTER ----------------
st.markdown(
    """
    <div class="footer">
        Speech Coach AI · Practice with purpose. Speak with confidence.
    </div>
    """,
    unsafe_allow_html=True,
)
