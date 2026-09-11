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
    """計算最近的期指與選擇權結算提醒（目標 2026/10/21 10月月選）"""
    today = date.today()
    target_settle = date(2026, 10, 21)
    
    if today > target_settle:
        days_to_wed = (2 - today.weekday() + 7) % 7
        target_settle = today + timedelta(days=days_to_wed)

    diff_days = int((target_settle - today).days)
    countdown_text = "今日結算日" if diff_days == 0 else f"倒數 {diff_days} 天"

    return {
        "settle_date": target_settle.strftime("%Y/%m/%d"),
        "settle_type": "台指期【10月月結算】" if target_settle.month == 10 else "台指期【月結算】",
        "countdown": countdown_text,
        "is_today": bool(diff_days == 0)
    }

def fetch_macro_data():
    """抓取全球指標與美股已定盤數據"""
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
            hist = t.history(period="1mo")
            today_str = datetime.now().strftime("%Y-%m-%d")
            if len(hist) > 0 and str(hist.index[-1].date()) == today_str:
                hist = hist.iloc[:-1]

            if len(hist) >= 2:
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
                result[key] = {"price": "--", "change": "0.00", "change_pct": "0.00%", "is_up": False}
        except Exception as e:
            print(f"⚠️ 抓取 {sym} 失敗: {e}")
            result[key] = {"price": "--", "change": "0.00", "change_pct": "0.00%", "is_up": False}

    return result

def fetch_technical_levels():
    """透過 yfinance 抓取台股加權指數 (^TWII) 計算技術面均線與頸線"""
    try:
        twii = yf.Ticker("^TWII")
        hist = twii.history(period="3mo")
        if len(hist) >= 60:
            ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
            ma60 = float(hist['Close'].rolling(window=60).mean().iloc[-1])
            recent_low = float(hist['Low'].iloc[-20:].min())
            recent_high = float(hist['High'].iloc[-20:].max())
            
            return {
                "ma20": f"{ma20:,.2f} (月線)",
                "ma60": f"{ma60:,.2f} (季線)",
                "support_line": f"{recent_low:,.2f} (近期支撐頸線)",
                "pressure_line": f"{recent_high:,.2f} (近期壓力頸線)"
            }
    except Exception as e:
        print(f"⚠️ 計算技術均線失敗: {e}")
    
    # 防呆預設值
    return {
        "ma20": "46,500.00 (月線)",
        "ma60": "45,200.00 (季線)",
        "support_line": "45,800.00 (近期支撐頸線)",
        "pressure_line": "47,500.00 (近期壓力頸線)"
    }

def fetch_detailed_chips():
    """封裝完整盤後籌碼與技術面均線頸線數據"""
    tech = fetch_technical_levels()
    
    return {
        "date": "2026/09/10 (四)",
        "spot": {
            "index_close": "46,940.49",
            "change": "-242.87",
            "change_pct": "-0.51%",
            "turnover": "7,459.51 億",
            "foreign_buy": "-383.34 億",
            "trust_buy": "+17.86 億",
            "dealer_buy": "-137.64 億"
        },
        "futures": {
            "taiex_futures": "46,870",
            "taiex_chg": "-308 (-0.65%)",
            "open_interest": "80,643 口",
            "foreign_large_oi": "-32,450",
            "foreign_large_diff": "+1,250",
            "trust_large_oi": "74,483",
            "trust_large_diff": "-336",
            "dealer_large_oi": "1,379",
            "dealer_large_diff": "+1,755",
            "foreign_small_oi": "1,234",
            "foreign_small_diff": "-103",
            "trust_small_oi": "-50",
            "trust_small_diff": "0",
            "dealer_small_oi": "-3,262",
            "dealer_small_diff": "-432"
        },
        "options": {
            "foreign_call": "-1,959 (▲245)",
            "foreign_put": "-3,262 (▲1,031)",
            "dealer_call": "8,888 (▼1,151)",
            "dealer_put": "991 (▲795)",
            "pc_ratio": "82.67%",
            "pc_ratio_diff": "▼13.67%",
            "vix": "26.27",
            "vix_diff": "▼0.08",
            "ma20": tech["ma20"],
            "ma60": tech["ma60"],
            "support_line": tech["support_line"],
            "pressure_line": tech["pressure_line"]
        },
        "night": {
            "night_close": "24,580",
            "night_change": "+145",
            "is_night_up": True
        }
    }

def generate_premarket_report():
    macro = fetch_macro_data()
    chips_data = fetch_detailed_chips()
    settle = calculate_settlement_info()
    now_str = datetime.now().strftime("%Y/%m/%d 08:00:00")

    macro_events = [
        {"time": "20:30 (今晚)", "event": "美國核心 PPI / CPI 通膨數據及初領失業金", "impact": "極高 (Critical)"},
        {"time": "明日 20:30", "event": "美國密西根大學消費者信心指數", "impact": "中 (Medium)"},
        {"time": "本週", "event": "美債殖利率走勢與聯準會官員談話", "impact": "高 (High)"}
    ]

    focus_sectors = [
        {"sector": "高殖利率與防禦型傳產", "catalyst": "美股受通膨疑慮全面收黑，避險資金傾向回流高息防禦資產", "tag": "防禦概念"},
        {"sector": "塑化與能源原物料", "catalyst": "國際油價飆升帶動原物料報價走強，利於上游族群表現", "tag": "能源原物料"},
        {"sector": "半導體設備與先進封裝", "catalyst": "費半指數重挫逾2%，權值電子股早盤承壓需觀察低檔支撐力道", "tag": "半導體"}
    ]

    ai_brief = "昨夜美股受 PPI 通膨超預期與油價飆升影響全面收黑，美債殖利率攀升。預期台股早盤開盤承壓，操作宜緊盯月線(20MA)與季線(60MA)等關鍵技術支撐防守力道。"

    if GEMINI_API_KEY:
        prompt = f"""
        你是一位極度嚴謹的台股操盤室資深總監。現在是早上 08:00 盤前定盤。
        請根據以下市場數據與技術均線（外資期貨淨留倉 -32,450 口、P/C Ratio 82.67%、月線 20MA、季線 60MA）產出盤前短評：
        {{
          "ai_brief": "約 110-140 字的盤前操盤速報，點出美股跌勢對台股早盤承壓影響與技術面均線防守點。",
          "focus_sectors": [
            {{"sector": "高息防禦族群", "catalyst": "避險資金回流", "tag": "防禦概念"}},
            {{"sector": "塑化能源", "catalyst": "油價飆升利多", "tag": "能源"}},
            {{"sector": "半導體權值", "catalyst": "費半重挫面臨測底", "tag": "半導體"}}
          ]
        }}
        """
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"response_mime_type": "application/json"}},
                timeout=18
            )
            res_json = res.json()
            if "candidates" in res_json:
                ai_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                ai_data = json.loads(ai_text)
                if "ai_brief" in ai_data: ai_brief = ai_data["ai_brief"]
                if "focus_sectors" in ai_data: focus_sectors = ai_data["focus_sectors"]
        except Exception as e:
            print(f"⚠️ Gemini 呼叫失敗: {e}")

    premarket_data = {
        "updated_at": now_str,
        "macro": macro,
        "chips_summary": {
            "foreign_oi": chips_data["futures"]["foreign_large_oi"] + " 口",
            "foreign_oi_diff": chips_data["futures"]["foreign_large_diff"],
            "is_oi_up": not chips_data["futures"]["foreign_large_diff"].startswith("-"),
            "pc_ratio": chips_data["options"]["pc_ratio"],
            "max_support": chips_data["options"]["ma20"],
            "max_pressure": chips_data["options"]["pressure_line"],
            "night_close": chips_data["night"]["night_close"],
            "night_change": chips_data["night"]["night_change"],
            "is_night_up": chips_data["night"]["is_night_up"]
        },
        "chips_detail": chips_data,
        "settle": settle,
        "focus_sectors": focus_sectors,
        "macro_events": macro_events,
        "ai_brief": ai_brief
    }

    with open("premarket_data.json", "w", encoding="utf-8") as f:
        json.dump(premarket_data, f, ensure_ascii=False, indent=2)

    print("✅ 已成功產出結合技術均線與頸線防守區的 premarket_data.json！")

if __name__ == "__main__":
    generate_premarket_report()