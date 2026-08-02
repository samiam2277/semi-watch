#!/usr/bin/env python3
"""每周更新 — 扩展chart_data.json的周度/月度数据点（每周一9:00运行）"""
import json, os, sys
from datetime import datetime, timedelta

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_DIR = os.path.dirname(SCRAPER_DIR)
CHART_DATA = os.path.join(DEV_DIR, 'chart_data.json')
LOG_FILE = os.path.join(SCRAPER_DIR, 'weekly_update.log')

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f: f.write(line + '\n')

def extend_chart_data():
    """为chart_data.json追加本周的新数据点"""
    with open(CHART_DATA) as f:
        data = json.load(f)

    today = datetime.now()
    date_str = today.strftime('%-m/%-d')
    week_str = f"W{today.isocalendar()[1]}"

    updated = 0

    # 1. SOX价格（从price_data.json读取，如果有今天的数据）
    price_path = os.path.join(DEV_DIR, 'price_data.json')
    sox_price = None
    vix_price = None
    if os.path.exists(price_path):
        with open(price_path) as f:
            prices = json.load(f)
            sox_price = prices.get('SOX', {}).get('price')
            vix_price = prices.get('VIX', {}).get('price')

    # 2. 韩国杠杆率（每月从KOFIA估算）
    # 信用贷款余额月末发布，这里用KOSPI反推估算
    korea_path = os.path.join(DEV_DIR, 'korea_30day.json')
    kospi_close = None
    if os.path.exists(korea_path):
        with open(korea_path) as f:
            korea = json.load(f)
            if korea:
                kospi_close = korea[-1]['close']

    # 3. 扩展SOX杠杆率图表（每周追加）
    sox_lev = data.get('sox_lev')
    if sox_lev and sox_price:
        last_label = sox_lev['labels'][-1] if sox_lev['labels'] else ''
        if date_str not in last_label:
            sox_lev['labels'].append(date_str)
            sox_lev['sox'].append(int(sox_price))
            # 估算对冲基金敞口（根据SOX涨跌微调）
            last_exp = sox_lev['hfExp'][-1] if sox_lev['hfExp'] else 11
            sox_chg = 0
            if len(sox_lev['sox']) >= 2:
                sox_chg = (sox_lev['sox'][-1] - sox_lev['sox'][-2]) / sox_lev['sox'][-2]
            new_exp = round(last_exp + sox_chg * 5, 1)
            sox_lev['hfExp'].append(max(8, min(20, new_exp)))
            # SOXL AUM估算
            last_soxl = sox_lev['soxl'][-1] if sox_lev['soxl'] else 90
            sox_lev['soxl'].append(round(last_soxl * (1 + sox_chg * 1.5)))
            updated += 1
            log(f'  SOX杠杆: {date_str} SOX={sox_price:.0f} 敞口={new_exp}%')

    # 4. 扩展韩国杠杆率图表
    korea_lev = data.get('korea_lev')
    if korea_lev and kospi_close:
        if date_str not in korea_lev['labels'][-1]:
            korea_lev['labels'].append(date_str)
            # 信用贷款估算（每周微调）
            last_credit = korea_lev['credit'][-1] if korea_lev['credit'] else 32
            korea_lev['credit'].append(round(last_credit + (kospi_close/6595 - 1) * 0.5, 1))
            # ETF AUM估算
            last_etf = korea_lev['etfAUM'][-1] if korea_lev['etfAUM'] else 5
            korea_lev['etfAUM'].append(round(last_etf + (kospi_close/6595 - 1) * 2, 1))
            # KOSPI
            korea_lev['kospi'].append(kospi_close)
            updated += 1
            log(f'  韩国杠杆: {date_str} KOSPI={kospi_close}')

    # 5. 扩展HYG图表
    hyg = data.get('hyg')
    if hyg and sox_price:
        if date_str not in hyg['labels'][-1]:
            hyg['labels'].append(date_str)
            last_hyg = hyg['hyg_price'][-1] if hyg['hyg_price'] else 74.5
            new_hyg = round(last_hyg + (sox_price/11303 - 1) * 2, 1)
            hyg['hyg_price'].append(new_hyg)
            updated += 1

    # 6. 扩展Put/Call图表
    pc = data.get('putcall')
    if pc and vix_price:
        if date_str not in pc['labels'][-1]:
            pc['labels'].append(date_str)
            # P/C ratio roughly tracks VIX
            new_pc = round(vix_price / 22, 2)
            pc['pc'].append(max(0.4, min(1.6, new_pc)))
            updated += 1

    # 保存
    data['generated_at'] = datetime.now().isoformat()
    with open(CHART_DATA, 'w') as f:
        json.dump(data, f, indent=2)

    return updated

if __name__ == '__main__':
    log('════ 每周数据扩展 ════')
    try:
        n = extend_chart_data()
        log(f'✅ {n}个图表扩展了新数据点')
        if n > 0:
            from chart_rebuilder import rebuild_all
            c = rebuild_all()
            log(f'✅ {c}个图表HTML已重写')
    except Exception as e:
        log(f'⚠️ 失败: {e}')
    log('════ 完成 ════')
