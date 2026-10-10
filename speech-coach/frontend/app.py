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
# Set BACKEND_URL in Streamlit Community Cloud Secrets.
# Example:
# BACKEND_URL = "https://your-colab-tunnel.trycloudflare.com"
BACKEND_URL = st.secrets["BACKEND_URL"].rstrip("/")


# ---------------- PROFESSIONAL THEME ----------------
st.markdown(
    """
    <style>
    /* Main background */
    .stApp {
        background: linear-gradient(
            135deg,
            #111827 0%,
            #1E1B4B 55%,
            #272052 100%
        );
        color: #F9FAFB;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Hero header */
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

    /* Section headings */
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

    /* Cards */
    .custom-card {
        background: rgba(31, 41, 55, 0.88);
        border: 1px solid rgba(167, 139, 250, 0.25);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }

    /* Input labels */
    label, .stMarkdown p {
        color: #E5E7EB;
    }

    /* Buttons */
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

    /* File uploader */
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

    /* Audio player */
    audio {
        width: 100%;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #1F2937;
        border: 1px solid rgba(167, 139, 250, 0.25);
        border-radius: 15px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"] {
        color: #C7D2FE;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    /* Text areas and select boxes */
    .stTextArea textarea,
    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] {
        background-color: #1F2937;
        color: #FFFFFF;
        border-radius: 10px;
    }

    /* Alerts */
    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    /* Footer */
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

# ---------------- RECORD SPEECH ----------------
st.markdown(
    '<div class="section-title">🎤 Record Your Speech</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p class="muted">
        Record your speech or upload an audio file to get personalized feedback.
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

# Prefer the recording if one is available.
selected_audio = audio_file if audio_file is not None else uploaded_file

# ---------------- ANALYSIS ----------------
st.markdown("")

if st.button("✨ Analyze My Speech", use_container_width=True):

    if selected_audio is None:
        st.warning("Please record your speech or upload an audio file first.")

    elif not BACKEND_URL:
        st.error(
            "Backend URL is not configured. Add BACKEND_URL to your "
            "Streamlit Community Cloud Secrets."
        )

    else:
        with st.spinner(
            "Analyzing your speech... Please wait."
        ):
            try:
                audio_bytes = selected_audio.getvalue()

                files = {
                    "file": (
                        selected_audio.name
                        if getattr(selected_audio, "name", None)
                        else "recording.wav",
                        audio_bytes,
                        getattr(
                            selected_audio,
                            "type",
                            None
                        ) or "application/octet-stream",
                    )
                }

                response = requests.post(
                    f"{BACKEND_URL}/analyze",
                    files=files,
                    timeout=180,
                )

                response.raise_for_status()
                result = response.json()

            except requests.exceptions.Timeout:
                st.error(
                    "The analysis took too long. Check that your Colab "
                    "backend is running and try again."
                )

            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not connect to the backend. Check your "
                    "BACKEND_URL and ensure the Colab tunnel is active."
                )

            except requests.exceptions.HTTPError as exc:
                st.error(
                    f"Backend returned an HTTP error: {exc}"
                )
                try:
                    st.code(response.text)
                except Exception:
                    pass

            except Exception as exc:
                st.error(f"Analysis failed: {exc}")

            else:
                st.session_state["speech_result"] = result

# ---------------- RESULTS ----------------
result = st.session_state.get("speech_result")

if result:
    st.markdown("---")
    st.markdown(
        '<div class="section-title">📊 Your Speech Analysis</div>',
        unsafe_allow_html=True,
    )

    # Display common metrics when present in the response.
    metric_options = [
        ("score", "Speech Score"),
        ("speech_rate", "Speech Rate"),
        ("duration", "Duration"),
    ]

    available_metrics = [
        (key, label, result[key])
        for key, label in metric_options
        if isinstance(result, dict) and key in result
        and not isinstance(result[key], (dict, list))
    ]

    if available_metrics:
        columns = st.columns(len(available_metrics))

        for column, (key, label, value) in zip(
            columns, available_metrics
        ):
            column.metric(label, value)

    # Show textual analysis if available.
    for key, title in [
        ("transcript", "📝 Transcript"),
        ("feedback", "💡 Personalized Feedback"),
        ("analysis", "🔍 Analysis"),
    ]:
        if isinstance(result, dict) and key in result:
            st.markdown(
                f'<div class="section-title">{title}</div>',
                unsafe_allow_html=True,
            )

            value = result[key]

            if isinstance(value, (dict, list)):
                st.json(value)
            else:
                st.write(value)

    # Always provide a way to inspect fields returned by your API.
    with st.expander("View complete backend response"):
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
