#!/usr/bin/env python3
"""SemiWatch 每日数据更新脚本 — 每天早上9点运行一次"""
import json, os, sys, time
from datetime import datetime

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_DIR = os.path.dirname(SCRAPER_DIR)

print(f"[{datetime.now():%Y-%m-%d %H:%M}] 📡 SemiWatch 每日更新启动")

# 1. 更新价格数据
print("  📈 更新价格...")
try:
    import yfinance as yf
    symbols = {'SOX': '^SOX', 'VIX': '^VIX', 'KOSPI': '^KS11',
               'SK_Hynix': '000660.KS', 'MU': 'MU', 'MRVL': 'MRVL',
               'NVDA': 'NVDA', 'SMH': 'SMH', 'SOXX': 'SOXX'}
    prices = {}
    for name, sym in symbols.items():
        try:
            t = yf.Ticker(sym); info = t.info
            p = info.get('regularMarketPrice') or info.get('currentPrice')
            prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
            if p and prev:
                chg = p - prev
                prices[name] = {'price': round(p,2), 'change': round(chg,2),
                               'changePct': round(chg/prev*100,2)}
            time.sleep(0.5)
        except: pass
    if len(prices) >= 3:
        prices['generated_at'] = datetime.now().isoformat()
        with open(os.path.join(SCRAPER_DIR, 'price_data.json'), 'w') as f:
            json.dump(prices, f, indent=2)
        # Copy to dev dir for dashboard
        with open(os.path.join(DEV_DIR, 'price_data.json'), 'w') as f:
            json.dump(prices, f, indent=2)
        print(f"    ✅ {len(prices)-1}个价格已更新")
    else:
        print("    ⚠️ 价格更新失败(rate limit)，保留昨日数据")
except Exception as e:
    print(f"    ⚠️ 价格模块异常: {e}")

# 2. 更新新闻
print("  📰 更新新闻...")
try:
    sys.path.insert(0, SCRAPER_DIR)
    from news_scraper import scrape_all
    scrape_all()
except Exception as e:
    print(f"    ⚠️ 新闻模块异常: {e}")

print(f"[{datetime.now():%Y-%m-%d %H:%M}] ✅ 每日更新完成")
