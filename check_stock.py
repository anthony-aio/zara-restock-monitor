import requests
import os
import json
import re
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
PRODUCT_URL = "https://www.zara.com/us/en/regular-fit-henley-shirt-p04090033.html?v1=531603913&v2=2718839"
PRODUCT_NAME = "Zara Regular Fit Henley Shirt"
TARGET_COLOR_ID = "2718839"   # v2 param = color variant
TARGET_SIZE_IDS = []          # Leave empty [] to alert on ANY size, or fill with size IDs like ["5188", "5189"]

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Zara's internal API endpoint (reverse-engineered from their site)
API_URL = (
    "https://www.zara.com/us/en/product/"
    "p04090033/details?sectionName=NEW_IN"
    f"&productColor[0]={TARGET_COLOR_ID}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.zara.com/",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_stock_info():
    """Fetch Zara product details and return list of in-stock sizes."""
    # Use Zara's stock/details API
    api_endpoint = (
        f"https://www.zara.com/us/en/product/p04090033/detail.json"
        f"?v1=531603913&v2={TARGET_COLOR_ID}"
    )
    resp = requests.get(api_endpoint, headers=HEADERS, timeout=15)

    if resp.status_code != 200:
        # Fallback: scrape the HTML page for JSON-LD / next data
        return scrape_html_for_stock()

    data = resp.json()
    return parse_stock_from_json(data)


def scrape_html_for_stock():
    """Scrape the product page HTML and extract stock info from embedded JSON."""
    resp = requests.get(PRODUCT_URL, headers=HEADERS, timeout=20)
    html = resp.text

    # Zara embeds product data in a <script id="__NEXT_DATA__"> tag
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError("Could not find __NEXT_DATA__ in page HTML")

    raw = match.group(1)
    data = json.loads(raw)
    return parse_next_data_for_stock(data)


def parse_stock_from_json(data):
    """Parse Zara API JSON response for stock."""
    in_stock = []
    try:
        colors = data.get("product", {}).get("detail", {}).get("colors", [])
        for color in colors:
            color_id = str(color.get("id", ""))
            if TARGET_COLOR_ID and color_id != TARGET_COLOR_ID:
                continue
            color_name = color.get("name", "Unknown Color")
            sizes = color.get("sizes", [])
            for size in sizes:
                availability = size.get("availability", "")
                size_name = size.get("name", "")
                size_id = str(size.get("id", ""))
                if availability in ("in_stock", "IN_STOCK", "available"):
                    if not TARGET_SIZE_IDS or size_id in TARGET_SIZE_IDS:
                        in_stock.append({"color": color_name, "size": size_name})
    except Exception as e:
        print(f"Warning: JSON parse error: {e}")
    return in_stock


def parse_next_data_for_stock(data):
    """Parse __NEXT_DATA__ blob for stock info."""
    in_stock = []
    try:
        # Walk the nested structure — Zara's NEXT_DATA varies; we search broadly
        text = json.dumps(data)
        # Look for size availability patterns
        size_blocks = re.findall(r'"name"\s*:\s*"([^"]+)"[^}]*?"availability"\s*:\s*"([^"]+)"', text)
        for size_name, avail in size_blocks:
            if avail.lower() in ("in_stock", "available"):
                in_stock.append({"color": "Selected Color", "size": size_name})
    except Exception as e:
        print(f"Warning: NEXT_DATA parse error: {e}")
    return in_stock


def send_discord_alert(in_stock_sizes):
    """Fire a Discord webhook notification."""
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL not set.")
        return

    sizes_text = "\n".join([f"• **{s['size']}** ({s['color']})" for s in in_stock_sizes])

    payload = {
        "username": "Stock Monitor 🛍️",
        "avatar_url": "https://i.imgur.com/4M34hi2.png",
        "embeds": [
            {
                "title": f"🚨 BACK IN STOCK: {PRODUCT_NAME}",
                "url": PRODUCT_URL,
                "description": (
                    f"The item you're watching just came back in stock!\n\n"
                    f"**Available sizes:**\n{sizes_text}\n\n"
                    f"[👉 Buy it now]({PRODUCT_URL})"
                ),
                "color": 0x00FF88,
                "footer": {"text": "Zara Stock Monitor • Act fast — sizes go quickly!"},
            }
        ],
    }

    r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    if r.status_code in (200, 204):
        print("✅ Discord alert sent!")
    else:
        print(f"❌ Discord webhook failed: {r.status_code} {r.text}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Checking stock for: {PRODUCT_NAME}")
    print(f"URL: {PRODUCT_URL}")

    try:
        in_stock = get_stock_info()
    except Exception as e:
        print(f"ERROR fetching stock info: {e}")
        sys.exit(1)

    if in_stock:
        print(f"✅ IN STOCK! Found {len(in_stock)} size(s): {in_stock}")
        send_discord_alert(in_stock)
    else:
        print("❌ Out of stock. No alert sent.")


if __name__ == "__main__":
    main()
