```python
import requests
import os
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────

PRODUCT_URL = "https://www.zara.com/us/en/regular-fit-henley-shirt-p04090033.html?v1=531603913&v2=2718839"

PRODUCT_NAME = "Zara Regular Fit Henley Shirt"

TARGET_COLOR_ID = "2718839"

# Leave empty [] for ANY size
# Replace later with Medium size ID once logs show it
# Example:
# TARGET_SIZE_IDS = ["5188"]

TARGET_SIZE_IDS = []

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": PRODUCT_URL,
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

      - name: Show current file
        run: cat check_stock.py

def get_stock_info():
    """Fetch Zara product details and return list of in-stock sizes."""

    resp = requests.get(API_URL, headers=HEADERS, timeout=20)

    print("Status code:", resp.status_code)
    print("Response preview:", resp.text[:500])

    if resp.status_code != 200:
        raise ValueError(
            f"Zara API request failed with status {resp.status_code}"
        )

    data = resp.json()

    return parse_stock_from_json(data)


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

                # PRINT SIZE IDS
                print(
                    f"SIZE NAME: {size_name} | "
                    f"SIZE ID: {size_id} | "
                    f"AVAILABILITY: {availability}"
                )

                if availability.lower() in (
                    "in_stock",
                    "available"
                ):

                    if (
                        not TARGET_SIZE_IDS
                        or size_id in TARGET_SIZE_IDS
                    ):

                        in_stock.append({
                            "color": color_name,
                            "size": size_name,
                        })

    except Exception as e:
        print(f"JSON parse error: {e}")

    return in_stock


def send_discord_alert(in_stock_sizes):
    """Send Discord webhook notification."""

    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL not set.")
        return

    sizes_text = "\n".join([
        f"• **{s['size']}** ({s['color']})"
        for s in in_stock_sizes
    ])

    payload = {
        "username": "Stock Monitor 🛍️",
        "embeds": [
            {
                "title": f"🚨 BACK IN STOCK: {PRODUCT_NAME}",
                "url": PRODUCT_URL,
                "description": (
                    f"**Available sizes:**\n"
                    f"{sizes_text}\n\n"
                    f"[👉 Buy it now]({PRODUCT_URL})"
                ),
                "color": 0x00FF88,
            }
        ],
    }

    r = requests.post(
        DISCORD_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

    if r.status_code in (200, 204):
        print("✅ Discord alert sent!")

    else:
        print(
            f"❌ Discord webhook failed: "
            f"{r.status_code} {r.text}"
        )


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

        print(
            f"✅ IN STOCK! "
            f"Found {len(in_stock)} size(s): {in_stock}"
        )

        send_discord_alert(in_stock)

    else:
        print("❌ Out of stock. No alert sent.")


if __name__ == "__main__":
    main()
```
