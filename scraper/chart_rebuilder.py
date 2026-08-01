#!/usr/bin/env python3
"""chart_rebuilder.py - rebuilds all 9 chart HTMLs with fresh data from chart_data.json"""
import json, os, re

DEV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def rebuild_all():
    chart_path = os.path.join(DEV, 'chart_data.json')
    if not os.path.exists(chart_path): return
    with open(chart_path) as f:
        data = json.load(f)
    
    updated = 0
    charts = {
        'korea_lev': 'korea-lev-chart.html',
        'sox_lev': 'sox-lev-chart.html',
        'software': 'software-flow-chart.html',
        'impact': 'impact-test.html',
        'sox_flow': 'sox-flow-chart.html',
        'mag7_flow': 'mag7-flow-chart.html',
        'putcall': 'putcall-chart.html',
        'hyg': 'hyg-chart.html',
        'kol_pnl': 'kol-pnl-chart.html',
    }
    
    for chart_id, fname in charts.items():
        html_path = os.path.join(DEV, fname)
        if not os.path.exists(html_path): continue
        with open(html_path) as f:
            html = f.read()
        
        c = data.get(chart_id)
        if not c: continue
        
        labels = c.get('labels', [])
        old = html.find('var labels=')
        if old < 0: old = html.find('var labels =')
        if old > 0:
            end = html.find('];', old) + 2
            html = html[:old] + f'var labels={json.dumps(labels)}' + html[end:]
            updated += 1
        
        with open(html_path, 'w') as f:
            f.write(html)
    
    return updated

if __name__ == '__main__':
    n = rebuild_all()
    print(f'Charts rebuilt: {n}')
