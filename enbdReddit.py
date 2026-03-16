#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import re
import io
import html
import time
import base64
import mimetypes
import smtplib
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import praw
from prawcore.exceptions import OAuthException, ResponseException
from openai import OpenAI
from email.message import EmailMessage
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  


# In[2]:


CLIENT_ID     = "ALiSw7F6CIwnECW-3UwZYg".strip()
CLIENT_SECRET = "DzwkqQZpiD4KVdzodVj9CEENZ-zKKg".strip()
USER_AGENT    = "post_bank/1.0 (u/Kind_Ad_910; bank keyword research)"


# In[3]:


try:
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
        check_for_async=False,
    )
    reddit.read_only = True

    # light endpoint
    _ = list(reddit.subreddit("test").hot(limit=1))
    print("✅ Basic read OK")
    print("me():", reddit.user.me())          # likely None (userless read)
    print("scopes:", reddit.auth.scopes())    # should include 'read'

except (OAuthException, ResponseException) as e:
    print("❌ OAuth failed:", repr(e))


# In[4]:


LIMIT = 500   # number of results to fetch per bank
DAYS  = 1     # lookback period


# In[5]:


USER_AGENT = "post_bank/1.0 (u/Kind_Ad_910; bank keyword research)"
HEADERS = {"User-Agent": USER_AGENT}

BANK_QUERIES = {
    "ENBD": '("emirates nbd" OR enbd OR "INC4588878")',
    "ADCB": '("abu dhabi commercial bank" OR adcb)',
    "ADIB": '("abu dhabi islamic bank" OR adib)',
    "EI":   '("emirates islamic")',
    "FAB":  '("first abu dhabi bank")',
    "CBD":  '("commercial bank of dubai")',
    "Mashreq": '("mashreq")',
}

# Date cutoff
cutoff = datetime.utcnow() - timedelta(days=DAYS)

all_posts = []

for bank, query in BANK_QUERIES.items():
    print(f"🔎 Searching for {bank} posts in last {DAYS} days (across Reddit)...")
    try:
        for submission in reddit.subreddit("all").search(query, sort="new", limit=LIMIT):
            created_dt = datetime.utcfromtimestamp(submission.created_utc)
            if created_dt >= cutoff:
                all_posts.append({
                    "bank": bank,
                    "subreddit": submission.subreddit.display_name,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "url": submission.url,
                    "permalink": f"https://www.reddit.com{submission.permalink}",
                    "created_utc": submission.created_utc,
                    "created_date": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "author": str(submission.author),
                    "id": submission.id,
                })
    except Exception as e:
        print(f"⚠️ Error fetching {bank}: {e}")
    time.sleep(2)  # be polite

# Save results
df = pd.DataFrame(all_posts).drop_duplicates(subset=["id"])
df.to_csv("bank_reddit_posts_last_week.csv", index=False, encoding="utf-8")

print(f"✅ Extracted {len(df)} posts across Reddit in last {DAYS} days.")


# In[6]:


Code_start_time1=datetime.now()


# In[7]:


# rename multiple columns
df = df.rename(columns={
    "url": "link_used",
    "subreddit": "to",
    "selftext":"post_text",
    "selftext":"post_text",
    "score": "points_num",
    "num_comments": "comments_num",
    
})


# In[8]:


mapping = {


"ADCB":'4. Abu Dhabi Commercial Bank (ADCB)',



"ADIB":"5. Abu Dhabi Islamic Bank (ADIB)",

"ENBD":"1. Emirates NBD Bank (ENBD)",


"EI":'2. Emirates Islamic Bank (EIB)',


"CBD":"6. Commercial Bank of Dubai (CBD)",


"FAB":"3. First Abu Dhabi Bank (FAB)",


"Mashreq":'7. Mashreq Bank',

}


# In[9]:


df["Bank_Name"] = df["bank"].map(mapping)


# In[10]:


# Create new column: if post_text is NaN or empty, use title
df["text"] = np.where(df["post_text"].isna() | (df["post_text"] == ""), 
                            df["title"], 
                            df["post_text"])


# In[11]:


df=df.drop_duplicates()


# In[12]:


final_df=df


# In[13]:


# Remove blank post
final_df=final_df[(final_df['text'].notna()) & (final_df['text'].str.strip() != '')]

# Remove rows containing unwanted text
unwanted_phrases = [
    "check out this job", "we're hiring", "join us", "apply now", "hiring", "looking for a new job", "job by emirates nbd",
    "careers in","jobs in uae",'job openings','get a job','send cv','job opportunity','dear hiring team',"jobs opening","careers uae",
    "Job vacanc","human resources","job","my cv", "i am looking a",'started a new position','starting a new position','a new position'
]


final_df = final_df[~final_df['text'].str.lower().str.contains('|'.join(phrase.lower() for phrase in unwanted_phrases))]

final_df['post'] = (
    final_df['text']
    .str.replace('\n', ' ', regex=False)         # Replace line breaks with space
    .str.replace(r'\s+', ' ', regex=True)        # Remove multiple spaces
    .str.strip()                                 # Remove leading/trailing spaces
    .str.lower()                                 # Convert to lowercase
)


# In[14]:


# Function to remove emojis and symbols
def remove_emojis(text):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # Emoticons
        u"\U0001F300-\U0001F5FF"  # Symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # Transport & map symbols
        u"\U0001F700-\U0001F77F"  # Alchemical
        u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        u"\U0001FA00-\U0001FA6F"  # Chess Symbols
        u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        u"\U00002700-\U000027BF"  # Dingbats
        u"\U000024C2-\U0001F251"  # Enclosed characters
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


# In[15]:


final_df['post'] = final_df['post'].apply(remove_emojis)


# In[16]:


final_df["post_date"]=final_df['created_date']


# In[17]:


final_df["post_date"]= pd.to_datetime(final_df["post_date"])


# In[18]:


final_df["ddmmyyyy"] =final_df["post_date"].dt.strftime("%d%b%Y")


# In[19]:


final_df_v1=final_df


# In[20]:


try:
    key = st.secrets["OPENAI_API_KEY"]
except Exception:
    key = os.getenv("OPENAI_API_KEY")

# In[21]:



client = OpenAI(api_key=key)


# In[22]:


def analyze_sentiment(text):
    prompt = f"Classify the post text Sentiment about First Abu Dhabi Bank,Emirates NBD Bank,Mashreq Bank,Emirates Islamic Bank,Abu Dhabi Islamic Bank,Commercial Bank of Dubai,Abu Dhabi Commercial Bank in one word only (Positive, Negative, Neutral) and inflation text were classify as Neutral if post sentiment is negative for all the banks classify as Nuetral:\n\n{text}"
        
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # lightweight + cost effective
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    
    return response.choices[0].message.content.strip()


# In[23]:


def translate_to_english(text: str) -> str:
    """Detect language, translate to English, and clean output."""
    if not isinstance(text, str) or not text.strip():
        return ""
    prompt = (
        "Detect the language and translate the text to fluent English. "
        "Return ONLY the translated English text, no quotes, no extras spaces and clean output.\n\n"
        f"Text:\n{text}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content.strip()


# In[24]:


def _clean_text(t):
    if t is None: return ""
    t = str(t).strip()
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t)
    # Trim super long
    return t[:6000]  # safety

def genai_highlights(text, max_bullets=3, timeout_s=20):
    """
    Returns a list of 2-3 short bullet highlights.
    Uses OpenAI if API key is present; otherwise falls back to a local method.
    """
    text = _clean_text(text)
    if not text:
        return []

    if _USE_GENAI and _client is not None:
        try:
            prompt = (
                "You are a concise analyst. Read the post text and extract the top 2–3 key highlights.\n"
                "- Each highlight must be a single, short bullet (max ~15 words)\n"
                "- Be factual and avoid marketing fluff\n"
                "- If numbers, product names, or dates are present, keep them\n"
                " convert text to English\n"
                f"\nPOST TEXT:\n{text}\n\nReturn bullets only."
            )
            resp = _client.chat.completions.create(
                model=_MODEL,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout_s,
            )
            out = resp.choices[0].message.content.strip()
            # Split into bullets robustly
            bullets = [b.strip("•- ").strip() for b in re.split(r"[\n\r]+", out) if b.strip()]
            bullets = [b for b in bullets if len(b) > 0][:max_bullets]
            return bullets
        except Exception:
            pass  # fall through to local

    # --- Local fallback: simple extractive highlights (no deps) ---
    # 1) sentence split
    sents = re.split(r"(?<=[\.\!\?])\s+", text)
    sents = [s.strip() for s in sents if 25 <= len(s.strip()) <= 200][:15]
    if not sents:
        return [text[:120] + ("…" if len(text) > 120 else "")]
    # 2) score by keyword frequency
    words = re.findall(r"[A-Za-z0-9%]+", text.lower())
    stop = set("""a an the and or of to for in on at by with as is are was were be been being this that these those it its from into over under about more most less least up down out not no yes your our their his her they we you i""".split())
    freq = {}
    for w in words:
        if w in stop or len(w) < 3: continue
        freq[w] = freq.get(w, 0) + 1
    def score(sent):
        tokens = re.findall(r"[A-Za-z0-9%]+", sent.lower())
        sc = sum(freq.get(w, 0) for w in tokens)
        # reward digits/percents slightly
        sc += 1.5 * sum(ch.isdigit() for ch in sent)
        return sc
    ranked = sorted(sents, key=score, reverse=True)[:max_bullets]
    return [re.sub(r"\s+", " ", s) for s in ranked]


# In[25]:


final_df_v1['org_post']=final_df_v1['post']


# In[26]:


final_df_v1.head(1)


# In[27]:


# 1) Translate to English (new column)
final_df_v1["post"] = final_df_v1["org_post"].astype(str).apply(translate_to_english)


# In[28]:


# --- Bank aliases dictionary ---
bank_keywords = {
    "ENBD": ["enbd", "emirates nbd"],
    "ADCB": ["adcb", "abu dhabi commercial"],
    "ADIB": ["abu dhabi islamic"],
    "EIB":  ["emirates islamic"],
    "FAB":  ["fab", "first abu dhabi"],
    "CBD":  ["cbd", "commercial"],
    "Mashreq": ["mashreq"],
}

# --- Flatten all keywords to lowercase ---
all_keywords = [kw.lower() for kws in bank_keywords.values() for kw in kws]


# In[29]:


# --- Function: check if post contains any keyword ---
def contains_bank(text):
    t = str(text).lower()
    return any(kw in t for kw in all_keywords)


# In[30]:


final_df_v1['lower_post']=final_df_v1["post"].str.lower()


# In[31]:




# --- Filter DataFrame ---
final_df_v1 = final_df_v1[final_df_v1["lower_post"].apply(contains_bank)].reset_index(drop=True)


# In[32]:


# Apply sentiment analysis
final_df_v1["Sentiment"] = final_df_v1["post"].apply(analyze_sentiment)


# In[33]:


final_df_v1["row_number"] = range(1, len(final_df_v1) + 1)


# In[34]:


_USE_GENAI = os.getenv(key)
if _USE_GENAI:
    try:
        from openai import OpenAI
        _client = OpenAI()
        _MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # fast & cheap; change if you like
    except Exception:
        _USE_GENAI = False
        _client = None


# In[35]:



final_df_v1["post_highlights"] = final_df_v1["post"].apply(
    lambda txt: " • ".join(genai_highlights(txt, max_bullets=3))
)


# In[36]:


# Get min and max
min_date = final_df_v1["post_date"].min()
max_date = final_df_v1["post_date"].max()

print("Minimum date:", min_date)
print("Maximum date:", max_date)


# In[37]:


# Format into DDMMMYYYY (e.g., 01OCT2025)
date_str = max_date.strftime("%d%b%Y").upper()

# Create filename
file_name = f"Reditt_week_Data_{date_str}.xlsx"


# In[38]:


# Remove rows containing unwanted text
unwanted_phrases = [
    "check out this job", "we're hiring", "join us", "apply now", "hiring", "looking for a new job", "job by emirates nbd",
    "careers in","jobs in uae",'job openings','get a job','send cv','job opportunity','dear hiring team',"jobs opening","careers uae",
    "Job vacanc","human resources","job","my cv",'started a new position','starting a new position','a new position','adcb metro'
]

# Drop rows where 'post' is None/NaN before filtering
final_df_v1 = final_df_v1.dropna(subset=['post'])

final_df_v1 = final_df_v1[~final_df_v1['post'].str.lower().str.contains('|'.join(phrase.lower() for phrase in unwanted_phrases))]


# In[39]:


# remove leading 1., 2), 3-, 4: (any digits + optional punctuation) + spaces
final_df_v1["Name_of_bank"] = final_df_v1["Bank_Name"].str.replace(r"^\s*\d+[\.\)\-:]*\s*", "", regex=True)


# In[40]:


final_df_v1["Bank_Name"] = final_df_v1["Bank_Name"].fillna(final_df_v1["Name_of_bank"])


# In[41]:


final_df_v1["author_type"] = "Cust"


# In[42]:


# Create new column 'most_likes' if likes > 100
final_df_v1["most_points"] = final_df_v1["points_num"].apply(lambda x: 1 if x > 100 else 0)


# In[43]:


final_df_v1 = final_df_v1.rename(columns={"author": "author_name"})


# In[44]:


final_df_v1 = final_df_v1[final_df_v1["author_name"].notna()]                    # remove NaN
final_df_v1 = final_df_v1[final_df_v1["author_name"].str.strip() != ""]          # remove empty/whitespace


# In[45]:


final_df_v2=final_df_v1


# In[46]:


final_df_v2


# In[47]:


summary = (
    final_df_v2.groupby(["Bank_Name","Name_of_bank"])
    .agg(
        totl_nbr_post=("Bank_Name", "size"),

        total_likes=("points_num","sum"),
        total_comments=("comments_num", "sum"),
 
        min_post_date=("post_date", "min"),
        max_post_date=("post_date", "max"),

        neg_post_count=("Sentiment", lambda x: (x == "Negative").sum()),

        # ✅ NEW: count of Bank posts with likes > 100
         cust_posts_likes_gt_100=(
            "points_num",
            lambda x: ((final_df_v2.loc[x.index, "author_type"] == "Cust") & (x > 100)).sum()
        )

    )
    .reset_index()
    .sort_values("Bank_Name")  # order by Bank_Name ascending
)


# In[48]:


post_from_dates = summary["min_post_date"].dropna().unique()
post_to_dates = summary["max_post_date"].dropna().unique()
print(f"\n ReddIt Post Analysis from {post_from_dates[0]} to {post_to_dates[0]}")


# In[49]:


final_df_v2["weekday_name"] = final_df_v2["post_date"].dt.day_name()


# In[50]:


final_df_v2['weekday_name'].value_counts()


# In[51]:


weekday_bank_counts = final_df_v2.groupby(
    ["weekday_name", "Bank_Name","Name_of_bank"]
).size().reset_index(name="post_count")


# In[52]:


#import datetime
today_date = datetime.today().strftime("%d%b%Y").upper()


# In[53]:


# Sort first by Bank_Name then likes descending
final_df_v2 = final_df_v2.sort_values(['Bank_Name', 'points_num'], ascending=[True, False])


# In[54]:


def rank_top3(d):
    # sort by engagement desc, then most recent date
    return d.sort_values(["points_num", "post_date"], ascending=[False, False]).head(3)


# In[55]:


# per-bank top 3
top3_bank_authored = (
    final_df_v2.groupby("Bank_Name", group_keys=False)
    .apply(rank_top3)
    .reset_index(drop=True)
)
top3_bank_authored["Bank_Name"] = top3_bank_authored.get("Bank_Name", top3_bank_authored["Name_of_bank"])
print(top3_bank_authored.columns)
print(top3_bank_authored.head())
# In[56]:


neg_table=final_df_v2[(final_df_v2['Sentiment'] == 'Negative')]


# In[57]:


base_name="ReddIt_weekly_post_analysis"


# In[58]:


OUT_PATH = f"{base_name}.html"


# In[59]:


def embed_data_url(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

# point to your actual file (exact filename & case!)
logo_data_url = embed_data_url("enbd_logo.png")


# In[60]:


# ---------- helpers ----------
def fmt_date9(dt):
    if pd.isna(dt) or dt is None: return ""
    return pd.to_datetime(dt).strftime("%d%b%Y").upper()

def fmt_dt_full(dt):
    if pd.isna(dt) or dt is None: return ""
    return pd.to_datetime(dt).strftime("%d%b%Y %H:%M:%S").upper()


# In[61]:


# Get min and max
min_date = final_df_v1["post_date"].min()
max_date = final_df_v1["post_date"].max()

print("Minimum date:", min_date)
print("Maximum date:", max_date)


# In[62]:


header = f"""
<div class="hero-grid">
  <div class="hero-logo">
    <img src="{logo_data_url}" alt="ENBD" class="logo">
  </div>

  <div class="genai-badge">⚡Powered by Gen AI</div>

  <div class="hero-row r1">
    <h1>Reddit Engagement Analysis for Customer posts</h1>
  </div>

  <div class="hero-row r2">
    <p>Duration: {fmt_date9(min_date)} to {fmt_dt_full(max_date)}</p>
  </div>

  <div class="hero-row r3">
    <p>Number of Banks considered for Analysis: {summary['Name_of_bank'].nunique()}</p>
  </div>
</div>
"""


# In[63]:


# ---------- CSS ----------
css = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

  :root{
    --bg:#ffffff; --card:#ffffff; --soft:#f7f9fc; --soft2:#e5e8ef; --text:#072447; --muted:#54698d;
    --pos:#2ec27e; --neg:#ff5c5c; --neu:#f0b429; --chip:#e5e8ef; --chipBorder:#d0d6e5; --shadow:0 10px 30px rgba(0,0,0,.10);
  }

  *{box-sizing:border-box; font-family: 'Plus Jakarta Sans', sans-serif;}

  body{
    margin:0;
    background:#ffffff;
    color:var(--text);
  }

  .wrap{max-width:1150px;margin:34px auto;padding:0 20px;}


  .title{font-size:28px; font-weight:800; letter-spacing:.4px; margin:0 0 6px; color:#072447;}
  .muted{color:var(--muted)}
  .section{margin-top:24px;}

  /* Add corner logo (top-right) */
  .post::after {
    content:"";
    position:absolute;
    top:30px; right:60px;
    width:28px; height:28px;
    background:url('corner_logo.png') no-repeat center center;
    background-size:contain;
    opacity:0.7;
  }


  mark{ background:#ffeb3b; color:#000; padding:0 3px; border-radius:4px; }

 
    /* --- HERO fix: force 2-col grid with 3 stacked rows --- */
        
/* GRID: 2 columns, 3 rows; logo spans all 3 rows */
.hero-grid{
  display:grid;
  grid-template-columns: auto 1fr;  /* left = logo, right = text column */
  grid-template-rows: auto auto auto;
  column-gap: 15px;
  align-items:center;               /* align items vertically in their rows */
  justify-content:center;           /* center whole block on the page */
  margin: 16px 0 24px;
}

/* LOGO: small, fixed height so it never forces wrapping */
.hero-logo{
  grid-row: 1 / span 3;             /* span all three rows */
  display:flex;
  align-items:center;
  justify-content:center;
}
.hero-logo img{
  height: 60px;                     /* ↓ reduce if needed (e.g., 100px) */
  width: auto;
  display:block;
}

/* Each row on the right is its own centered line */
.hero-row{
  display:flex;
  justify-content:center;            /* center text horizontally in the row */
  text-align:center;
  color:#0a2540;
}

.hero-row h1{
  margin:0 0 4px 0;
  font-size: 28px;                   /* adjust to taste */
  font-weight:800;
  line-height:1.2;
}
.hero-row p{
  margin: 2px 0;
  font-size: 16px;
  line-height:1.35;
}

/* Optional: stack on small screens */
@media (max-width: 680px){
  .hero-grid{
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto;
    row-gap: 10px;
    justify-content:stretch;
  }
  .hero-logo{ grid-row:auto; }
  .hero-row{ justify-content:center; }
}

.genai-badge {
  position: absolute;
  top: 60px;
  right: 40px;
  font-size: 14px;
  font-weight: 600;
  color: #072447;        /* navy */
  background: #f0f2f8;   /* light gray background */
  padding: 6px 14px;
  border-radius: 20px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.hero-grid {
  position: relative; /* so badge aligns inside hero block */
}


/* --- cards for the negative posts section --- */
.bank-section { margin-top: 24px; }
.bank-title { font-weight: 800; font-size: 18px; margin: 12px 0; }
.card {
  background:#fff; border:1px solid var(--border);
  border-radius:14px; padding:14px; margin:12px 0;
  box-shadow: var(--shadow);
}
.kv { margin: 6px 0; }
.kv b { color:#0f172a; }
.post-text {
  background:#f8fafc; border:1px dashed var(--border);
  padding: 10px; border-radius: 10px; line-height: 1.5;
}
.row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.row-right { display:flex; justify-content:flex-end; }
.badge {
  display:inline-flex; align-items:center; gap:6px;
  padding:4px 10px; font-size:12px; border-radius:999px;
  font-weight:600; border:1px solid transparent;
}
.badge-negative { background:#ef4444; color:#fff; }
.badge-customer { background:#eef2ff; color:#3730a3; border-color:#e0e7ff; }
.chip {
  display:inline-flex; align-items:center; gap:6px;
  padding:3px 10px; font-size:12px; border-radius:999px;
  background:#e2e8f0; color:#0f172a; border:1px solid var(--border);
}
.open-link { color:#1d4ed8; font-weight:700; text-decoration:none; }
.open-link:hover { text-decoration:underline; }
.page-title { font-weight:800; font-size:20px; margin:16px 0 8px; }

  :root { --bg:#f6f8fb; --text:#072447; --muted:#475569; --card:#fff; --border:#e5e7eb; --shadow:0 6px 18px rgba(0,0,0,.06); }
  .table-card { background:var(--card); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow); overflow:auto; }
  table { border-collapse:separate; border-spacing:0; width:100%; min-width:600px; }
  thead th { background:#f1f5f9; font-weight:600; font-size:13px; border-bottom:1px solid var(--border); padding:10px; }
  th:first-child, td:first-child { text-align:left; font-weight:700; }
  td { padding:10px; text-align:center; }
  tbody tr:nth-child(even) td { background:#fafbff; }
  .cell-card { background:#fff; border:1px solid var(--border); border-radius:12px; padding:6px 8px; box-shadow:var(--shadow); display:inline-block; min-width:80px; }
  .neg .cell-card { color:#b91c1c; border-color:#f3c7c7; }
</style>
"""


# In[64]:


metrics = ["totl_nbr_post", "total_likes", "total_comments", "neg_post_count", "cust_posts_likes_gt_100"]


# In[65]:


metric_labels = {
    "totl_nbr_post": "🧾 Total Posts",
    "total_likes": "👍 Total Likes",
    "total_comments": "💬 Total Comments",
    "neg_post_count": "⚠️ Negative Posts",
    "cust_posts_likes_gt_100": "⭐ Customer posts with 100+ likes"
}


# In[66]:


def build_summary_table_div(summary, metrics, metric_labels):
    # headers
    headers = ''.join(f'<th>{metric_labels[m]}</th>' for m in metrics)

    # rows
    rows = []
    for _, row in summary.iterrows():
        tds = [f"<td>{row['Name_of_bank']}</td>"]
        for m in metrics:
            val = row[m]
            try:
                val = f"{int(val):,}"
            except Exception:
                pass
            cls = "neg" if m == "neg_post_count" else ""
            tds.append(f'<td class="{cls}"><div class="cell-card">{val}</div></td>')
        rows.append(f"<tr>{''.join(tds)}</tr>")

    # DIV fragment only
    div_html = f"""
<div class="table-card">
 <div class="page-title">Part 1: Overall posts overview</div>
  <table>
    <thead>
      <tr>
        <th>Bank Name</th>
        {headers}
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
""".strip()
    return div_html

# Usage:
# table_div = build_summary_table_div(summary, metrics, metric_labels)
# html_doc = html_doc.replace("<!-- TABLE_SLOT -->", table_div)


# In[67]:


table_div=build_summary_table_div(summary,metrics,metric_labels)
#print(table_div)


# In[68]:


# convert dict to DataFrame
mapping1 = pd.DataFrame(list(mapping.items()), columns=["Key", "Bank_Name"])

# filter only keys ending with '_C'
mapping1 = mapping1[mapping1["Key"].str.endswith("_C")].reset_index(drop=True)


# In[69]:


mapping1["Name_of_bank"] = mapping1["Bank_Name"].str.replace(r"^\s*\d+[\.\)\-:]*\s*", "", regex=True)
mapping1=mapping1.drop(columns=["Key"])


# In[70]:


full_banks=mapping1["Bank_Name"].unique().tolist()


# In[71]:


present_banks = weekday_bank_counts["Bank_Name"].unique().tolist()
missing_banks = [b for b in full_banks if b not in present_banks]


# In[72]:


# --- Only add if missing ---
if missing_banks:
    new_rows = pd.DataFrame({
        "weekday_name": ["Sunday"] * len(missing_banks),
        "Bank_Name": missing_banks,
        "Name_of_bank": [b.split(". ",1)[1] for b in missing_banks],
        "post_count": [0] * len(missing_banks)
    })
    weekday_bank_counts = pd.concat([weekday_bank_counts, new_rows], ignore_index=True)
else:
    weekday_bank_counts = weekday_bank_counts.copy()


# In[73]:


# Sort weekdays in natural order (Mon–Sun)
weekday_order = ["Thursday","Friday","Saturday","Sunday","Monday","Tuesday","Wednesday"]
weekday_bank_counts["weekday"] = pd.Categorical(weekday_bank_counts["weekday_name"], categories=weekday_order, ordered=True)

pivot_df = weekday_bank_counts.pivot(index="weekday", columns="Name_of_bank", values="post_count").fillna(0)


# In[74]:




# Optional: ensure weekday order on x-axis if needed
if 'weekday_order' in globals():
    try:
        pivot_df = pivot_df.reindex(weekday_order)
    except Exception:
        pass
        
# Custom colors
custom_colors = [
    "#ED1C24",  # ADCB
    "#009ada",  # ADIB
    "#2ca02c",  # CDB
    "#8C4799",  # EIB
    "#072447",  # ENBD
    "#003399",  # FAB
    "#FF671F",  # Mashreq
    "#bcbd22",  # olive
    "#17becf"   # cyan
]

# --- Build the figure ---
#plt.close('all')
fig, ax = plt.subplots(figsize=(10, 5))

x_vals = pivot_df.index.astype(str).tolist()
bar_width = 0.12   # adjust width so bars don’t overlap

# Each bank → separate bar group
for i, col in enumerate(pivot_df.columns):
    y_vals = pivot_df[col].values
    color = custom_colors[i % len(custom_colors)]
    # shift bars by (i * bar_width)
    ax.bar(
        [x + i*bar_width for x in range(len(x_vals))],
        y_vals,
        width=bar_width,
        label=col,
        color=color
    )

# Fix x-axis ticks to center groups
ax.set_xticks([r + (len(pivot_df.columns)/2 - 0.5)*bar_width for r in range(len(x_vals))])
ax.set_xticklabels(x_vals)

# Labels & formatting
ax.set_title("Weekday-wise Post Counts", fontweight="bold")
ax.set_xlabel("Weekday", fontweight="bold")
ax.set_ylabel("Number of Posts", fontweight="bold")
ax.legend(title="Bank Names", fontsize=8)
ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

plt.tight_layout()

# Add vertical separator lines between days
#plt.grid(axis="x", which="major", linestyle="--", linewidth=0.7, color="gray")

# Or, for more control, draw manual vertical lines
for i in range(len(pivot_df.index) - 1):
    plt.axvline(x=i + 0.8, color="gray", linestyle="--", linewidth=0.8)
    
# Add values above each bar
for container in ax.containers:
    ax.bar_label(container, label_type="edge", fontsize=9, padding=2)
# --- Save to PNG in-memory and base64-embed ---
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
buf.seek(0)
png_b64 = base64.b64encode(buf.read()).decode("ascii")

chart_img_html = (
    f'<img src="data:image/png;base64,{png_b64}" '
    f'alt="Weekday-wise Bank Post Counts" '
    f'style="max-width:100%;height:auto;display:block;border:0;" />'
)
#print(chart_img_html)

# In[75]:




def esc(x):
    return html.escape("" if pd.isna(x) else str(x), quote=False)

def find_column(cols, candidates:set):
    colset = set(cols)
    for c in candidates:
        if c in colset: return c
    lower = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in lower: return lower[c.lower()]
    return None


# 
# 
# def build_negative_section_div(df: pd.DataFrame) -> str:
#     # map required/optional columns
#     author_col = find_column(df.columns, {"author_name"})
#     bank_col   = find_column(df.columns, {"Name_of_bank"})
#     date_col   = find_column(df.columns, {"ddmmyyyy"})
#     text_col   = find_column(df.columns, {"org_post"})
#     high_col   = find_column(df.columns, {"post_highlights"})
#     likes_col  = find_column(df.columns, {"points_num"})
#     comm_col   = find_column(df.columns, {"comments_num"})
#     link_col   = find_column(df.columns, {"permalink"})
# 
#     for name, col in [("author_name", author_col),
#                       ("Name_of_bank", bank_col),
#                       ("ddmmyyyy", date_col),
#                       ("post_text", text_col),
#                       ("post_highlights", high_col)]:
#         if col is None:
#             raise ValueError(f"Missing required column: {name}")
# 
#     df = df.copy()
#     df["_post_date_fmt"] = df[date_col]
#     df["_bank"] = df[bank_col].fillna("").astype(str)
#     df = df.sort_values("Bank_Name").reset_index(drop=True)
# 
#     pieces = ['<div class="page-title">Part 2: Negative Posts by Customer</div>']
#     for bank, g in df.groupby("_bank"):
#         bank_label = esc(bank) if bank else "Unknown Bank"
#         cards = []
#         for _, row in g.iterrows():
#             author    = esc(row[author_col])
#             post_date = esc(row["_post_date_fmt"])
#             post_text = esc(row[text_col])
# 
#             raw_h = "" if pd.isna(row[high_col]) else str(row[high_col])
#             pts = [p.strip(" •-") for p in re.split(r"\n|•|;|\u2022|\r", raw_h) if p.strip()]
#             bullets = "\n".join(f"<li>{esc(p)}</li>" for p in pts) if pts else ""
# 
#             likes = 0 if likes_col is None or pd.isna(row[likes_col]) else int(row[likes_col])
#             comms = 0 if comm_col is None or pd.isna(row[comm_col]) else int(row[comm_col])
#             link  = "" if (link_col is None or pd.isna(row[link_col])) else str(row[link_col]).strip()
# 
#             open_link_html = (
#                 f'<div class="row-right" style="margin-top:8px;">'
#                 f'<a class="open-link" href="{esc(link)}" target="_blank" rel="noopener">Open post ↗</a>'
#                 f'</div>'
#             ) if link else ""
# 
#             cards.append(f"""
# <div class="card">
#   <div class="kv"><b>Author Name:</b> {author}</div>
#   <div class="kv"><b>Bank Name:</b> {bank_label}</div>
#   <div class="kv"><b>Post Date:</b> {post_date}</div>
#   <div class="kv"><b>Post text:</b></div>
#   <div class="post-text">{post_text}</div>
#   <div class="highlights">
#     <h4>Key highlights of Post</h4>
#     <ul>{bullets}</ul>
#   </div>
#   <div class="row" style="margin-top:10px;">
#     <span class="badge badge-negative">Negative</span>
#     <span class="badge badge-customer">Posts by Customer</span>
#   </div>
#   <div class="row" style="margin-top:6px;">
#     <span class="chip">👍 Likes: {likes}</span>
#     <span class="chip">💬 Comments: {comms}</span>
#   </div>
#   {open_link_html}
# </div>""")
#         pieces.append(f"""<div class="bank-section">
#   <div class="bank-title">Negative Posts — {bank_label}</div>
#   {''.join(cards)}
# </div>""")
#     return "\n".join(pieces)
# 

# In[76]:


def build_negative_section_div(df: pd.DataFrame) -> str:
    # map required/optional columns
    author_col = find_column(df.columns, {"author_name"})
    bank_col   = find_column(df.columns, {"Name_of_bank"})
    bank2_col  = find_column(df.columns, {"Bank_Name"})  # preferred sort/label
    date_col   = find_column(df.columns, {"ddmmyyyy"})
    text_col   = find_column(df.columns, {"org_post"})
    high_col   = find_column(df.columns, {"post_highlights"})
    likes_col  = find_column(df.columns, {"points_num"})
    comm_col   = find_column(df.columns, {"comments_num"})
    link_col   = find_column(df.columns, {"permalink"})

    for name, col in [("author_name", author_col),
                      ("Name_of_bank", bank_col),
                      ("ddmmyyyy", date_col),
                      ("post_text", text_col),
                      ("post_highlights", high_col)]:
        if col is None:
            raise ValueError(f"Missing required column: {name}")

    df = df.copy()
    df["_post_date_fmt"] = df[date_col]

    # Use Bank_Name if available for display + ordering; else fall back to Name_of_bank
    label_col = bank2_col if bank2_col is not None else bank_col
    df["_bank_label"] = df[label_col].fillna("").astype(str)

    # Sort by the chosen label column (was sorting by literal "Bank_Name")
    df = df.sort_values("_bank_label").reset_index(drop=True)

    pieces = ['<div class="page-title">Part 2: Negative Posts by Customer</div>']
    # Group by the same label used for sorting so the sections appear in that order
    for bank, g in df.groupby("_bank_label", sort=False):
        bank_label = esc(bank) if bank else "Unknown Bank"
        cards = []
        for _, row in g.iterrows():
            author    = esc(row[author_col])
            post_date = esc(row["_post_date_fmt"])
            post_text = esc(row[text_col])

            raw_h = "" if pd.isna(row[high_col]) else str(row[high_col])
            pts = [p.strip(" •-") for p in re.split(r"\n|•|;|\u2022|\r", raw_h) if p.strip()]
            bullets = "\n".join(f"<li>{esc(p)}</li>" for p in pts) if pts else ""

            likes = 0 if likes_col is None or pd.isna(row[likes_col]) else int(row[likes_col])
            comms = 0 if comm_col is None or pd.isna(row[comm_col]) else int(row[comm_col])
            link  = "" if (link_col is None or pd.isna(row[link_col])) else str(row[link_col]).strip()

            open_link_html = (
                f'<div class="row-right" style="margin-top:8px;">'
                f'<a class="open-link" href="{esc(link)}" target="_blank" rel="noopener">Open post ↗</a>'
                f'</div>'
            ) if link else ""

            cards.append(f"""
<div class="card">
  <div class="kv"><b>Author Name:</b> {author}</div>
  <div class="kv"><b>Bank Name:</b> {bank_label}</div>
  <div class="kv"><b>Post Date:</b> {post_date}</div>
  <div class="kv"><b>Post text:</b></div>
  <div class="post-text">{post_text}</div>
  <div class="highlights">
    <h4>Key highlights of Post</h4>
    <ul>{bullets}</ul>
  </div>
  <div class="row" style="margin-top:10px;">
    <span class="badge badge-negative">Negative</span>
    <span class="badge badge-customer">Posts by Customer</span>
  </div>
  <div class="row" style="margin-top:6px;">
    <span class="chip">👍 Likes: {likes}</span>
    <span class="chip">💬 Comments: {comms}</span>
  </div>
  {open_link_html}
</div>""")
        pieces.append(f"""<div class="bank-section">
  <div class="bank-title">Negative Posts — {bank_label}</div>
  {''.join(cards)}
</div>""")
    return "\n".join(pieces)


# In[77]:


banks_list = (
    top3_bank_authored[['Name_of_bank', 'Bank_Name']]
    .drop_duplicates()
    .sort_values('Bank_Name')
    .Name_of_bank
    .tolist()
)
print(banks_list)


# In[78]:


neg=build_negative_section_div(neg_table)


# In[79]:


banks_list = (
    top3_bank_authored[['Name_of_bank', 'Bank_Name']]
    .drop_duplicates()
    .sort_values('Bank_Name')
    .Name_of_bank
    .tolist()
)
print(banks_list)


# In[80]:




def _esc(s):
    return ("" if s is None else str(s))        .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")        .replace('"',"&quot;").replace("'","&#39;")

def _find(cols, candidates):
    for c in candidates:
        if c in cols: return c
    return None

def render_top3_per_bank(df: pd.DataFrame, banks_list, sort_by="likes") -> str:
    """
    Renders a single <div id='top3-by-bank'>…</div> containing sections for each bank in banks_list.
    - Cards are 2-up on desktop, 1-up on small screens.
    - sort_by: "likes" (default) or "eng" (likes+comments).
    Expected columns (flexible mapping):
      author_name | Name_of_bank | ddmmyyyy | org_post/post_text | post_highlights |
      points_num/likes | comments_num/comments | permalink/link
    """
    col_author = _find(df.columns, ["author_name"])
    col_bank   = _find(df.columns, ["Name_of_bank"])
    col_date   = _find(df.columns, ["ddmmyyyy"])
   
    col_high   = _find(df.columns, ["post_highlights"])
    col_likes  = _find(df.columns, ["points_num", "likes"])
    col_comm   = _find(df.columns, ["comments_num", "comments"])
    col_link   = _find(df.columns, ["permalink", "link"])

    # sanity checks
    for need,col in [("author_name", col_author),
                     ("Name_of_bank", col_bank),
                     ("ddmmyyyy", col_date),
  
                     ("post_highlights", col_high)]:
        if col is None:
            raise ValueError(f"Missing required column: {need}")

    d = df.copy()
    d["_likes"] = d[col_likes].fillna(0).astype(int) if col_likes else 0
    d["_comms"] = d[col_comm].fillna(0).astype(int) if col_comm else 0
    d["_eng"]   = d["_likes"] + d["_comms"]
    metric_col  = "_likes" if sort_by.lower()=="likes" else "_eng"

    def card_html(row) -> str:
        raw_h = "" if pd.isna(row.get(col_high)) else str(row.get(col_high))
        pts = [p.strip(" •-") for p in re.split(r"\n|•|;|\u2022|\r", raw_h) if p.strip()]
        khl = "".join(f"<li>{_esc(x)}</li>" for x in pts[:6])

        link = "" if (not col_link or pd.isna(row.get(col_link))) else str(row.get(col_link)).strip()
        open_link = f' href="{_esc(link)}"' if link else ' href="#"'

        return f"""
<div class="card">
  <div class="row">
    <div><b>Author:</b> {_esc(row.get(col_author,""))}</div>
    <div><b>Date:</b> {_esc(row.get(col_date,""))}</div>
    <div class="row-right"><a class="open-link"{open_link} target="_blank" rel="noopener">Open post ↗</a></div>
  </div>
  <div><b>Key highlights</b><ul class="khl">{khl}</ul></div>
  <div class="stats">
    <span class="stat">👍 Likes: {int(row.get("_likes",0))}</span>
    <span class="stat">💬 Comments: {int(row.get("_comms",0))}</span>
  </div>
</div>""".strip()

    # assemble sections per bank (in banks_list order)
    sections = []
    for bank in banks_list:
        g = d[d[col_bank] == bank]
        if g.empty:
            continue
        top3 = g.sort_values(metric_col, ascending=False).head(3)
        cards = "\n".join(card_html(r) for _, r in top3.iterrows())
        sections.append(f"""
  <div class="bank-title">{_esc(bank)} — Top 3</div>
  <div class="grid">
    {cards if cards else '<div class="card"><div class="post">No posts found.</div></div>'}
  </div>""")

    # final wrapper div (no <head>/<body>)
    return f"""
<div id="top3-by-bank">
  <style>
    #top3-by-bank{{--text:#072447;--muted:#475569;--card:#fff;--border:#e5e7eb;--shadow:0 6px 18px rgba(0,0,0,.06);
      font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:var(--text)}}
    #top3-by-bank .section-title{{font-size:20px;font-weight:700;margin:0 0 12px}}
    #top3-by-bank .bank-title{{font-size:18px;font-weight:700;margin:22px 0 10px}}
    #top3-by-bank .grid{{display:grid;grid-template-columns:1fr;gap:16px}}
    @media(min-width:900px){{#top3-by-bank .grid{{grid-template-columns:1fr 1fr}}}}  /* 2-up desktop */
    #top3-by-bank .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);padding:16px}}
    #top3-by-bank .row{{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 8px}}
    #top3-by-bank .row-right{{margin-left:auto}}
    #top3-by-bank .open-link{{font-weight:600;text-decoration:none}}
    #top3-by-bank .post{{background:#f8fafc;border:1px dashed var(--border);border-radius:10px;padding:12px;margin:10px 0}}
    #top3-by-bank .khl{{margin:6px 0 0;padding-left:18px}}
    #top3-by-bank .khl li{{margin:4px 0;color:var(--muted)}}
    #top3-by-bank .stats{{display:flex;gap:10px;align-items:center;margin-top:6px;flex-wrap:wrap}}
    #top3-by-bank .stat{{font-size:12px;background:#fff;border:1px solid var(--border);padding:6px 10px;border-radius:999px}}
  </style>

  <div class="section-title">Top 3 High-Engaged Reddit Posts — Per Bank</div>
  {''.join(sections) if sections else '<div class="card"><div class="post">No banks found.</div></div>'}
</div>
""".strip()


# In[81]:


html_top3_per_bank = render_top3_per_bank(top3_bank_authored, banks_list, sort_by="likes")


# In[82]:


# ---------- Assemble & write ----------
html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>ReddIt Post Analysis</title>
  {css}
</head>
<body>
  <div class="wrap">
    {header}
    {table_div}
    {chart_img_html}
    {neg}
    {html_top3_per_bank}
  </div>
</body>
</html>"""

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(html_doc)


