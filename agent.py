import json
import hashlib
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


SEARCHES = [
    "site:morth.gov.in motor vehicle notification India",
    "site:parivahan.gov.in vehicle rules notification India",
    "\"Central Motor Vehicles Rules\" amendment India",
    "MoRTH new rule commercial vehicle driver India",
    "driving licence new rules India",
    "FASTag toll new rules India",
    "vehicle fitness certificate permit rules India",
    "tractor construction equipment transport rules India",
]

KNOWN_FILE = "known_updates.json"
OUTPUT_FILE = "latest_updates.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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
        "motor vehicle",
        "vehicle",
        "driver",
        "driving licence",
        "driving license",
        "transport",
        "commercial vehicle",
        "truck",
        "bus",
        "taxi",
        "permit",
        "fitness certificate",
        "challan",
        "fine",
        "fastag",
        "toll",
        "road safety",
        "tractor",
        "tipper",
        "dumper",
        "construction equipment",
        "morth",
        "cmvr",
        "motor vehicles act",
    ]

    text = title.lower()
    return any(keyword in text for keyword in keywords)


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are not configured.")
        return False

    url = (
        "https://api.telegram.org/bot"
        + TELEGRAM_BOT_TOKEN
        + "/sendMessage"
    )

    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = response.read().decode("utf-8")
            print("Telegram notification sent.")
            return result
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def main():
    send_telegram_message(
        "✅ ChalakSetu Vehicle Rules Agent is connected successfully!\n\n"
        "Telegram notifications are working."
    )
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

    save_json(
        KNOWN_FILE,
        {"ids": list(known_ids)}
    )

    save_json(
        OUTPUT_FILE,
        {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "new_updates": new_updates,
        },
    )

    print(f"Found {len(new_updates)} new relevant updates")

    for update in new_updates:
        message = (
            "🚨 NEW VEHICLE / TRANSPORT UPDATE\n\n"
            f"📢 {update['title']}\n\n"
            f"📰 Source: {update['source']}\n"
            f"📅 Published: {update['published']}\n\n"
            f"🔗 {update['link']}"
        )

        send_telegram_message(message)


if __name__ == "__main__":
    main()
