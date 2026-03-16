import streamlit as st
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

st.set_page_config(page_title="ENBD Reddit Dashboard", layout="wide")
st_autorefresh(interval=60000)

file_time = os.path.getmtime("bank_reddit_posts_last_week.csv")

dubai = pytz.timezone("Asia/Dubai")
last_update = datetime.fromtimestamp(file_time, dubai)
st.write("Last data update:", last_update.strftime("%Y-%m-%d %H:%M:%S"))


#st.title("Emirates NBD Reddit Sentiment Dashboard")

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