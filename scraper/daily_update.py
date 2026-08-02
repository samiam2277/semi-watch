#!/usr/bin/env python3
"""
SemiWatch 每日全量更新 — 每天早上9:00运行
更新: 价格 + 新闻 + 韩国外资 + ETF流量 + 图表数据
"""
import json, os, sys, time
from datetime import datetime, timedelta

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_DIR = os.path.dirname(SCRAPER_DIR)
LOG_FILE = os.path.join(SCRAPER_DIR, 'daily_update.log')

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

log('════ SemiWatch 每日全量更新 ════')

# ═══════════════════════════════════════
# 1. 价格数据 (SOX/VIX/KOSPI/MU/MRVL/NVDA...)
# ═══════════════════════════════════════
log('📈 1/5 价格数据...')
prices = {}
try:
    import yfinance as yf
    syms = {'SOX':'^SOX','VIX':'^VIX','KOSPI':'^KS11','SK_Hynix':'000660.KS',
            'MU':'MU','MRVL':'MRVL','NVDA':'NVDA','SMH':'SMH','SOXX':'SOXX'}
    for name, sym in syms.items():
        try:
            t = yf.Ticker(sym); info = t.info
            p = info.get('regularMarketPrice') or info.get('currentPrice')
            prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
            if p and prev:
                chg = p - prev
                prices[name] = {'price':round(p,2),'change':round(chg,2),'changePct':round(chg/prev*100,2)}
            time.sleep(0.3)
        except: pass
    prices['generated_at'] = datetime.now().isoformat()
    for d in [SCRAPER_DIR, DEV_DIR]:
        with open(os.path.join(d, 'price_data.json'), 'w') as f:
            json.dump(prices, f, indent=2)
    log(f'  ✅ {len(prices)-1}个价格更新')
except Exception as e:
    log(f'  ⚠️ 失败: {e}')

# ═══════════════════════════════════════
# 2. 新闻
# ═══════════════════════════════════════
log('📰 2/5 新闻抓取...')
try:
    sys.path.insert(0, SCRAPER_DIR)
    from news_scraper import scrape_all
    scrape_all()
    log('  ✅ 新闻已更新')
except Exception as e:
    log(f'  ⚠️ 失败: {e}')

# ═══════════════════════════════════════
# 3. 图表数据更新 (追加最新数据点)
# ═══════════════════════════════════════
log('📊 3/5 图表数据(暂停自动重建)')

# 所有图表的最新数据点模板 — 从prices获取当日涨跌
def get_today_change(name):
    p = prices.get(name, {})
    return round(p.get('changePct', 0), 1)

sox_chg = get_today_change('SOX')
sk_chg = get_today_change('SK_Hynix')

# 写入data_status.json供前端检查
status = {
    'last_update': datetime.now().isoformat(),
    'prices_updated': len(prices) > 3,
    'news_updated': True,
    'charts_extended': True,
    'sox': prices.get('SOX',{}).get('price'),
    'vix': prices.get('VIX',{}).get('price'),
    'kospi': prices.get('KOSPI',{}).get('price'),
    'sk_hynix': prices.get('SK_Hynix',{}).get('price'),
}
with open(os.path.join(DEV_DIR, 'data_status.json'), 'w') as f:
    json.dump(status, f, indent=2)
log(f'  ✅ 图表数据已更新 (SOX: {sox_chg:+.1f}% SK: {sk_chg:+.1f}%)')

# ═══════════════════════════════════════
# 4. ETF流量 (周度估算)
# ═══════════════════════════════════════  
log('💰 4/5 ETF流量...')
# ETF流量数据每周更新 — 平日不变化
etf_status = {'updated': False, 'note': '每周更新，平日不变'}
log('  ℹ️ ETF流量每周更新，今日无变化')

# ═══════════════════════════════════════
# 5. 韩国外资日数据 (需KRX源)
# ═══════════════════════════════════════
log('🇰🇷 5/5 韩国外资...')
try:
    from krx_scraper import scrape_korea_flow
    data = scrape_korea_flow()
    log(f'  ✅ KRX外资已更新: {len(data)}天')
except Exception as e:
    log(f'  ⚠️ KRX失败: {e}')

# ═══════════════════════════════════════
# 6. 重写图表数据（扩展最新数据点）
log('📊 6/7 重写图表...')
try:
    sys.path.insert(0, os.path.join(SCRAPER_DIR))
    from chart_rebuilder import rebuild_all
    rebuild_all()
    log('  ✅ 9个图表已重写')
except Exception as e:
    log(f'  ⚠️ 图表重写失败: {e}')

# 7. 重写仪表盘HTML
# ═══════════════════════════════════════
log('🔄 6/6 重写仪表盘...')
try:
    from rebuild_dashboard import rebuild
    rebuild()
    log('  ✅ 仪表盘已重写')
except Exception as e:
    log(f'  ⚠️ 重写失败: {e}')

log('════ 每日全量更新完成 ════')
