import json
from collections import defaultdict, Counter
import sys

sys.stdout.reconfigure(encoding="utf-8")


FILE = "data/raw/divar_cars_500.json"


with open(FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)


# title -> values -> count
fields = defaultdict(Counter)

for post in posts:
    for item in post.get("data", []):
        title = item.get("title")
        value = item.get("value")

        if title:
            fields[title][value] += 1


print("=" * 80)
print("FIELD VALUE INSPECTION")
print("=" * 80)


for title, values in fields.items():

    print("\n" + "-" * 80)
    print(f"FIELD: {title}")
    print("-" * 80)

    print(f"Unique values: {len(values)}")

    for value, count in values.most_common(20):
        print(f"{count:4}  {value}")