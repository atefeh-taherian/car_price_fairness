from divar import Client
import json
import os
import random
import time
from datetime import datetime


CITIES = {
    1: "tehran",
    2: "mashhad",
    3: "isfahan",
    4: "shiraz",
    5: "karaj",
    6: "tabriz",
}

CATEGORY = "cars"
TARGET_PER_CITY = 250

OUTPUT_DIR = "data/raw"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_json(path, records):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )


def collect_city(city_id, city_name):
    output_file = os.path.join(
        OUTPUT_DIR,
        f"divar_{city_name}.json"
    )

    client = Client("car_price_multi_city")

    print("=" * 70)
    print(f"City: {city_name}")
    print(f"City ID: {city_id}")
    print(f"Target: {TARGET_PER_CITY}")
    print("=" * 70)

    posts = client.get_posts(
        place_ids=city_id,
        category=CATEGORY,
        limit=TARGET_PER_CITY
    )

    records = []
    seen_tokens = set()

    for index, post in enumerate(posts, start=1):

        if post.token in seen_tokens:
            continue

        seen_tokens.add(post.token)

        print(
            f"[{index}/{TARGET_PER_CITY}] "
            f"{city_name} | {post.token}"
        )

        success = False

        for attempt in range(3):

            try:
                full_post = client.get_post(
                    token=post.token
                )

                record = {
                    "token": full_post.token,
                    "title": full_post.title,
                    "publish_date": str(
                        full_post.publish_date
                    ),
                    "city": (
                        full_post.city.name
                        if full_post.city
                        else None
                    ),
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

                records.append(record)
                success = True

                print(
                    f"  OK | collected={len(records)}"
                )

                break

            except Exception as error:

                error_text = str(error)

                print(
                    f"  Attempt {attempt + 1}/3 failed: "
                    f"{error_text}"
                )

                if "429" in error_text:
                    wait_seconds = 15 * (attempt + 1)

                    print(
                        f"  Rate limit detected. "
                        f"Waiting {wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)

                else:
                    time.sleep(3)

        if not success:
            print("  SKIPPED")

        sleep_time = random.uniform(1.5, 3.0)
        time.sleep(sleep_time)

        if len(records) >= TARGET_PER_CITY:
            break

    save_json(output_file, records)

    print()
    print(f"Finished city: {city_name}")
    print(f"Collected: {len(records)}")
    print(f"Output: {output_file}")
    print()

    return records


all_city_records = []

for city_id, city_name in CITIES.items():

    try:
        city_records = collect_city(
            city_id,
            city_name
        )

        all_city_records.extend(city_records)

    except Exception as error:

        print(
            f"City collection failed: "
            f"{city_name} | {error}"
        )

    print(
        "Waiting before moving to the next city..."
    )

    time.sleep(
        random.uniform(10, 20)
    )


merged_file = os.path.join(
    OUTPUT_DIR,
    "divar_multi_city_raw.json"
)

save_json(
    merged_file,
    all_city_records
)

print("=" * 70)
print("MULTI-CITY COLLECTION FINISHED")
print("=" * 70)

print(
    f"Total raw records: "
    f"{len(all_city_records)}"
)

print(
    f"Output: {merged_file}"
)

print(
    f"Finished at: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)