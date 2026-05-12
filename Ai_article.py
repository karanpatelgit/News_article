import feedparser
import pandas as pd
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import requests
import textwrap
import os
import time
import re

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN missing")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not CHAT_ID:
    raise ValueError("CHAT_ID missing")

print("✅ ENV LOADED")

# =========================================================
# HUGGINGFACE CLIENT
# =========================================================

client = InferenceClient(
    token=HF_TOKEN
)

TEXT_MODEL = "google/flan-t5-large"
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"

# =========================================================
# SHORT LINK FUNCTION
# =========================================================

def shorten_url(long_url):

    try:

        api_url = (
            f"https://is.gd/create.php?format=simple&url={long_url}"
        )

        response = requests.get(
            api_url,
            timeout=10
        )

        if response.status_code == 200:
            return response.text.strip()

        return long_url

    except Exception as e:

        print("SHORT LINK ERROR:", e)

        return long_url

# =========================================================
# TELEGRAM PHOTO FUNCTION
# =========================================================

def send_telegram_photo(photo_path, caption=""):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    try:

        with open(photo_path, "rb") as photo:

            payload = {
                "chat_id": CHAT_ID,
                "caption": caption[:1000]
            }

            files = {
                "photo": photo
            }

            response = requests.post(
                url,
                data=payload,
                files=files,
                timeout=60
            )

        print("\n========== TELEGRAM RESPONSE ==========")
        print(response.text)

    except Exception as e:

        print("\n========== TELEGRAM ERROR ==========")
        print("Error Type:", type(e))
        print("Full Error:", str(e))

        import traceback
        traceback.print_exc()

# =========================================================
# AI IMAGE GENERATION
# =========================================================

def generate_ai_image(headline):

    API_URL = (
        f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}"
    )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    prompt = f"""
cinematic Indian news scene,
viral social media poster,
dramatic lighting,
emotional atmosphere,
realistic,
ultra detailed,
4k,
news thumbnail style

Headline:
{headline}
"""

    try:

        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": prompt
            },
            timeout=120
        )

        if response.status_code != 200:

            print("\nIMAGE API ERROR:")
            print(response.text)

            return None

        image_path = "generated_news.png"

        with open(image_path, "wb") as f:
            f.write(response.content)

        return image_path

    except Exception as e:

        print("\n========== IMAGE GENERATION ERROR ==========")
        print("Error Type:", type(e))
        print("Error Details:", str(e))

        import traceback
        traceback.print_exc()

        return None

# =========================================================
# CREATE SOCIAL MEDIA POSTER
# =========================================================

def create_news_poster(image_path, headline, article):

    try:

        img = Image.open(image_path).convert("RGB")

        img = img.resize((1080, 1350))

        overlay = Image.new(
            'RGBA',
            img.size,
            (0, 0, 0, 120)
        )

        img = Image.alpha_composite(
            img.convert('RGBA'),
            overlay
        )

        draw = ImageDraw.Draw(img)

        try:

            title_font = ImageFont.truetype(
                "arial.ttf",
                52
            )

            article_font = ImageFont.truetype(
                "arial.ttf",
                34
            )

        except:

            title_font = ImageFont.load_default()
            article_font = ImageFont.load_default()

        wrapped_headline = textwrap.fill(
            headline,
            width=28
        )

        draw.text(
            (60, 80),
            wrapped_headline,
            font=title_font,
            fill="white"
        )

        article = article[:700]

        wrapped_article = textwrap.fill(
            article,
            width=38
        )

        draw.text(
            (60, 350),
            wrapped_article,
            font=article_font,
            fill="white"
        )

        draw.text(
            (60, 1240),
            "AI Viral News",
            font=article_font,
            fill="yellow"
        )

        final_path = "final_news_post.png"

        img.convert("RGB").save(final_path)

        return final_path

    except Exception as e:

        print("\nPOSTER ERROR:")
        print(e)

        return None

# =========================================================
# RSS FEEDS
# =========================================================

RSS_FEEDS = {

    "India":
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",

    "Technology":
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en",

    "World":
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",

    "Business":
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en"
}

# =========================================================
# FETCH NEWS
# =========================================================

all_news = []

print("\n========== FETCHING NEWS ==========\n")

for category, url in RSS_FEEDS.items():

    print(f"Fetching: {category}")

    try:

        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            all_news.append({

                "category": category,

                "headline": entry.title,

                "link": entry.link
            })

    except Exception as e:

        print("\nRSS ERROR:")
        print(e)

# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(all_news)

if df.empty:

    print("No news found")
    exit()

df.drop_duplicates(
    subset=["headline"],
    inplace=True
)

print("\nTOTAL NEWS:", len(df))

# =========================================================
# RESULTS
# =========================================================

results = []

# =========================================================
# AI ANALYSIS
# =========================================================

for index, row in df.iterrows():

    headline = row["headline"]
    category = row["category"]
    link = row["link"]

    print("\n" + "=" * 80)
    print("HEADLINE:", headline)
    print("=" * 80)

    prompt = f"""
You are an expert viral Hindi social media writer.

Analyze this news headline.

HEADLINE:
{headline}

Return STRICTLY in this format:

Emotion Score: number/10
Virality Score: number/10
Political Toxicity: number/10

HOOK:
(one emotional hook)

FACEBOOK ARTICLE:
(write emotional Hindi article.
Make it human-like.
Make it deeply engaging.
Make it social-media-ready.)

HASHTAGS:
(viral hashtags only)
"""


    try:

        response = client.text_generation(

            prompt=prompt,

            model=TEXT_MODEL,

            max_new_tokens=300
        )

        ai_result = str(response)

        if not ai_result.strip():

            print("EMPTY AI RESPONSE")

            continue

        print("\n========== AI RESPONSE ==========\n")
        print(ai_result)

        # =====================================================
        # EXTRACT SCORES
        # =====================================================

        emotion_match = re.search(
            r"Emotion Score:\s*(\d+)",
            ai_result
        )

        virality_match = re.search(
            r"Virality Score:\s*(\d+)",
            ai_result
        )

        toxicity_match = re.search(
            r"Political Toxicity:\s*(\d+)",
            ai_result
        )

        emotion_score = int(
            emotion_match.group(1)
        ) if emotion_match else 0

        virality_score = int(
            virality_match.group(1)
        ) if virality_match else 0

        toxicity_score = int(
            toxicity_match.group(1)
        ) if toxicity_match else 0

        # =====================================================
        # FINAL SCORE
        # =====================================================

        final_score = (
            virality_score * 0.5 +
            emotion_score * 0.35 -
            toxicity_score * 0.15
        )

        final_score = round(final_score, 2)

        print("\n========== SCORES ==========")

        print("Emotion:", emotion_score)
        print("Virality:", virality_score)
        print("Toxicity:", toxicity_score)
        print("Final Score:", final_score)

        # =====================================================
        # ARTICLE EXTRACTION
        # =====================================================

        article_match = re.search(
            r"FACEBOOK ARTICLE:(.*?)(HASHTAGS:|$)",
            ai_result,
            re.DOTALL
        )

        article_text = (
            article_match.group(1).strip()
            if article_match else ai_result[:700]
        )

        # =====================================================
        # SAVE RESULTS
        # =====================================================

        if final_score >= 3:

            results.append({

                "category": category,

                "headline": headline,

                "link": link,

                "emotion_score": emotion_score,

                "virality_score": virality_score,

                "toxicity_score": toxicity_score,

                "final_score": final_score,

                "article": article_text
            })

            print("✅ SAVED")

        else:

            print("❌ REJECTED")

        time.sleep(2)

    except Exception as e:

        print("\n========== AI ERROR ==========")

        print("Headline:", headline)

        print("Error Type:", type(e))

        print("Full Error:", str(e))

        import traceback

        traceback.print_exc()

        time.sleep(5)

        continue

# =========================================================
# RESULTS DATAFRAME
# =========================================================

results_df = pd.DataFrame(results)

if results_df.empty:

    print("\n❌ NO VIRAL NEWS FOUND")
    exit()

results_df = results_df.sort_values(
    by="final_score",
    ascending=False
)

results_df = results_df.head(5)

results_df.to_csv(
    "viral_news_results.csv",
    index=False
)

# =========================================================
# GENERATE POSTS
# =========================================================

print("\n========== GENERATING POSTS ==========\n")

for i, row in results_df.iterrows():

    print(f"\nGenerating Post #{i+1}")

    short_link = shorten_url(
        row['link']
    )

    image_path = generate_ai_image(
        row['headline']
    )

    if not image_path:
        continue

    final_poster = create_news_poster(
        image_path,
        row['headline'],
        row['article']
    )

    if not final_poster:
        continue

    caption = f"""
🔥 VIRAL NEWS

📈 Score: {row['final_score']}

🔗 {short_link}
"""

    send_telegram_photo(
        final_poster,
        caption
    )

    print(f"✅ SENT #{i+1}")

    time.sleep(5)

print("\n✅ ALL POSTS COMPLETED")
