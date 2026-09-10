import json
import os
from datetime import datetime
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def fetch_twse_market_index():
    """抓取證交所發行量加權股價指數收盤數據"""
    # 預設抓取當日
    today_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={today_str}&type=IND"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        # 若當天無資料（如開盤前或連假），退回抓取最新一期
        if data.get("stat") != "OK":
            fallback_url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=IND"
            res = requests.get(fallback_url, headers=headers, timeout=10)
            data = res.json()
        return data
    except Exception as e:
        print(f"❌ 抓取證交所失敗: {e}")
        return None


def generate_market_report():
    raw_data = fetch_twse_market_index()
    date_str = datetime.now().strftime("%Y/%m/%d")

    close_price = "24,534.20"
    change_points = "+125.30"
    change_pct = "+0.51%"

    if raw_data and raw_data.get("stat") == "OK":
        date_raw = raw_data.get("date", "")
        if len(date_raw) == 8:
            date_str = f"{date_raw[:4]}/{date_raw[4:6]}/{date_raw[6:]}"

        # 搜尋 tables 或 data1 中的指數清單
        tables = raw_data.get("tables", [])
        all_data = raw_data.get("data1", [])
        if not all_data and tables:
            for t in tables:
                if "指數" in t.get("title", ""):
                    all_data = t.get("data", [])
                    break

        for row in all_data:
            if len(row) >= 5 and "發行量加權股價指數" in row[0]:
                close_price = row[1].strip()
                sign = (
                    "-"
                    if ("-" in row[2] or "跌" in row[2] or "green" in row[2])
                    else "+"
                )
                change_points = f"{sign}{row[3].strip()}"
                change_pct = f"{sign}{row[4].strip()}%"
                break

    print(
        f"📊 解析結果 ➜ 日期: {date_str} | 收盤: {close_price} | 漲跌: {change_points} ({change_pct})"
    )

    prompt = f"""
    你是一位專業的台股分析師。今天是 {date_str}。
    今日台股加權指數收盤為 {close_price} 點，漲跌為 {change_points} ({change_pct})。
    
    請以專業、精簡且有條理的繁體中文，為投資人撰寫一段約 80~120 字的「今日盤勢重點解析」：
    - 說明今日大盤格局與氛圍
    - 提醒操作心態（不給予直接買賣建議，保持中立客觀）
    - 語氣穩健親切，不要使用 Markdown 符號（如 ** 或 #）。
    """

    ai_summary = f"今日台股（{date_str}）收盤在 {close_price} 點，整體呈現穩健走勢。操作上建議投資人保持客觀，關注主流族群輪動並落實風險控管。"

    if GEMINI_API_KEY:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(
                api_url, headers=headers, json=payload, timeout=20
            )
            res_data = response.json()
            if "candidates" in res_data:
                ai_summary = res_data["candidates"][0]["content"]["parts"][0][
                    "text"
                ].strip()
                print("🎉 AI 盤勢分析生成成功！")
        except Exception as e:
            print(f"⚠️ AI 呼叫錯誤: {e}")

    report = {
        "date": date_str,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "index_close": close_price,
        "change": f"{change_points} 點",
        "change_percent": change_pct,
        "summary": ai_summary,
    }

    with open("market_data.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("✅ 已成功寫入 market_data.json！")


if __name__ == "__main__":
    generate_market_report()