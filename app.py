
from flask import Flask, request, jsonify, session, send_from_directory
import requests, json, time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Загружаем find_id
find_id = {}
with open("youpin898.txt", encoding="utf-8") as f:
    for line in f:
        try:
            name = line.split(": ")[0][3:-1]
            ID = line.split(": ")[1][:-2]
            find_id[name] = ID
        except:
            continue

# Загружаем skin_map
with open("buff163.txt", encoding="utf-8") as f:
    skin_map = json.load(f)

# Загружаем sales.json
with open("sales.json", "r", encoding="utf-8") as f:
    sales_map = json.load(f)

def get_youpin_price(name):
    try:
        youpinID = find_id.get(name)
        if not youpinID:
            return None
        url = "https://www.youpin898.com/api/homepage/frontPage"
        data = {"listType": 10, "templateId": youpinID, "pageSize": 1, "sortType": 1}
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.youpin898.com"}
        r = requests.post(url, json=data, headers=headers, timeout=10)
        result = r.json()
        if result["code"] == 0 and result["data"]["list"]:
            price_str = result["data"]["list"][0]["price"]
            return float(price_str) if price_str else None
    except:
        return None

@app.route("/api/price")
def get_price_data():
    name = request.args.get("name")
    goods_id = skin_map.get(name)
    if not goods_id:
        return jsonify({"error": f"Скин '{name}' не найден"}), 404

    results = {}

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
            r = requests.get(f"https://market.csgo.com/api/v2/search-item-by-hash-name?key=xxx&hash_name={name}", timeout=10)
            data = r.json()
            return float(data["data"][0]["price"]) if "data" in data else None
        except:
            return None

    def fetch_youpin():
        try:
            youpinID = find_id.get(name)
            price = get_youpin_price(name)
            return youpinID, price
        except:
            return None, None

    with ThreadPoolExecutor() as executor:
        f_buff = executor.submit(fetch_buff)
        f_leg1t = executor.submit(fetch_leg1t)
        f_youpin = executor.submit(fetch_youpin)

        results["buff"], results["icon"] = f_buff.result()
        results["leg1t"] = f_leg1t.result()
        results["youpinID"], results["youpin"] = f_youpin.result()

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

# Остальные маршруты оставляю без изменений

@app.route("/api/skins")
def get_skin_names():
    return jsonify(list(skin_map.keys()))

@app.route("/api/youpin_names")
def youpin_skin_names():
    return jsonify(list(find_id.keys()))

@app.route("/api/sales")
def get_sales():
    return jsonify(sales_map)

@app.route("/api/find_id")
def get_find_id():
    return jsonify(find_id)

@app.route("/authorize", methods=["POST"])
def authorize():
    data = request.get_json()
    if data.get("code") == "2007":
        session["access_granted"] = True
        return {"status": "ok"}
    return {"status": "forbidden"}, 403

@app.route("/potok.html")
def protected_potok():
    if not session.get("access_granted"):
        return "Access denied", 403
    return send_from_directory("static", "potok.html")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
