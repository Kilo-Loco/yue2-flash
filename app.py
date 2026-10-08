# Minimal local UI for the deployed YuE2 endpoint.
# run: streamlit run app.py   (uses RUNPOD_CALLER_KEY and ENDPOINT_ID from .env)
import base64
import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
URL = f"https://api.runpod.ai/v2/{os.environ['ENDPOINT_ID']}"
HEADERS = {"Authorization": f"Bearer {os.environ['RUNPOD_CALLER_KEY']}"}

st.title("YuE2 song generator")
prompt = st.text_input("Style", "English, upbeat indie pop, bright female vocals, jangly guitars, 120 BPM")
lyrics = st.text_area("Lyrics (optional, use [Verse] / [Chorus] tags)", height=250)

if st.button("Generate"):
    payload = {"prompt": prompt}
    if lyrics.strip():
        payload["lyrics"] = lyrics

    # Queue the job, then poll its status until it finishes.
    job = requests.post(f"{URL}/run", json={"input": payload}, headers=HEADERS).json()
    with st.spinner("Generating... about 1-2 minutes, longer on a cold start"):
        while job.get("status") not in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"):
            time.sleep(5)
            job = requests.get(f"{URL}/status/{job['id']}", headers=HEADERS).json()

    # Flash's handler reports exceptions inside the output, so check both places.
    output = job.get("output") or {}
    if job.get("status") != "COMPLETED" or "error" in output:
        st.error(job.get("error") or output.get("error") or job)
    else:
        st.audio(base64.b64decode(output["mp3_base64"]), format="audio/mpeg")
        st.caption(f"{output['seconds']}s")
