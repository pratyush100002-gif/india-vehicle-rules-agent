import json
import hashlib
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Google News RSS searches for discovering possible updates.
# Important: discovered items should be verified against official sources.
SEARCHES = [
    "site:morth.nic.in OR site:morth.gov.in new motor vehicle rules India",
    "\"Central Motor Vehicles Rules\" amendment India",
    "MoRTH notification commercial vehicle driver India",
    "driving licence transport vehicle new rules India",
    "FASTag toll new rules India",
    "vehicle fitness certificate permit rules India",
    "tractor construction equipment transport rules India",
]

KNOWN_FILE = "known_updates.json"
OUTPUT_FILE = "latest_updates.json"


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def google_news_rss(query):
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        source = item.findtext("source", "").strip()

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "published": pub_date,
                "source": source,
            })

    return items


def is_relevant(title):
    keywords = [
        "motor vehicle", "vehicle", "driver", "driving licence",
        "driving license", "transport", "commercial vehicle",
        "truck", "bus", "taxi", "permit", "fitness certificate",
        "challan", "fine", "fastag", "toll", "road safety",
        "tractor", "tipper", "dumper", "construction equipment",
        "morth", "cmvr", "motor vehicles act"
    ]

    text = title.lower()
    return any(keyword in text for keyword in keywords)


def main():
    known = load_json(KNOWN_FILE, {"ids": []})
    known_ids = set(known.get("ids", []))

    new_updates = []

    for query in SEARCHES:
        try:
            items = google_news_rss(query)

            for item in items:
                if not is_relevant(item["title"]):
                    continue

                unique_text = item["title"] + item["link"]
                item_id = hashlib.sha256(
                    unique_text.encode("utf-8")
                ).hexdigest()

                if item_id in known_ids:
                    continue

                known_ids.add(item_id)

                item["id"] = item_id
                item["found_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                new_updates.append(item)

        except Exception as e:
            print(f"Search failed: {query} -> {e}")

    save_json(KNOWN_FILE, {"ids": list(known_ids)})

    save_json(OUTPUT_FILE, {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "new_updates": new_updates
    })

    print(f"Found {len(new_updates)} new relevant updates")

    for update in new_updates:
        print("- " + update["title"])


if __name__ == "__main__":
    main()
