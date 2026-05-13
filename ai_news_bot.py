import feedparser
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import requests
import textwrap
import os
import time
import re
import random
import subprocess

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not CHAT_ID:
    raise ValueError("CHAT_ID missing")

print("✅ ENV LOADED")

# =========================================================
# GROQ CLIENT
# =========================================================

groq_client = Groq(api_key=GROQ_API_KEY)
TEXT_MODEL   = "llama-3.1-8b-instant"

# =========================================================
# LOAD FONTS ONCE AT STARTUP
# =========================================================

def load_hindi_font(size, bold=False):
    """
    Dynamically finds installed Hindi fonts using fc-list.
    Loads once at startup — not on every poster call.
    """

    try:

        result = subprocess.run(
            ['fc-list', ':lang=hi'],
            capture_output=True,
            text=True
        )

        paths = [
            line.split(':')[0].strip()
            for line in result.stdout.strip().split('\n')
            if line.strip()
        ]

        print(f"  📋 Found {len(paths)} Hindi fonts")

        # Try bold fonts first if bold=True
        if bold:
            for path in paths:
                if ('Bold' in path or 'bold' in path) and (path.endswith('.ttf') or path.endswith('.otf')):
                    try:
                        font = ImageFont.truetype(path, size)
                        print(f"  ✅ Bold font: {path}")
                        return font
                    except:
                        continue

        # Try any Hindi font
        for path in paths:
            if path.endswith('.ttf') or path.endswith('.otf'):
                try:
                    font = ImageFont.truetype(path, size)
                    print(f"  ✅ Font: {path}")
                    return font
                except:
                    continue

    except Exception as e:
        print(f"  ⚠️ fc-list error: {e}")

    # Hard fallback paths
    fallback_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.otf",
        "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.otf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in fallback_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                print(f"  ✅ Fallback font: {path}")
                return font
            except:
                continue

    print("  ❌ No font found — using PIL default")
    return ImageFont.load_default()


# ── Load fonts ONCE here at startup ──
print("\n========== LOADING FONTS ==========")
FONT_HEADLINE = load_hindi_font(46, bold=True)
FONT_ARTICLE  = load_hindi_font(32, bold=True)
print("✅ FONTS LOADED\n")

# =========================================================
# SHORT LINK FUNCTION
# =========================================================

def shorten_url(long_url):

    try:

        api_url  = f"https://is.gd/create.php?format=simple&url={long_url}"
        response = requests.get(api_url, timeout=10)

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

            files = {"photo": photo}

            response = requests.post(
                url,
                data=payload,
                files=files,
                timeout=60
            )

        print("\n========== TELEGRAM PHOTO RESPONSE ==========")
        print(response.text)

    except Exception as e:

        print("\n========== TELEGRAM PHOTO ERROR ==========")
        print("Error Type:", type(e))
        print("Full Error:", str(e))

        import traceback
        traceback.print_exc()

# =========================================================
# TELEGRAM MESSAGE FUNCTION
# =========================================================

def send_telegram_message(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        payload = {
            "chat_id":    CHAT_ID,
            "text":       text,
            "parse_mode": "HTML"
        }

        response = requests.post(url, data=payload, timeout=60)

        print("\n========== TELEGRAM MESSAGE RESPONSE ==========")
        print(response.text)

    except Exception as e:

        print("\n========== TELEGRAM MESSAGE ERROR ==========")
        print("Error Type:", type(e))
        print("Full Error:", str(e))

        import traceback
        traceback.print_exc()

# =========================================================
# CREATE POSTER FROM TEMPLATE
# =========================================================

def create_news_poster(headline, article):

    try:

        # --- Pick random template ---
        template_folder = "templates"

        templates = [
            f for f in os.listdir(template_folder)
            if f.lower().endswith(".png") or f.lower().endswith(".jpg")
        ]

        if not templates:
            print("❌ No templates found in /templates folder")
            return None

        chosen        = random.choice(templates)
        template_path = os.path.join(template_folder, chosen)

        print(f"  🎨 Using template: {chosen}")

        # --- Open template ---
        img  = Image.open(template_path).convert("RGBA")
        img  = img.resize((1080, 1350))
        draw = ImageDraw.Draw(img)

        # ── TOP BOX: Headline ──
        # Area: y=55 to y=260, x=30 to x=1050
        # Each line centered (expands from middle)

        box_top    = 55
        box_bottom = 260
        box_left   = 30
        box_right  = 1050

        wrapped_headline = textwrap.fill(headline, width=28)
        lines            = wrapped_headline.split("\n")
        line_height      = 52
        total_h          = len(lines) * line_height
        start_y          = box_top + (box_bottom - box_top - total_h) // 2

        for line in lines:

            if start_y > box_bottom - 10:
                break

            bbox       = draw.textbbox((0, 0), line, font=FONT_HEADLINE)
            text_width = bbox[2] - bbox[0]
            x          = (box_left + box_right - text_width) // 2

            # subtle shadow
            draw.text((x + 2, start_y + 2), line, font=FONT_HEADLINE, fill=(180, 180, 180))
            # main text
            draw.text((x,     start_y),     line, font=FONT_HEADLINE, fill=(15,  15,  15))

            start_y += line_height

        # ── ARTICLE BOX ──
        # Area: y=545 to y=1140, x=60 to x=1020

        article_clean   = article[:1500]
        wrapped_article = textwrap.fill(article_clean, width=36)

        y_art = 545

        for line in wrapped_article.split("\n"):

            if y_art > 1130:
                draw.text((60, y_art), "...", font=FONT_ARTICLE, fill=(30, 30, 30))
                break

            draw.text((60, y_art), line, font=FONT_ARTICLE, fill=(20, 20, 20))
            y_art += 48

        # --- Save ---
        final_path = "final_news_post.png"
        img.convert("RGB").save(final_path, quality=95)

        print("  ✅ Poster created")
        return final_path

    except Exception as e:

        print("\nPOSTER ERROR:", e)

        import traceback
        traceback.print_exc()

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
                "link":     entry.link
            })

    except Exception as e:

        print("\nRSS ERROR:", e)

# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(all_news)

if df.empty:
    print("No news found")
    exit()

df.drop_duplicates(subset=["headline"], inplace=True)

print("\nTOTAL NEWS:", len(df))

# =========================================================
# AI TEXT GENERATION WITH RETRY
# =========================================================

def generate_ai_text(prompt, retries=3, wait=5):

    for attempt in range(1, retries + 1):

        try:

            print(f"  🤖 AI attempt {attempt}/{retries}...")

            response = groq_client.chat.completions.create(

                model=TEXT_MODEL,

                messages=[
                    {
                        "role":    "system",
                        "content": "You are an expert viral Hindi social media writer for Facebook. Always write articles in pure Hindi only."
                    },
                    {
                        "role":    "user",
                        "content": prompt
                    }
                ],

                max_tokens=1024,
                temperature=0.7
            )

            result = response.choices[0].message.content

            if not result or not result.strip():
                raise ValueError("Empty response from model")

            return result

        except Exception as e:

            print(f"  ❌ Error: {type(e)} — {e}")

            if attempt < retries:
                print(f"  ⏳ Waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                print("  ❌ All retries exhausted.")
                return None

    return None

# =========================================================
# RESULTS
# =========================================================

results = []

# =========================================================
# AI ANALYSIS LOOP
# =========================================================

for index, row in df.iterrows():

    headline = row["headline"]
    category = row["category"]
    link     = row["link"]

    print("\n" + "=" * 80)
    print("HEADLINE:", headline)
    print("=" * 80)

    prompt = f"""
You are an expert viral Hindi social media writer for Facebook.

NEWS HEADLINE (in English):
{headline}

Your task:
1. Understand this headline deeply
2. Write a full emotional viral Facebook post in HINDI ONLY
3. The article must be 200-300 words minimum
4. Make it human, emotional, engaging

Return STRICTLY in this exact format and nothing else:

Emotion Score: number/10
Virality Score: number/10
Political Toxicity: number/10

HOOK:
(one strong emotional Hindi hook line)

FACEBOOK ARTICLE:
(write full 200-300 word emotional Hindi article here.
Pure Hindi only. No English words except proper nouns.
Start with a strong emotional opening.
Use short punchy paragraphs.
Add questions to engage readers.
End with a call to action.)

HASHTAGS:
#hindi #hashtags #only
"""

    ai_result = generate_ai_text(prompt)

    if not ai_result:
        print("⏭️  SKIPPING — no AI response")
        continue

    try:

        # --- Extract Scores ---
        emotion_match  = re.search(r"Emotion Score:\s*(\d+)",      ai_result)
        virality_match = re.search(r"Virality Score:\s*(\d+)",     ai_result)
        toxicity_match = re.search(r"Political Toxicity:\s*(\d+)", ai_result)

        emotion_score  = int(emotion_match.group(1))  if emotion_match  else 0
        virality_score = int(virality_match.group(1)) if virality_match else 0
        toxicity_score = int(toxicity_match.group(1)) if toxicity_match else 0

        # --- Final Score ---
        final_score = round(
            virality_score * 0.5 +
            emotion_score  * 0.35 -
            toxicity_score * 0.15,
            2
        )

        print("\n========== SCORES ==========")
        print("Emotion:",     emotion_score)
        print("Virality:",    virality_score)
        print("Toxicity:",    toxicity_score)
        print("Final Score:", final_score)

        # --- Extract ONLY Facebook Article (no scores, no hook) ---
        article_match = re.search(
            r"FACEBOOK ARTICLE:\s*(.*?)\s*HASHTAGS:",
            ai_result,
            re.DOTALL
        )

        article_text = (
            article_match.group(1).strip()
            if article_match else ""
        )

        # --- Extract Hashtags ---
        hashtag_match = re.search(
            r"HASHTAGS:\s*(.*?)$",
            ai_result,
            re.DOTALL
        )

        hashtags = (
            hashtag_match.group(1).strip()
            if hashtag_match else ""
        )

        # --- Skip if no article extracted ---
        if not article_text:
            print("⚠️  Article extraction failed — skipping")
            continue

        # --- Save if score good ---
        if final_score >= 3:

            results.append({
                "category":       category,
                "headline":       headline,
                "link":           link,
                "emotion_score":  emotion_score,
                "virality_score": virality_score,
                "toxicity_score": toxicity_score,
                "final_score":    final_score,
                "article":        article_text,
                "hashtags":       hashtags
            })

            print("✅ SAVED")

        else:
            print("❌ REJECTED (low score)")

    except Exception as e:

        print("\n========== PARSE ERROR ==========")
        print("Headline:",   headline)
        print("Error Type:", type(e))
        print("Full Error:", str(e))

        import traceback
        traceback.print_exc()

        continue

    time.sleep(2)

# =========================================================
# RESULTS DATAFRAME
# =========================================================

results_df = pd.DataFrame(results)

if results_df.empty:
    print("\n❌ NO VIRAL NEWS FOUND")
    exit()

results_df = results_df.sort_values(by="final_score", ascending=False)
results_df = results_df.head(5)
results_df.to_csv("viral_news_results.csv", index=False)

# =========================================================
# GENERATE AND SEND POSTS
# =========================================================

print("\n========== GENERATING POSTS ==========\n")

for i, row in results_df.iterrows():

    print(f"\nGenerating Post #{i+1}")

    short_link = shorten_url(row['link'])

    # --- Generate poster from template ---
    final_poster = create_news_poster(
        row['headline'],
        row['article']
    )

    if not final_poster:
        continue

    # --- Send photo with minimal caption ---
    caption = f"🔥 {row['category']} | 🔗 {short_link}"

    send_telegram_photo(final_poster, caption)

    time.sleep(2)

    # --- Send full Hindi FB article as separate message ---
    full_message = f"""📰 <b>{row['headline']}</b>

{row['article']}

{row['hashtags']}

🔗 {short_link}

<b>— Karan Patel Kushinagar</b>
<i>सच्ची खबर, सबसे पहले</i>"""

    send_telegram_message(full_message)

    print(f"✅ SENT #{i+1}")

    time.sleep(5)

print("\n✅ ALL POSTS COMPLETED")

print("\n✅ ALL POSTS COMPLETED")

