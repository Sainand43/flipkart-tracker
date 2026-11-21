import json
import os
import requests
from bs4 import BeautifulSoup

URL = os.environ["PRODUCT_URL"]
TARGET_PRICE = float(os.environ["TARGET_PRICE"])
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def get_price(url: str) -> float:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue
            offers = item.get("offers")
            if isinstance(offers, list):
                offers = offers[0] if offers else None
            if not offers or "price" not in offers:
                continue
            if "InStock" not in offers.get("availability", "InStock"):
                raise RuntimeError("Product is out of stock")
            return float(offers["price"])

    raise RuntimeError("No Product price found in JSON-LD; layout may have changed or you were blocked")


def notify_ntfy(price: float) -> None:
    resp = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=f"Now ₹{price:,.0f} (your target: ₹{TARGET_PRICE:,.0f})".encode("utf-8"),
        headers={
            "Title": "Flipkart price drop!",   # HTTP headers must be plain ASCII, so no ₹ here
            "Click": URL,                      # tapping the notification opens the product page
            "Priority": "high",
            "Tags": "moneybag",                # shows an emoji on the notification
        },
        timeout=10,
    )
    resp.raise_for_status()   # fail loudly if the notification didn't go through


def main():
    price = get_price(URL)
    print(f"Current price: ₹{price:,.0f}")
    if price <= TARGET_PRICE:
        print("Below target, sending notification...")
        notify_ntfy(price)
    else:
        print("Above target, nothing to do.")


if __name__ == "__main__":
    main()