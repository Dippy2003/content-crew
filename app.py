"""Streamlit frontend for the CrewAI content pipeline.

Run with:
    streamlit run app.py
"""

import os

import streamlit as st

from content_pipeline import run_with_retries, save_article

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

st.set_page_config(page_title="Content Crew", page_icon="📝")
st.title("Content Crew")
st.caption("Researcher → Writer → Editor, powered by CrewAI + Groq")

topic = st.text_input("Topic", placeholder="e.g. the future of electric vehicles")
run_clicked = st.button("Generate article", type="primary", disabled=not topic.strip())

if run_clicked:
    with st.spinner(f"Running the crew on '{topic}'... this can take a minute or two."):
        result = run_with_retries(topic)

    if result is None:
        st.error("The pipeline failed after multiple retries. Check your API key and connection.")
    else:
        path = save_article(topic, result)
        st.success(f"Saved to {os.path.basename(path)}")
        st.markdown(str(result))

st.divider()
st.subheader("Past articles")

if not os.path.isdir(OUTPUTS_DIR):
    st.info("No articles generated yet.")
else:
    files = sorted(os.listdir(OUTPUTS_DIR), reverse=True)
    if not files:
        st.info("No articles generated yet.")
    for filename in files:
        path = os.path.join(OUTPUTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with st.expander(filename):
            st.markdown(content)
            st.download_button(
                "Download",
                data=content,
                file_name=filename,
                mime="text/markdown",
                key=f"download_{filename}",
            )
