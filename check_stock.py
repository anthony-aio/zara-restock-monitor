import requests
import os
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────

PRODUCT_URL = "https://www.zara.com/us/en/regular-fit-henley-shirt-p04090033.html?v1=531603913&v2=2718839"

PRODUCT_NAME = "Zara Regular Fit Henley Shirt"

# Leave empty for now
# Later we can filter Medium specifically
TARGET_SKUS = []

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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

def get_stock_info():
    """Fetch Zara availability data."""

    availability_url = (
        "https://www.zara.com/us/en/product/"
        "531603913/availability"
    )

    resp = requests.get(
        availability_url,
        headers=HEADERS,
        timeout=20
    )

    print("Status code:", resp.status_code)

    print("Response preview:", resp.text[:1000])

    if resp.status_code != 200:
        raise ValueError(
            f"Availability request failed: {resp.status_code}"
        )

    data = resp.json()

    in_stock = []

    for item in data.get("skusAvailability", []):

        sku = str(item.get("sku"))

        availability = item.get("availability", "")

        print(
            f"SKU: {sku} | "
            f"AVAILABILITY: {availability}"
        )

        if availability == "in_stock":

            if not TARGET_SKUS or sku in TARGET_SKUS:

                in_stock.append({
                    "color": "Selected Color",
                    "size": f"SKU {sku}"
                })

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
            f"Found {len(in_stock)} matching SKU(s): "
            f"{in_stock}"
        )

        send_discord_alert(in_stock)

    else:

        print("❌ Out of stock. No alert sent.")


if __name__ == "__main__":
    main()
