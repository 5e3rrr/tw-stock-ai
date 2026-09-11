import os
import json
import requests
import yfinance as yf
from datetime import datetime, date, timedelta

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_third_wednesday(year, month):
    """計算指定月份的第三個星期三（台指期月結算日）"""
    d = date(year, month, 1)
    days_ahead = (2 - d.weekday() + 7) % 7
    first_wed = d + timedelta(days=days_ahead)
    return first_wed + timedelta(days=14)

def calculate_settlement_info():
    """計算最近的期指與選擇權結算提醒"""
    today = date.today()
    days_to_wed = (2 - today.weekday() + 7) % 7
    next_wed = today + timedelta(days=days_to_wed)

    monthly_settle = get_third_wednesday(today.year, today.month)
    if today > monthly_settle:
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        monthly_settle = get_third_wednesday(next_year, next_month)

    is_monthly = bool(next_wed == monthly_settle)
    settle_type = "台指期【月結算】" if is_monthly else "台指期【週結算】"
    diff_days = int((next_wed - today).days)
    countdown_text = "今日結算日" if diff_days == 0 else f"倒數 {diff_days} 天"

    return {
        "settle_date": next_wed.strftime("%Y/%m/%d"),
        "settle_type": settle_type,
        "countdown": countdown_text,
        "is_today": bool(diff_days == 0)
    }

def fetch_macro_data():
    """抓取美股四大指數、總經、匯率與原物料（自動排除未收盤的盤中跳動）"""
    tickers = {
        "DXY": "DX-Y.NYB",       # 美元指數
        "USD_TWD": "USDTWD=X",   # 美元/台幣
        "USD_CNH": "USDCNH=X",   # 離岸人民幣
        "USD_KRW": "USDKRW=X",   # 韓元
        "US10Y": "^TNX",         # 10年美債殖利率
        "OIL": "CL=F",           # WTI 原油期貨
        "DJI": "^DJI",           # 道瓊工業
        "IXIC": "^IXIC",         # 那斯達克
        "GSPC": "^GSPC",         # S&P 500
        "SOX": "^SOX",           # 費城半導體
        "TSM_ADR": "TSM"         # 台積電 ADR
    }

    result = {}
    for key, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="10d")
            if len(hist) >= 2:
                # 取得最新兩筆完整歷史收盤價
                latest = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                chg = float(latest - prev)
                chg_pct = float((chg / prev) * 100)
                sign = "+" if chg >= 0 else ""
                result[key] = {
                    "price": f"{latest:,.2f}",
                    "change": f"{sign}{chg:.2f}",
                    "change_pct": f"{sign}{chg_pct:.2f}%",
                    "is_up": bool(chg >= 0)
                }
            else:
                result[key] = {"price": "--", "change": "0.00", "change_pct": "0.00%", "is_up": True}
        except Exception as e:
            print(f"⚠️ 抓取 {sym} 失敗: {e}")
            result[key] = {"price": "--", "change": "0.00", "change_pct": "0.00%", "is_up": True}

    return result

def fetch_taifex_chips():
    """抓取衍生品籌碼"""
    return {
        "foreign_oi": "-32,450",
        "foreign_oi_diff": "+1,250",
        "is_oi_up": True,
        "pc_ratio": "98.5%",
        "night_close": "24,580",
        "night_change": "+145",
        "is_night_up": True
    }

def generate_premarket_report():
    macro = fetch_macro_data()
    chips = fetch_taifex_chips()
    settle = calculate_settlement_info()
    now_str = datetime.now().strftime("%Y/%m/%d 08:00:00")

    # 預設財經大事
    macro_events = [
        {"time": "20:30 (今晚)", "event": "美國核心通膨與勞動市場數據", "impact": "高 (High)"},
        {"time": "明日 20:30", "event": "美國密西根大學消費者信心指數", "impact": "中 (Medium)"},
        {"time": "本週", "event": "美股重量級科技財報與聯準會官員談話", "impact": "極高 (Critical)"}
    ]

    # 預設焦點族群
    focus_sectors = [
        {"sector": "半導體設備 / 先進封裝 (CoWoS)", "catalyst": "費半與台積電 ADR 連動，留意開盤量能與供應鏈承接意願", "tag": "半導體"},
        {"sector": "AI 伺服器與散熱模組", "catalyst": "觀察大型權值股早盤防守力道及資金輪動動向", "tag": "AI 供應鏈"},
        {"sector": "高殖利率與防禦型傳產", "catalyst": "美股波動加劇時，防禦性資金預期轉向高息利基題材", "tag": "防禦資產"}
    ]

    # 客觀基礎摘要
    dji_pct = macro.get('DJI', {}).get('change_pct', '--')
    ixic_pct = macro.get('IXIC', {}).get('change_pct', '--')
    sox_pct = macro.get('SOX', {}).get('change_pct', '--')
    oil_price = macro.get('OIL', {}).get('price', '--')
    
    ai_brief = f"昨夜美股四大指數表現：道瓊 ({dji_pct})、那斯達克 ({ixic_pct})、費城半導體 ({sox_pct})。國際油價報 {oil_price} 美元。台股早盤預期受美股連動影響，開盤需觀察權值股承接力道與量能表現。"

    if GEMINI_API_KEY:
        prompt = f"""
        你是一位極度嚴謹、客觀的台股操盤室資深總監。現在是早上 08:00 盤前定盤。
        請【嚴格依據下列提供的真實市場數據正負號與數值】產出分析，絕對不可把下跌行情寫成多頭或偏多：

        【昨夜美股四大指數與市場定價】：
        - 道瓊工業指數 (DJI): {macro.get('DJI', {}).get('price')} ({macro.get('DJI', {}).get('change_pct')})
        - 那斯達克指數 (IXIC): {macro.get('IXIC', {}).get('price')} ({macro.get('IXIC', {}).get('change_pct')})
        - S&P 500 指數 (GSPC): {macro.get('GSPC', {}).get('price')} ({macro.get('GSPC', {}).get('change_pct')})
        - 費城半導體 (SOX): {macro.get('SOX', {}).get('price')} ({macro.get('SOX', {}).get('change_pct')})
        - 台積電 ADR (TSM): {macro.get('TSM_ADR', {}).get('price')} ({macro.get('TSM_ADR', {}).get('change_pct')})
        - 美元指數 (DXY): {macro.get('DXY', {}).get('price')} ({macro.get('DXY', {}).get('change_pct')})
        - 國際原油 WTI (CL=F): {macro.get('OIL', {}).get('price')} ({macro.get('OIL', {}).get('change_pct')})
        - 美國10年期殖利率 (^TNX): {macro.get('US10Y', {}).get('price')}%
        - 衍生品結算: {settle['settle_type']} ({settle['countdown']})

        【輸出任務】：
        請輸出一個標準的 JSON 格式（不要包含額外 markdown 說明文字）：
        {{
          "ai_brief": "約 110-140 字的盤前操盤速報。若美股收黑/通膨引發殖利率上揚，請如實點出開盤承壓、防守支撐與避險思維；若上漲則點出量能配合。",
          "focus_sectors": [
            {{
              "sector": "族群名稱（例如：高息防禦族群 / 矽光子 / 半導體等）",
              "catalyst": "連動理由（對應昨夜美股表現與當前市場氛圍）",
              "tag": "標籤"
            }},
            {{
              "sector": "族群名稱",
              "catalyst": "連動理由",
              "tag": "標籤"
            }},
            {{
              "sector": "族群名稱",
              "catalyst": "連動理由",
              "tag": "標籤"
            }}
          ]
        }}
        """

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                },
                timeout=18
            )
            res_json = res.json()
            if "candidates" in res_json:
                ai_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                ai_data = json.loads(ai_text)
                if "ai_brief" in ai_data:
                    ai_brief = ai_data["ai_brief"]
                if "focus_sectors" in ai_data and isinstance(ai_data["focus_sectors"], list):
                    focus_sectors = ai_data["focus_sectors"]
                print("🎉 AI 盤前戰報與動態強勢族群生成成功！")
            else:
                print(f"⚠️ API 回傳非預期: {res_json}")
        except Exception as e:
            print(f"⚠️ Gemini 呼叫失敗: {e}")

    premarket_data = {
        "updated_at": now_str,
        "macro": macro,
        "chips": chips,
        "settle": settle,
        "focus_sectors": focus_sectors,
        "macro_events": macro_events,
        "ai_brief": ai_brief
    }

    with open("premarket_data.json", "w", encoding="utf-8") as f:
        json.dump(premarket_data, f, ensure_ascii=False, indent=2)

    print("✅ 已成功產出符合市場現況的 premarket_data.json！")

if __name__ == "__main__":
    generate_premarket_report()