import base64

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Speech Coach", page_icon="🎤", layout="wide")
st.title("🎤 Speech Coach")

# Sidebar: Colab ka link aur language
url = st.sidebar.text_input("Backend URL", placeholder="https://xxxx.trycloudflare.com")
lang = st.sidebar.selectbox("Language", ["en", "hi"])

recording = st.audio_input("Record karo (3-4 sentence bolo)")

if recording and st.button("Analyze"):
    if not url:
        st.error("Pehle sidebar me backend ka URL daalo")
        st.stop()

    with st.spinner("Backend pe analysis ho raha hai... (20-40 second)"):
        try:
            # recording ko backend ko bhejo
            response = requests.post(
                url.rstrip("/") + "/analyze",
                files={"file": ("recording.wav", recording.getvalue(), "audio/wav")},
                data={"lang": lang},
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            st.error(f"Backend se connect nahi hua: {e}")
            st.stop()

    results = data["results"]
    if not results:
        st.warning("Koi sentence nahi mila. Thoda zyada aur saaf bolo.")
        st.stop()

    # ---------- Summary ----------
    problem_count = sum(1 for r in results if r["tips"])
    avg_wpm = sum(r["rate"] or 0 for r in results) / len(results) * 60
    c1, c2, c3 = st.columns(3)
    c1.metric("Sentences", len(results))
    c2.metric("Average speed", f"{avg_wpm:.0f} words/min")
    c3.metric("Problem wale sentences", problem_count)

    # ---------- Transcript ----------
    with st.expander("Transcript (jo tumne bola)"):
        st.write(data["transcript"])

    # ---------- Graph ----------
    st.subheader("Graph")
    st.image(base64.b64decode(data["graph"]),
             caption="Hara = IDEAL range | Laal = problem wale hisse | S1, S2... = sentences")

    # ---------- Issues (time ke sath) ----------
    st.subheader("Detected issues (kis time pe kya problem)")
    if data["regions"]:
        st.dataframe(pd.DataFrame(data["regions"]).rename(
            columns={"from": "From (s)", "to": "To (s)", "issue": "Issue"}))
    else:
        st.success("Koi lamba issue nahi mila 🎉")

    # ---------- Sentence-wise result ----------
    st.subheader("Kaise bolna chahiye (sentence-wise)")
    for i, item in enumerate(results, start=1):
        if item["tips"]:
            st.error(f"❌ S{i}: {item['sentence']}")
            for tip in item["tips"]:
                st.write("→", tip)
        else:
            st.success(f"✅ S{i}: {item['sentence']}")

    # ---------- Numbers ----------
    st.subheader("Numbers")
    table = pd.DataFrame(results).drop(columns="tips")
    table.index = [f"S{i}" for i in range(1, len(table) + 1)]
    st.dataframe(table)

    # ---------- Audio ----------
    st.subheader("Sun ke compare karo")
    st.write("Tumhari recording:")
    st.audio(recording)
    st.write("Sudhri hui (ideal) recording:")
    st.audio(base64.b64decode(data["ideal_audio"]), format="audio/mp3")
