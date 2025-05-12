
from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import time
import os

app = Flask(__name__)

with open("buff163.txt", encoding="utf-8") as f:
    skin_map = json.load(f)

find_id = {}
with open("youpin898.txt", encoding="utf-8") as f:
    for line in f:
        try:
            name = line.split(": ")[0][3:-1]
            ID = line.split(": ")[1][:-2]
            find_id[name] = ID
        except:
            continue

def get_youpin_price(name):
    ID = find_id.get(name)
    if not ID:
        return None
    payload = json.dumps({
        "listSortType": 1,
        "listType": 10,
        "pageIndex": 1,
        "pageSize": 10,
        "sortType": 1,
        "templateId": ID
    })
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/json'
    }
    time.sleep(1)
    r = requests.post("https://api.youpin898.com/api/homepage/es/commodity/GetCsGoPagedList", headers=headers, data=payload, timeout=10)
    return float(r.json()["Data"]["TemplateInfo"]["MinPrice"])

@app.route("/api/price")
def get_price_data():
    name = request.args.get("name")
    goods_id = skin_map.get(name)
    if not goods_id:
        return jsonify({"error": f"Скин '{name}' не найден"}), 404

    results = {}

    try:
        r = requests.get("https://buff.163.com/api/market/goods/sell_order", params={
            "game": "csgo", "goods_id": goods_id, "page_num": 1, "sort_by": "default"
        }, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        data = r.json()
        results["buff"] = float(data["data"]["items"][0]["price"]) if data["code"] == "OK" and data["data"]["items"] else None
    except:
        results["buff"] = None

    try:
        r = requests.get(f"https://market.csgo.com/api/v2/search-item-by-hash-name?key=k4188s3VOAqUkv9ZGsWTi5760pO9s45&hash_name={name}", timeout=10)
        data = r.json()
        results["leg1t"] = float(data["data"][0]["price"]) if "data" in data else None
    except:
        results["leg1t"] = None

    try:
        results["youpin"] = get_youpin_price(name)
    except:
        results["youpin"] = None

    def profit(from_val, to_val, mult=12):
        if from_val is None or to_val is None:
            return None
        from_rub = from_val * mult
        to_rub = to_val * 0.95 / 100
        diff = to_rub - from_rub
        percent = (diff / from_rub) * 100 if from_rub != 0 else 0
        return {"rub": diff, "percent": percent}

    results["profit_youpin"] = profit(results.get("youpin"), results.get("leg1t"))
    results["profit_buff"] = profit(results.get("buff"), results.get("leg1t"))

    return jsonify(results)

@app.route("/api/skins")
def get_skin_names():
    return jsonify(sorted(list(skin_map.keys()), key=str.lower))

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
