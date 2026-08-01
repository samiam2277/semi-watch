#!/usr/bin/env python3
"""每日重新生成仪表盘HTML - 读取最新JSON数据，重写表格"""
import json, os, sys
from datetime import datetime

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_DIR = os.path.dirname(SCRAPER_DIR)

def rebuild():
    # Load latest Korea data
    korea_path = os.path.join(DEV_DIR, 'korea_30day.json')
    with open(korea_path) as f:
        korea = json.load(f)
    
    # Load dashboard template
    dash_path = os.path.join(DEV_DIR, 'semiconductor-dashboard.html')
    with open(dash_path) as f:
        html = f.read()
    
    # Find and replace the Korea flow table rows
    # The table rows are between <tbody> and </tbody> in the first scroll-table
    # We'll look for the marker comment <!-- KOREA_ROWS_START --> and <!-- KOREA_ROWS_END -->
    
    # Build fresh rows
    rows = ''
    for d in korea:
        fc = 'up' if d['foreign_net'] > 0 else 'down'
        ic = 'up' if d['inst_net'] > 0 else 'down'
        fs = f'+{d["foreign_net"]:,}' if d['foreign_net'] > 0 else f'{d["foreign_net"]:,}'
        iis = f'+{d["inst_net"]:,}' if d['inst_net'] > 0 else f'{d["inst_net"]:,}'
        kc = 'up' if d['close'] > 1500000 else ('down' if d['close'] < 1300000 else 'neutral')
        evt = d.get('event', '')
        rows += f'<tr><td style="font-size:10px;white-space:nowrap">{d["date"]}</td><td style="font-size:10px;color:#8b949e;white-space:nowrap">{evt}</td><td class="{fc}" style="font-size:11px;text-align:right;white-space:nowrap">{fs}억</td><td class="{ic}" style="font-size:11px;text-align:right;white-space:nowrap">{iis}억</td><td class="{kc}" style="font-size:11px;text-align:right;white-space:nowrap">{d["close"]:,}</td></tr>\n'
    
    if '<!-- KOREA_ROWS -->' in html:
        old = html.split('<!-- KOREA_ROWS -->')[1].split('<!-- /KOREA_ROWS -->')[0]
        html = html.replace(f'<!-- KOREA_ROWS -->{old}<!-- /KOREA_ROWS -->', f'<!-- KOREA_ROWS -->\n{rows}<!-- /KOREA_ROWS -->')
        print(f'  ✅ Korea rows updated ({len(korea)} days)')
    else:
        print('  ⚠️ KOREA_ROWS markers not found in dashboard')
    
    # Update timestamp
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    old_ts = 'id="updateTime">'
    idx = html.find(old_ts)
    if idx > 0:
        end = html.find('</div>', idx)
        html = html[:idx+len(old_ts)] + f'✅ 数据更新于 {now}（每日自动）' + html[end:]
    
    with open(dash_path, 'w') as f:
        f.write(html)
    
    print(f'✅ Dashboard rebuilt at {now}')

if __name__ == '__main__':
    rebuild()
