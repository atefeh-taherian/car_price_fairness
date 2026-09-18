import json

with open(
    "data/raw/divar_test_5.json",
    "r",
    encoding="utf-8"
) as f:
    posts = json.load(f)

print("Number of posts:", len(posts))

for i, post in enumerate(posts, start=1):

    print("\n" + "=" * 70)
    print(f"POST {i}")
    print("=" * 70)

    print("Token:", post["token"])
    print("Title:", post["title"])
    print("Publish date:", post["publish_date"])
    print("City:", post["city"])
    print("District:", post["district"])

    print("\nDATA FIELDS:")

    for item in post["data"]:
        print(f"  {item['title']}  =>  {item['value']}")