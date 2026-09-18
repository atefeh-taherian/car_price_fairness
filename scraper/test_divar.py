from divar import Client
import json

client = Client("car_price_test")

posts = client.get_posts(
    place_ids=1,
    category="cars",
    limit=5
)

all_posts = []

for i, post in enumerate(posts, start=1):
    print(f"Getting post {i}: {post.token}")

    full_post = client.get_post(token=post.token)

    record = {
        "token": full_post.token,
        "title": full_post.title,
        "publish_date": str(full_post.publish_date),
        "city": full_post.city.name,
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

with open(
    "data/raw/divar_test_5.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        all_posts,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"\nSaved {len(all_posts)} posts.")