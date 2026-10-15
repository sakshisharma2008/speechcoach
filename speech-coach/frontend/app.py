```python
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

# ---------------- PROFESSIONAL CSS ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f5f7ff, #eef2ff);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

.hero {
    background: linear-gradient(120deg, #312e81, #6366f1, #8b5cf6);
    padding: 30px;
    border-radius: 22px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 8px 25px rgba(79, 70, 229, 0.20);
}

.hero h1 {
    color: white;
    font-size: 36px;
    margin-bottom: 8px;
}

.hero p {
    color: #eef2ff;
    font-size: 16px;
    margin-bottom: 0;
}

.section-title {
    color: #312e81;
    font-size: 23px;
    font-weight: 700;
    margin-top: 15px;
    margin-bottom: 12px;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #e0e7ff;
    box-shadow: 0 4px 15px rgba(49, 46, 129, 0.06);
}

div[data-testid="stMetricLabel"] {
    color: #64748b;
}

div[data-testid="stMetricValue"] {
    color: #312e81;
}

.stButton > button {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: 600;
    width: 100%;
}

.stButton > button:hover {
    color: white;
    border: 1px solid #a5b4fc;
}

div[data-testid="stExpander"] {
    background: white;
    border-radius: 12px;
    border: 1px solid #e0e7ff;
}

div[data-testid="stAudioInput"] {
    background: white;
    padding: 16px;
    border-radius: 14px;
}

</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------
st.markdown("""
<div class="hero">
    <h1>🎤 Speech Coach AI</h1>
    <p>
        Improve your speaking skills with speech speed measurement,
        sentence analysis and personalized feedback.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    url = st.text_input(
        "Backend URL",
        placeholder="https://xxxx.trycloudflare.com"
    )

    lang = st.selectbox(
        "Select Language",
        ["en", "hi"],
        format_func=lambda x: "English" if x == "en" else "Hindi"
    )

    st.divider()

    st.caption("🎙️ Record 3–4 complete sentences.")
    st.caption("🔗 Start your Colab backend before analysis.")


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

        # Assumes each sentence's rate is measured in words per second.
        rates = [
            float(item.get("rate") or 0)
            for item in results
        ]

        avg_wpm = sum(rates) / len(rates) * 60

        total_sentences = len(results)
        issue_percentage = (problem_count / total_sentences) * 100

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
                    "font": {"size": 34, "color": "#312e81"}
                },
                title={
                    "text": "Your Average Speaking Speed",
                    "font": {"size": 19, "color": "#334155"}
                },
                gauge={
                    "axis": {
                        "range": [0, 240],
                        "tickwidth": 1,
                        "tickcolor": "#64748b",
                        "dtick": 30
                    },
                    "bar": {
                        "color": "#4f46e5",
                        "thickness": 0.25
                    },
                    "bgcolor": "white",
                    "borderwidth": 0,
                    "steps": [
                        {
                            "range": [0, 100],
                            "color": "#fee2e2"
                        },
                        {
                            "range": [100, 120],
                            "color": "#fef3c7"
                        },
                        {
                            "range": [120, 150],
                            "color": "#dcfce7"
                        },
                        {
                            "range": [150, 180],
                            "color": "#fef3c7"
                        },
                        {
                            "range": [180, 240],
                            "color": "#fee2e2"
                        }
                    ],
                    "threshold": {
                        "line": {
                            "color": "#16a34a",
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
            st.markdown("**Improved / Ideal Recording**")

            if data.get("ideal_audio"):
                try:
                    ideal_bytes = base64.b64decode(data["ideal_audio"])
                    st.audio(ideal_bytes, format="audio/mp3")
                except Exception:
                    st.warning("The ideal audio could not be played.")
            else:
                st.info("Ideal audio is not available from the backend.")

        # ---------------- FOOTER ----------------
        st.divider()
        st.caption(
            "Speech Coach AI · Practice regularly to improve clarity, "
            "pace and confidence."
        )
```
