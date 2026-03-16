import streamlit as st
import os

st.set_page_config(page_title="ENBD Reddit Dashboard", layout="wide")

st.title("Emirates NBD Reddit Sentiment Dashboard")

html_file = "ReddIt_weekly_post_analysis.html"

if os.path.exists(html_file):
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    st.components.v1.html(
        html_content,
        height=1200,
        scrolling=True
    )

else:
    st.warning("Report not generated yet.")