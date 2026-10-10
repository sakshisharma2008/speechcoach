
import base64
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
try:
    BACKEND_URL = st.secrets.get("BACKEND_URL", "").rstrip("/")
except Exception:
    BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")


# ---------------- PROFESSIONAL THEME ----------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            135deg,
            #111827 0%,
            #1E1B4B 55%,
            #272052 100%
        );
        color: #F9FAFB;
    }

    [data-testid="stHeader"],
    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(
            120deg,
            #3730A3 0%,
            #6366F1 55%,
            #8B5CF6 100%
        );
        padding: 32px 34px;
        border-radius: 24px;
        margin-bottom: 30px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.18);
    }

    .hero h1 {
        color: #FFFFFF;
        font-size: clamp(30px, 4vw, 42px);
        font-weight: 750;
        margin: 0 0 12px 0;
        letter-spacing: -1px;
    }

    .hero p {
        color: #EEF2FF;
        font-size: 16px;
        line-height: 1.7;
        margin: 0;
    }

    h2, h3 {
        color: #F9FAFB !important;
    }

    .section-title {
        color: #E0E7FF;
        font-size: 23px;
        font-weight: 700;
        margin: 24px 0 16px 0;
    }

    .muted {
        color: #C7D2FE;
        font-size: 14px;
    }

    .custom-card {
        background: rgba(31, 41, 55, 0.88);
        border: 1px solid rgba(167, 139, 250, 0.25);
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }

    .custom-card p {
        color: #E5E7EB;
        line-height: 1.7;
        overflow-wrap: anywhere;
    }

    label, .stMarkdown p {
        color: #E5E7EB;
    }

    .stButton > button {
        background: linear-gradient(120deg, #6366F1, #8B5CF6);
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        min-height: 48px;
        font-size: 16px;
        font-weight: 650;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        border: 1px solid #C4B5FD;
        color: #FFFFFF;
        box-shadow: 0 0 18px rgba(139, 92, 246, 0.3);
        transform: translateY(-1px);
    }

    [data-testid="stFileUploader"] {
        background: rgba(31, 41, 55, 0.7);
        border-radius: 14px;
        padding: 12px;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: #1F2937;
        border: 1px dashed #818CF8;
        border-radius: 12px;
    }

    audio {
        width: 100%;
    }

    [data-testid="stMetric"] {
        background: #1F2937;
        border: 1px solid rgba(167, 139, 250, 0.25);
        border-radius: 15px;
        padding: 15px;
    }

    [data-testid="stMetricLabel"] {
        color: #C7D2FE;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    .stTextArea textarea,
    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] {
        background-color: #1F2937;
        color: #FFFFFF;
        border-radius: 10px;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    .footer {
        color: #9CA3AF;
        text-align: center;
        font-size: 13px;
        padding-top: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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

selected_audio = (
    audio_file if audio_file is not None else uploaded_file
)


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

                filename = getattr(selected_audio, "name", None)
                if not filename:
                    filename = "recording.wav"

                mime_type = (
                    getattr(selected_audio, "type", None)
                    or "application/octet-stream"
                )

                response = requests.post(
                    f"{BACKEND_URL}/analyze",
                    files={
                        "file": (
                            filename,
                            audio_bytes,
                            mime_type,
                        )
                    },
                    timeout=180,
                )

                response.raise_for_status()
                result = response.json()

                if not isinstance(result, dict):
                    raise ValueError(
                        "The backend did not return a JSON object."
                    )

                st.session_state["speech_result"] = result
                st.session_state.pop("speech_error", None)

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
                "and make sure your Cloudflare tunnel is active."
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

    # Transcript
    transcript = result.get("transcript", "")

    st.markdown("### 📝 Transcript")

    if transcript:
        st.markdown(
            '<div class="custom-card">'
            + "<p>"
            + __import__("html").escape(str(transcript))
            + "</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No transcript was returned by the backend.")

    # Overall metrics, only when the backend provides them
    overall_metrics = [
        ("score", "Speech Score"),
        ("speech_rate", "Speech Rate"),
        ("duration", "Duration"),
    ]

    available_metrics = [
        (label, result[key])
        for key, label in overall_metrics
        if key in result
        and not isinstance(result[key], (dict, list, bool))
        and result[key] is not None
    ]

    if available_metrics:
        st.markdown("### 📌 Overview")
        cols = st.columns(len(available_metrics))

        for col, (label, value) in zip(cols, available_metrics):
            col.metric(label, value)

    # Sentence-by-sentence analysis
    sentence_results = result.get("results", [])

    if sentence_results:
        st.markdown("### 🎯 Sentence-wise Analysis")

        for index, item in enumerate(sentence_results, start=1):
            if not isinstance(item, dict):
                continue

            with st.container(border=True):
                st.markdown(f"**Sentence {index}**")

                sentence = item.get(
                    "sentence", "Sentence unavailable"
                )
                st.write(sentence)

                start = item.get("start")
                end = item.get("end")

                if isinstance(start, (int, float)) and isinstance(
                    end, (int, float)
                ):
                    st.caption(f"Timestamp: {start:.2f}s – {end:.2f}s")

                sentence_metrics = [
                    ("rate", "Speaking Rate"),
                    ("pitch", "Pitch"),
                    ("pitch_var", "Pitch Variation"),
                    ("energy", "Energy"),
                ]

                available = [
                    (label, item[key])
                    for key, label in sentence_metrics
                    if isinstance(item.get(key), (int, float))
                    and not isinstance(item.get(key), bool)
                ]

                if available:
                    metric_cols = st.columns(len(available))

                    for col, (label, value) in zip(
                        metric_cols, available
                    ):
                        col.metric(label, f"{value:.2f}")

                tips = item.get("tips", [])

                if isinstance(tips, str):
                    tips = [tips]

                if tips:
                    st.markdown("**💡 Improvement Tips**")

                    for tip in tips:
                        st.write(f"• {tip}")

    # Detected issues and timestamps
    regions = result.get("regions", [])

    if regions:
        st.markdown("### ⚠️ Areas to Improve")

        for region in regions:
            if not isinstance(region, dict):
                continue

            start = region.get("from", 0)
            end = region.get("to", 0)
            issue = region.get("issue", "Review this section")

            st.markdown(
                f"""
                <div class="custom-card">
                    <p><strong>⏱️ {start}s – {end}s</strong></p>
                    <p>{__import__("html").escape(str(issue))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Graph returned by the backend
    graph = result.get("graph")

    if graph:
        st.markdown("### 📈 Speech Analysis Graph")

        try:
            graph_string = str(graph)

            if graph_string.startswith("data:image"):
                graph_string = graph_string.split(",", 1)[1]

            graph_bytes = base64.b64decode(graph_string, validate=True)
            st.image(graph_bytes, use_container_width=True)

        except Exception:
            st.warning(
                "The backend returned graph data, but it could not "
                "be displayed as an image."
            )

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
                    st.markdown(f"**{label.replace('_', ' ').title()}**")
                    st.write(detail)

    # Raw JSON is hidden unless someone opens this section
    with st.expander("Developer debugging — raw backend response"):
        st.json(result)


# ---------------- FOOTER ----------------
st.markdown(
    """
    <div class="footer">
        Speech Coach AI · Practice with purpose. Speak with confidence.
    </div>
    """,
    unsafe_allow_html=True,
)
