import json
import os
from datetime import datetime
import requests

# 從系統環境變數讀取金鑰
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def fetch_twse_market_index():
    """抓取證交所當日發行量加權股價指數真實收盤數據"""
    url = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=IND"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("stat") != "OK":
            print(f"⚠️ 證交所 API 狀態異常: {data.get('stat')}")
            return None
        return data
    except Exception as e:
        print(f"❌ 抓取證交所失敗: {e}")
        return None


def generate_market_report():
    raw_data = fetch_twse_market_index()
    today_dt = datetime.now()
    date_str = today_dt.strftime("%Y/%m/%d")

    close_price = None
    change_points = None
    change_pct = None

    if raw_data:
        # 格式化證交所回傳日期 (民國或西元)
        date_raw = raw_data.get("date", "")
        if len(date_raw) == 8:
            date_str = f"{date_raw[:4]}/{date_raw[4:6]}/{date_raw[6:]}"

        # 搜尋包含加權指數的資料區塊 (可能在 data1、tables 或不同鍵值中)
        data_rows = (
            raw_data.get("data1")
            or raw_data.get("tables", [{}])[0].get("data", [])
            or []
        )

        for row in data_rows:
            # 比對大盤加權指數列
            if len(row) >= 5 and "發行量加權股價指數" in row[0]:
                close_price = row[1].strip()  # 收盤指數

                # 判定漲跌符號
                sign_str = row[2].strip()
                points = row[3].strip()
                pct = row[4].strip()

                if "-" in sign_str or "跌" in sign_str or "green" in sign_str:
                    change_points = f"-{points}"
                    change_pct = f"-{pct}%"
                else:
                    change_points = f"+{points}"
                    change_pct = f"+{pct}%"
                break

    # 若遇假日或開盤前未取到資料，進行提示處理
    if not close_price:
        print("⚠️ 今日尚未開盤或未取得收盤資料，將標註休市/待更新狀態")
        close_price = "暫無資料"
        change_points = "0.00"
        change_pct = "0.00%"

    print(
        f"📊 成功解析市場數據 ➜ 日期: {date_str} | 收盤: {close_price} | 漲跌: {change_points} ({change_pct})"
    )

    prompt = f"""
    你是一位專業的台股分析師。今天是 {date_str}。
    今日台股加權指數收盤為 {close_price} 點，漲跌為 {change_points} ({change_pct})。
    
    請以專業、精簡且有條理的繁體中文，為投資人撰寫一段約 80~120 字的「今日盤勢重點解析」：
    - 說明今日大盤格局與氛圍
    - 提醒操作心態（不給予直接買賣建議，保持中立客觀）
    - 語氣穩健親切，不要使用 Markdown 符號（如 ** 或 #）。
    """

    ai_summary = "今日台股呈現震盪整理格局，權值股漲跌互見，市場資金輪動快速，建議投資人留意國際總經變數與族群延續性，謹慎控管部位。"

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
            else:
                print(f"⚠️ API 回傳結果：{res_data}")
        except Exception as e:
            print(f"⚠️ 呼叫 AI 時發生錯誤：{e}")
    else:
        print("⚠️ 未偵測到 GEMINI_API_KEY 環境變數，使用預設分析。")

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

    print("✅ 已成功更新 market_data.json！")


if __name__ == "__main__":
    generate_market_report()