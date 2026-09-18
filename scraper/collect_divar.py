from divar import Client
import json
import os
import time
from datetime import datetime


# -----------------------------
# Settings
# -----------------------------
CITY_ID = 1          # Tehran
CATEGORY = "cars"
LIMIT = 500

OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "divar_cars_500.json")


# -----------------------------
# Prepare output directory
# -----------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -----------------------------
# Create Divar client
# -----------------------------
client = Client("car_price_test")


# -----------------------------
# Get car listings
# -----------------------------
print("Starting collection...")
print(f"City ID: {CITY_ID}")
print(f"Category: {CATEGORY}")
print(f"Target: {LIMIT} posts")
print("-" * 60)


posts = client.get_posts(
    place_ids=CITY_ID,
    category=CATEGORY,
    limit=LIMIT
)


all_posts = []


# -----------------------------
# Fetch full posts
# -----------------------------
for i, post in enumerate(posts, start=1):

    print(f"[{i}/{LIMIT}] Getting: {post.token}")

    try:
        full_post = client.get_post(token=post.token)

        record = {
            "token": full_post.token,
            "title": full_post.title,
            "publish_date": str(full_post.publish_date),
            "city": full_post.city.name if full_post.city else None,
            "district": full_post.district,
            "url": full_post.url,
            "description": full_post.description,
            "data": [
                {
                    "title": item.title,
                    "value": item.value
                }
                for item in full_post.data
            ]
        }

        all_posts.append(record)

    except Exception as e:
        print(f"  ERROR: {e}")

    # Small delay to avoid aggressive requests
    time.sleep(0.5)


# -----------------------------
# Save raw data
# -----------------------------
with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        all_posts,
        f,
        ensure_ascii=False,
        indent=2
    )


# -----------------------------
# Summary
# -----------------------------
print("\n" + "=" * 60)
print("COLLECTION FINISHED")
print("=" * 60)

print("Collected:", len(all_posts))
print("Output:", OUTPUT_FILE)
print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))