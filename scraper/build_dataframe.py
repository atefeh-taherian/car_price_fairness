import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

OLD_RAW_PATH = BASE_DIR / "data" / "raw" / "divar_cars_500.json"
NEW_RAW_PATH = BASE_DIR / "data" / "raw" / "divar_multi_city_raw.json"

OUTPUT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "divar_cars_expanded.csv"
OUTPUT_JSON = OUTPUT_DIR / "divar_cars_expanded.json"
COLUMN_MAP_PATH = OUTPUT_DIR / "column_mapping.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_source_title(title):
    if title is None:
        return ""

    title = str(title).strip()

    # Normalize Arabic/Persian character variants.
    title = title.replace("\u064a", "\u06cc")
    title = title.replace("\u0643", "\u06a9")

    # Remove zero-width non-joiner and tatweel.
    title = title.replace("\u200c", "")
    title = title.replace("\u0640", "")

    # Normalize spaces.
    title = " ".join(title.split())

    return title


SOURCE_TO_ENGLISH = {
    "\u06a9\u0627\u0631\u06a9\u0631\u062f": "mileage",
    "\u0645\u062f\u0644 (\u0633\u0627\u0644 \u062a\u0648\u0644\u06cc\u062f)": "year_raw",
    "\u0631\u0646\u06af": "color",
    "\u0628\u0631\u0646\u062f \u0648 \u0645\u062f\u0644": "brand_model",
    "\u0645\u0647\u0644\u062a \u0628\u06cc\u0645\u0647\u0654 \u0634\u062e\u0635 \u062b\u0627\u0644\u062b": "third_party_insurance",
    "\u0646\u0648\u0639 \u0633\u0648\u062e\u062a": "fuel_type",
    "\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647": "asking_price_raw",
    "\u0645\u0648\u062a\u0648\u0631": "engine_condition",
    "\u0648\u0636\u0639\u06cc\u062a \u0634\u0627\u0633\u06cc\u200c\u0647\u0627": "chassis_condition",
    "\u0628\u062f\u0646\u0647": "body_condition",
    "\u0646\u0648\u0639 \u0648\u0633\u06cc\u0644\u0647\u0654 \u0646\u0642\u0644\u06cc\u0647": "vehicle_type",
}


# Normalize mapping keys once.
SOURCE_TO_ENGLISH = {
    normalize_source_title(k): v
    for k, v in SOURCE_TO_ENGLISH.items()
}


def expand_data(record):
    result = {}

    # Keep the top-level fields.
    result["token"] = record.get("token")
    result["title"] = record.get("title")
    result["publish_date"] = record.get("publish_date")
    result["city"] = record.get("city")
    result["district"] = record.get("district")
    result["url"] = record.get("url")
    result["description"] = record.get("description")

    # Track original source titles and repeated fields.
    source_titles = {}

    for item in record.get("data", []):
        if not isinstance(item, dict):
            continue

        raw_title = item.get("title")
        value = item.get("value")

        normalized_title = normalize_source_title(raw_title)

        if not normalized_title:
            continue

        source_titles.setdefault(normalized_title, []).append(value)

    for source_title, values in source_titles.items():

        # Special handling for repeated gearbox fields.
        if source_title == normalize_source_title(
            "\u06af\u06cc\u0631\u0628\u06a9\u0633"
        ):
            if len(values) >= 1:
                result["Gearbox_type"] = values[0]

            if len(values) >= 2:
                result["Gearbox_condition"] = values[1]

            # Preserve any unexpected additional values.
            if len(values) > 2:
                for index, extra_value in enumerate(values[2:], start=3):
                    result[f"Gearbox_extra_{index}"] = extra_value

            continue

        english_name = SOURCE_TO_ENGLISH.get(source_title)

        if english_name is None:
            continue

        # For now, preserve the first value.
        # Repeated non-gearbox fields are handled separately later
        # if the raw data shows that they carry different meanings.
        result[english_name] = values[0]

    return result


def main():
    old_records = load_json(OLD_RAW_PATH)
    new_records = load_json(NEW_RAW_PATH)

    combined_records = old_records + new_records

    print(f"Old records: {len(old_records)}")
    print(f"New records: {len(new_records)}")
    print(f"Combined records: {len(combined_records)}")

    expanded_rows = [
        expand_data(record)
        for record in combined_records
    ]

    df = pd.DataFrame(expanded_rows)

    print("\nDataFrame shape:")
    print(df.shape)

    print("\nColumns:")
    for column in df.columns:
        print(column)

    print("\nGearbox columns:")
    gearbox_columns = [
        column
        for column in df.columns
        if "Gearbox" in column
    ]

    for column in gearbox_columns:
        print(column)

    # Save UTF-8 CSV for inspection.
    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # Save JSON version.
    df.to_json(
        OUTPUT_JSON,
        orient="records",
        force_ascii=False,
        indent=2
    )

    # Save the source-title mapping.
    with open(COLUMN_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(
            SOURCE_TO_ENGLISH,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\nSaved files:")
    print(OUTPUT_CSV)
    print(OUTPUT_JSON)
    print(COLUMN_MAP_PATH)


if __name__ == "__main__":
    main()