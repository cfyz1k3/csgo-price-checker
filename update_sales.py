import requests
import json

URL = "https://market.csgo.com/api/v2/prices/class_instance/RUB.json"
OUTPUT_FILE = "sales.json"

def update_sales():
    try:
        response = requests.get(URL, timeout=30)
        r = response.json()
        all_sales = {}
        for key, item in r.get("items", {}).items():
            name = item.get("market_hash_name")
            popularity_7d = item.get("popularity_7d") or 0
            if name:
                all_sales[name] = all_sales.get(name, 0) + int(popularity_7d)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_sales, f, ensure_ascii=False)
        print(f"✅ sales.json обновлён. Записано: {len(all_sales)} скинов")
    except Exception as e:
        print("❌ Ошибка при обновлении sales:", str(e))

if __name__ == "__main__":
    update_sales()