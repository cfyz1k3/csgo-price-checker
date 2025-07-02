from flask import Flask, request, jsonify, send_from_directory, session, redirect
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

with open("buff163.txt", encoding="utf-8") as f:
    skin_map = json.load(f)

executor = ThreadPoolExecutor(max_workers=5)

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

    buff_enabled = request.args.get("buff", "1") == "1"

    results = {"buff_enabled": buff_enabled}

    def fetch_buff():
        try:
            r = requests.get("https://buff.163.com/api/market/goods/sell_order", params={
                "game": "csgo", "goods_id": goods_id, "page_num": 1, "sort_by": "default"
            }, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            data = r.json()
            if data["code"] == "OK" and data["data"]["items"]:
                item = data["data"]["items"][0]
                return float(item["price"]), item["asset_info"]["info"]["icon_url"]
            else:
                return None, None
        except:
            return None, None

    def fetch_leg1t():
        try:
            r = requests.get(f"https://market.csgo.com/api/v2/search-item-by-hash-name?key=v2866i5cp2ZmX6M12yJISnRdRuNbZ40&hash_name={name}", timeout=10)
            data = r.json()
            return float(data["data"][0]["price"]) if "data" in data else None
        except:
            return None

    def fetch_youpin():
        try:
            return get_youpin_price(name)
        except:
            return None

    futures = {}

    if buff_enabled:
        futures["buff"] = executor.submit(fetch_buff)
    else:
        results["buff"] = None
        results["icon"] = None

    futures["leg1t"] = executor.submit(fetch_leg1t)
    futures["youpin"] = executor.submit(fetch_youpin)

    if buff_enabled:
        buff_price, buff_icon = futures["buff"].result()
        results["buff"] = buff_price
        results["icon"] = buff_icon

    leg1t_price = futures["leg1t"].result()
    youpin_price = futures["youpin"].result()

    results["leg1t"] = leg1t_price
    youpinID = find_id.get(name)
    results["youpinID"] = youpinID
    results["youpin"] = youpin_price

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

@app.route("/api/youpin_names")
def youpin_skin_names():
    return jsonify(list(find_id.keys()))

@app.route("/api/sales")
def get_sales():
    try:
        with open("sales.json", "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": f"Не удалось прочитать sales.json: {str(e)}"}), 500

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/potok.html")
def protected_potok():
    if not session.get("access_granted"):
        return "Access denied", 403
    return send_from_directory("static", "potok.html")

@app.route("/authorize", methods=["POST"])
def authorize():
    data = request.get_json()
    code = data.get("code")
    target = data.get("target")  # "potok" или "y"

    if target == "potok" and code == "2007":
        session["access_potok"] = True
        return {"status": "ok"}
    elif target == "y" and code == "Y":
        session["access_y"] = True
        return {"status": "ok"}
    else:
        return {"status": "forbidden"}, 403

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory("static", filename)

@app.route("/api/find_id")
def get_find_id():
    return jsonify(find_id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))