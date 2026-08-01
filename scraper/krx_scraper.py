#!/usr/bin/env python3
"""SK海力士韩国外资日数据爬虫 — Naver Finance"""
import urllib.request, ssl, json, os, sys
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'korea_30day.json')

def scrape_korea_flow():
    url = "https://finance.naver.com/item/frgn.naver?code=000660&page=1"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://finance.naver.com/'
    })
    r = urllib.request.urlopen(req, context=ctx, timeout=15)
    html = r.read().decode('euc-kr', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')

    rows_data = []
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 9: continue
        try:
            date_str = cells[0].get_text(strip=True)
            close = int(cells[1].get_text(strip=True).replace(',',''))
            f_shares = int(cells[5].get_text(strip=True).replace(',','').replace('+',''))
            i_shares = int(cells[6].get_text(strip=True).replace(',','').replace('+',''))
            foreign_pct = cells[8].get_text(strip=True).replace('%','')

            # Net amount in 억원 = shares * close / 1억
            f_amount = round(f_shares * close / 100000000, 0)
            i_amount = round(i_shares * close / 100000000, 0)

            rows_data.append({
                'date': date_str,
                'close': close,
                'foreign_net_억': int(f_amount),
                'inst_net_억': int(i_amount),
                'foreign_pct': float(foreign_pct),
            })
        except: continue

    rows_data.sort(key=lambda x: x['date'])
    rows_data = rows_data[-30:]

    # Load existing for event annotations
    event_map = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            old = json.load(f)
            event_map = {d.get('date',''): d.get('event','') for d in old}

    output = []
    for d in rows_data:
        date_fmt = d['date']
        evt = ''
        try:
            dt = datetime.strptime(d['date'], '%Y.%m.%d')
            date_fmt = dt.strftime('%#m/%#d') if sys.platform=='win32' else dt.strftime('%-m/%-d')
            evt = event_map.get(dt.strftime('%-m/%-d'), '')
        except: pass
        entry = {
            'date': date_fmt,
            'close': d['close'],
            'foreign_net': d['foreign_net_억'],
            'inst_net': d['inst_net_억'],
            'foreign_pct': d['foreign_pct'],
            'event': evt,
        }
        output.append(entry)

    with open(OUTPUT, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output

if __name__ == '__main__':
    data = scrape_korea_flow()
    for d in data[-5:]:
        f = d['foreign_net']
        i = d['inst_net']
        print(f"  {d['date']}  收盘:{d['close']:,}  外资:{'+'if f>0 else''}{f}억  机构:{'+'if i>0 else''}{i}억")
