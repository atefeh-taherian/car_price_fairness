import json
from collections import Counter
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open(
    "data/raw/divar_cars_500.json",
    "r",
    encoding="utf-8"
) as f:
    posts = json.load(f)


values = Counter()

for post in posts:
    for item in post.get("data", []):
        if item.get("title") == "گیربکس":
            values[item.get("value")] += 1


print("=" * 60)
print("ALL GEARBOX VALUES")
print("=" * 60)

for value, count in values.most_common():
    print(f"{count:3}  {value}")