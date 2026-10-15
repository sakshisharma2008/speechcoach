import base64
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Speech Coach AI",
    page_icon="🎤",
    layout="wide"
)


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





# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    # Read backend URL from Streamlit Secrets
    try:
        url = st.secrets["BACKEND_URL"].rstrip("/")
    except (KeyError, FileNotFoundError):
        st.error("⚠️ Backend URL not found in Streamlit Secrets.")
        url = ""

    lang = st.selectbox(
        "Select Language",
        ["en", "hi"],
        format_func=lambda x: "English" if x == "en" else "Hindi"
    )

    st.divider()

    st.caption("🎙️ Record 3–4 complete sentences.")
    st.caption("🔗 Ensure your Colab backend is running before analysis.")

# ---------------- RECORDING SECTION ----------------
st.markdown(
    '<div class="section-title">🎙️ Record Your Speech</div>',
    unsafe_allow_html=True
)

recording = st.audio_input("Record your voice")

analyze = st.button("✨ Analyze My Speech", use_container_width=True)


# ---------------- ANALYSIS ----------------
if analyze:

    if recording is None:
        st.warning("Please record your speech first.")

    elif not url.strip():
        st.error("Please enter your Colab backend URL in the sidebar.")

    else:
        with st.spinner("Analyzing your speech... Please wait."):

            try:
                response = requests.post(
                    url.rstrip("/") + "/analyze",
                    files={
                        "file": (
                            "recording.wav",
                            recording.getvalue(),
                            "audio/wav"
                        )
                    },
                    data={"lang": lang},
                    timeout=300
                )

                response.raise_for_status()
                data = response.json()

            except requests.exceptions.Timeout:
                st.error("Analysis timed out. Please try again.")

                st.stop()

            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the backend: {e}")
                st.stop()

            except ValueError:
                st.error("The backend did not return valid JSON.")
                st.stop()

        results = data.get("results", [])

        if not results:
            st.warning(
                "No sentences detected. Please record a longer, clearer speech."
            )
            st.stop()

        # ---------------- CALCULATE METRICS ----------------
        problem_count = sum(
            1 for item in results if item.get("tips")
        )

        # Calculate overall WPM using total words / total speaking time.
        # This is more reliable than averaging each sentence's rate equally.
        total_words = sum(
            len(str(item.get("sentence", "")).split())
            for item in results
        )
        total_duration = sum(
            max(
                float(item.get("end") or 0) - float(item.get("start") or 0),
                0.1
            )
            for item in results
        )
        avg_wpm = (total_words / total_duration * 60) if total_duration else 0

        total_sentences = len(results)
        issue_percentage = (problem_count / total_sentences) * 100

        # ---------------- PERFORMANCE SCORES ----------------
        # These are coaching estimates, not a clinical or objective measure.
        def bounded_score(value, low, high, penalty=8.0):
            if value is None:
                return None
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
            if pd.isna(value):
                return None
            distance = max(low - value, 0.0, value - high)
            return max(0.0, min(100.0, 100.0 - distance * penalty))

        speed_score = max(0.0, min(100.0, 100.0 - (
            (120 - avg_wpm) * 1.25 if avg_wpm < 120 else
            (avg_wpm - 150) * 1.1 if avg_wpm > 150 else 0
        )))

        pitch_values = [item.get("pitch") for item in results]
        pitch_scores = [bounded_score(v, -4, 4, 8.0) for v in pitch_values]
        pitch_scores = [v for v in pitch_scores if v is not None]
        pitch_score = sum(pitch_scores) / len(pitch_scores) if pitch_scores else None

        energy_values = [item.get("energy") for item in results]
        energy_scores = [bounded_score(v, -6, 6, 4.0) for v in energy_values]
        energy_scores = [v for v in energy_scores if v is not None]
        energy_score = sum(energy_scores) / len(energy_scores) if energy_scores else None

        variation_scores = []
        for item in results:
            value = item.get("pitch_var")
            try:
                value = float(value)
                if pd.isna(value):
                    continue
                if value < 1.0:
                    score = max(0.0, 100.0 - (1.0 - value) * 15.0)
                elif value > 6.0:
                    score = max(0.0, 100.0 - (value - 6.0) * 10.0)
                else:
                    score = 100.0
                variation_scores.append(score)
            except (TypeError, ValueError):
                continue
        variation_score = sum(variation_scores) / len(variation_scores) if variation_scores else None

        # If an audio feature is unavailable, redistribute its weight across
        # the scores that are available instead of treating missing data as zero.
        weighted_components = [(speed_score, 0.60)]
        if pitch_score is not None:
            weighted_components.append((pitch_score, 0.15))
        if variation_score is not None:
            weighted_components.append((variation_score, 0.15))
        if energy_score is not None:
            weighted_components.append((energy_score, 0.10))
        weight_total = sum(weight for _, weight in weighted_components)
        overall_score = round(
            sum(score * weight for score, weight in weighted_components) / weight_total
        ) if weight_total else round(speed_score)

        # ---------------- PERFORMANCE OVERVIEW ----------------
        st.markdown(
            '<div class="section-title">📊 Performance Overview</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "📝 Total Sentences",
            total_sentences
        )

        c2.metric(
            "⚡ Speaking Speed",
            f"{avg_wpm:.0f} WPM"
        )

        c3.metric(
            "⚠️ Sentences With Issues",
            f"{problem_count}/{total_sentences}"
        )

        # ---------------- SPEEDOMETER ----------------
        st.markdown(
            '<div class="section-title">🎯 Speaking Speed Meter</div>',
            unsafe_allow_html=True
        )

        gauge_value = max(0, min(avg_wpm, 240))

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=gauge_value,
                number={
                    "suffix": " WPM",
                    "font": {"size": 34, "color": "#5C4033"}
                },
                title={
                    "text": "Your Average Speaking Speed",
                    "font": {"size": 19, "color": "#5C4033"}
                },
                gauge={
                    "axis": {
                        "range": [0, 240],
                        "tickwidth": 1,
                        "tickcolor": "#806B5D",
                        "dtick": 30
                    },
                    "bar": {
                        "color": "#795548",
                        "thickness": 0.25
                    },
                    "bgcolor": "white",
                    "borderwidth": 0,
                    "steps": [
                        {
                            "range": [0, 100],
                            "color": "#F3E2D8"
                        },
                        {
                            "range": [100, 120],
                            "color": "#F2E5D5"
                        },
                        {
                            "range": [120, 150],
                            "color": "#E2E9DA"
                        },
                        {
                            "range": [150, 180],
                            "color": "#F2E5D5"
                        },
                        {
                            "range": [180, 240],
                            "color": "#F3E2D8"
                        }
                    ],
                    "threshold": {
                        "line": {
                            "color": "#8B7355",
                            "width": 4
                        },
                        "thickness": 0.8,
                        "value": 135
                    }
                }
            )
        )

        fig.update_layout(
            height=320,
            margin=dict(l=25, r=25, t=70, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "Arial"}
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

        st.caption(
            "Illustrative guide: this meter highlights 120–150 WPM "
            "as a target range. The best pace depends on the speaker, "
            "language and speaking situation."
        )

        # ---------------- OVERALL PERFORMANCE METER ----------------
        st.markdown(
            '<div class="section-title">🏆 Overall Speech Performance</div>',
            unsafe_allow_html=True
        )
        score_col, detail_col = st.columns([1, 1.5])

        with score_col:
            score_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=overall_score,
                number={"suffix": "%", "font": {"size": 38, "color": "#5C4033"}},
                title={"text": "Estimated Performance Score", "font": {"size": 17, "color": "#5C4033"}},
                gauge={
                    "axis": {"range": [0, 100], "dtick": 20, "tickcolor": "#806B5D"},
                    "bar": {"color": "#A47148", "thickness": 0.28},
                    "bgcolor": "#FFFCF8",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "#F3E2D8"},
                        {"range": [50, 75], "color": "#F2E5D5"},
                        {"range": [75, 100], "color": "#E2E9DA"}
                    ],
                    "threshold": {"line": {"color": "#795548", "width": 4}, "thickness": 0.8, "value": 75}
                }
            ))
            score_fig.update_layout(
                height=290,
                margin=dict(l=20, r=20, t=65, b=15),
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})

        with detail_col:
            st.markdown("**Your delivery breakdown**")
            components = [
                ("Speaking speed", speed_score),
                ("Pitch control", pitch_score),
                ("Pitch variation", variation_score),
                ("Vocal energy", energy_score),
            ]
            for label, score in components:
                if score is not None:
                    st.write(f"**{label}: {round(score)}/100**")
                    st.progress(max(0.0, min(1.0, score / 100.0)))
            st.caption(
                "The overall score is a practice estimate weighted toward speaking speed. "
                "Pitch, energy and variation are approximate audio features; a higher score "
                "does not mean one voice type is inherently better."
            )

        if avg_wpm < 120:
            st.info(
                "💡 Your pace is below the highlighted target range. "
                "Try speaking a little faster while staying clear."
            )
        elif avg_wpm <= 150:
            st.success(
                "🎉 Your speaking speed is within the highlighted target range!"
            )
        else:
            st.info(
                "💡 Your pace is above the highlighted target range. "
                "Try slowing down slightly and pausing between ideas."
            )

        # ---------------- TRANSCRIPT ----------------
        st.markdown(
            '<div class="section-title">📄 Speech Transcript</div>',
            unsafe_allow_html=True
        )

        with st.expander("View your complete transcript", expanded=True):
            st.write(data.get("transcript", "Transcript not available."))

        # ---------------- GRAPH ----------------
        if data.get("graph"):
            st.markdown(
                '<div class="section-title">📈 Speech Analysis Graph</div>',
                unsafe_allow_html=True
            )

            try:
                graph_bytes = base64.b64decode(data["graph"])
                st.image(
                    graph_bytes,
                    caption=(
                        "Green = ideal range | Red = problem areas | "
                        "S1, S2... = sentences"
                    ),
                    use_container_width=True
                )
            except Exception:
                st.warning("The analysis graph could not be displayed.")

        # ---------------- DETECTED ISSUES ----------------
        st.markdown(
            '<div class="section-title">🔍 Detected Issues</div>',
            unsafe_allow_html=True
        )

        regions = data.get("regions", [])

        if regions:
            region_df = pd.DataFrame(regions).rename(
                columns={
                    "from": "Start (seconds)",
                    "to": "End (seconds)",
                    "issue": "Detected Issue"
                }
            )

            st.dataframe(
                region_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("🎉 No long-duration issues were detected.")

        # ---------------- SENTENCE-WISE FEEDBACK ----------------
        st.markdown(
            '<div class="section-title">💬 Sentence-wise Feedback</div>',
            unsafe_allow_html=True
        )

        for i, item in enumerate(results, start=1):

            sentence = item.get("sentence", "")
            tips = item.get("tips") or []

            with st.expander(f"Sentence {i}", expanded=bool(tips)):

                st.write(f"**What you said:** {sentence}")

                if tips:
                    st.warning("Suggestions for improvement")

                    for tip in tips:
                        st.write(f"• {tip}")
                else:
                    st.success("No issues flagged for this sentence.")

        # ---------------- DETAILED TABLE ----------------
        st.markdown(
            '<div class="section-title">📋 Detailed Measurements</div>',
            unsafe_allow_html=True
        )

        table = pd.DataFrame(results).drop(
            columns=["tips"],
            errors="ignore"
        )

        table.index = [
            f"Sentence {i}"
            for i in range(1, len(table) + 1)
        ]

        st.dataframe(
            table,
            use_container_width=True
        )

        # ---------------- AUDIO COMPARISON ----------------
        st.markdown(
            '<div class="section-title">🎧 Listen and Compare</div>',
            unsafe_allow_html=True
        )

        original_col, ideal_col = st.columns(2)

        with original_col:
            st.markdown("**Your Original Recording**")
            st.audio(recording)

        with ideal_col:
            st.markdown("**AI Clear-Delivery Reference (Same Transcript)**")

            if data.get("ideal_audio"):
                try:
                    ideal_bytes = base64.b64decode(data["ideal_audio"])
                    st.audio(ideal_bytes, format="audio/mp3")
                    st.caption(
                        "This is a synthetic reference reading of the transcribed words. "
                        "It is not your own voice cloned or altered. Fillers such as “like” "
                        "are kept only when the speech recognizer includes them in the transcript."
                    )
                except Exception:
                    st.warning("The reference audio could not be played.")
            else:
                st.info("Reference audio is not available. Check the backend logs for the text-to-speech error.")

        # ---------------- FOOTER ----------------
        st.divider()
        st.caption(
            "Speech Coach AI · Practice regularly to improve clarity, "
            "pace and confidence."
        )
