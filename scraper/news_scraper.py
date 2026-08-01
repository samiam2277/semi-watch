#!/usr/bin/env python3
"""
SemiWatch 半导体新闻抓取器
抓取多个源的半导体/存储相关新闻，进行关键词情绪打分，输出JSON
运行: python3 news_scraper.py          → 输出到 news_data.json
      python3 news_scraper.py --serve   → 启动简易HTTP服务（配合前端）
"""
import json, re, sys, os, time
from datetime import datetime, timedelta
from collections import Counter
import feedparser
import requests
from bs4 import BeautifulSoup
from http.server import HTTPServer, SimpleHTTPRequestHandler

# ==================== 配置 ====================
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'news_data.json')

# RSS 源 — 聚焦大利好/大利空的金融快讯源
RSS_FEEDS = [
    # 🇨🇳 中文快讯（金十数据/华尔街见闻/财联社 — 利好利空最直接）
    ('https://news.google.com/rss/search?q=site:jin10.com+半导体+芯片+存储+暴涨+暴跌+熔断+涨停&hl=zh-CN&gl=CN&ceid=CN:zh-Hans', '金十数据'),
    ('https://news.google.com/rss/search?q=site:jin10.com+三星+海力士+美光+英伟达+台积电&hl=zh-CN&gl=CN&ceid=CN:zh-Hans', '金十数据'),
    ('https://news.google.com/rss/search?q=site:wallstreetcn.com+半导体+芯片+存储+HBM&hl=zh-CN&gl=CN&ceid=CN:zh-Hans', '华尔街见闻'),
    ('https://news.google.com/rss/search?q=site:cls.cn+半导体+芯片+暴涨+暴跌+涨停+熔断&hl=zh-CN&gl=CN&ceid=CN:zh-Hans', '财联社'),
    # 🇺🇸 英文核心（market-moving news）
    ('https://news.google.com/rss/search?q=semiconductor+chip+stock+surge+plunge+record+crash&hl=en-US&gl=US&ceid=US:en', 'Google News'),
    ('https://news.google.com/rss/search?q=SK+Hynix+Samsung+Micron+Nvidia+earnings+beat+miss+capex&hl=en-US&gl=US&ceid=US:en', 'Google News'),
    ('https://news.google.com/rss/search?q=반도체+급등+폭락+상한가+서킷브레이커&hl=ko&gl=KR&ceid=KR:ko', 'Google News KR'),
]

# HTML备用源
HTML_SOURCES = []

# ==================== 情绪词典 ====================
BULLISH_PATTERNS = [
    # 英文
    r'\bbeat\b', r'\bsurge\b', r'\brally\b', r'\brecord\b', r'\bupgrade\b',
    r'\bshortage\b', r'\btight\b supply', r'\boutperform\b', r'\b超预期\b',
    r'\b上调\b', r'\b突破\b', r'\b新高\b', r'\b反弹\b', r'\b短缺\b',
    r'\bHBM4\b', r'\b量产\b', r'\b扩产\b', r'\b回购\b', r'\b增持\b',
    r'\b新建仓\b', r'\bbuyback\b', r'\bCapEx\b.*\b(raise|increase|boost)\b',
    r'\bAzure\b.*\b(accelerate|growth|beat)\b',
    r'\bAI\b.*\bdemand\b', r'\bchip\b.*\bshortage\b',
    r'\bguidance\b.*\b(raise|boost|above)\b',
    r'\binflow\b', r'\baccumulate\b', r'\b外资.*买\b',
    r'\b상한가\b', r'\b반등\b', r'\b순매수\b',
    r'\bNVIDIA\b.*\bpartner\b', r'\b出货\b.*\b增长\b',
    # 扩展模式
    r'\bjump\b', r'\bsoar\b', r'\bpop\b', r'\bclimb\b', r'\bgain\b',
    r'\brebound\b', r'\brecover', r'\bbullish\b', r'\boptimism\b',
    r'\bstrong\b.*\b(growth|demand|result|quarter|earnings)\b',
    r'\b(raise|boost|lift)\b.*\b(target|guidance|forecast|outlook)\b',
    r'\bexceed\b', r'\bprofit\b.*\b(jump|surge|rise|climb)\b',
    r'\brevenue\b.*\b(jump|surge|rise|climb|beat)\b',
    r'\bAI\b.*\b(spending|investment|build)\b',
    r'\bbreak\b.*\bthrough\b', r'\bmilestone\b', r'\bpartnership\b',
    r'\bfastest\b.*\bgrowth\b', r'\baccelerate\b',
    r'\b제품\b.*\b출하\b', r'\b실적\b.*\b(개선|호조|서프라이즈)\b',
    r'\b수출\b.*\b증가\b', r'\b호실적\b', r'\b급등\b',
]

BEARISH_PATTERNS = [
    # 原有
    r'\bmiss\b', r'\bplunge\b', r'\bcrash\b', r'\btumble\b', r'\bdowngrade\b',
    r'\bselloff\b', r'\bbear\b', r'\bdecline\b', r'\b不及预期\b',
    r'\b下调\b', r'\b暴跌\b', r'\b熔断\b', r'\b熊市\b',
    r'\b过剩\b', r'\b产能过剩\b', r'\b禁售\b', r'\b限制\b',
    r'\b做空\b', r'\b减持\b', r'\b清仓\b', r'\b泡沫\b',
    r'\bfree cash flow\b.*\bnegative\b', r'\bFCF.*转负\b',
    r'\blayoff\b', r'\b裁员\b', r'\btariff\b', r'\bexport\b.*\b(curb|ban|restrict)\b',
    r'\bliquidat\b', r'\bmargin\b.*\bcall\b', r'\b強平\b',
    r'\b하한가\b', r'\b폭락\b', r'\b순매도\b', r'\b서킷브레이커\b',
    r'\bDelist\b', r'\bdelisting\b', r'\bfraud\b', r'\bprobe\b',
    r'\bchip\b.*\b(glut|oversupply)\b', r'\bprice\b.*\b(cut|decline|fall)\b',
    r'\bChina\b.*\b(ban|restrict)\b', r'\bCXMT\b',
    # 扩展模式
    r'\bsink\b', r'\bdrop\b', r'\bslide\b', r'\bslump\b', r'\bfall\b',
    r'\bwarn\b', r'\bcautio\b', r'\brisk\b', r'\bworr\b', r'\bfear\b',
    r'\bweak\b.*\b(guidance|demand|outlook|forecast|quarter)\b',
    r'\b(cut|slash|trim)\b.*\b(target|guidance|forecast|outlook)\b',
    r'\bloss\b', r'\bnegative\b.*\b(growth|margin|cash)\b',
    r'\bdebt\b.*\b(concern|risk|worry)\b', r'\boverheat\b',
    r'\bbubble\b', r'\bcorrection\b', r'\bvolatil\b',
    r'\bdisappoint\b', r'\bdelay\b', r'\bsuspend\b', r'\bhalt\b',
    r'\b공매도\b', r'\b위기\b', r'\b경고\b', r'\b부진\b',
    r'\b급락\b', r'\b폭등\b.*\b(우려|경고|위험)\b',
]

# 过滤词（排除无关新闻）
IRRELEVANT_PATTERNS = [
    r'\bsoccer\b', r'\bfootball\b', r'\bNBA\b', r'\bcelebrity\b',
    r'\brecipe\b', r'\bweather\b', r'\belection\b.*\b(governor|senate)\b',
]

def classify_sentiment(text):
    """对单条文本进行情绪分类"""
    text_lower = text.lower()
    bullish = sum(1 for p in BULLISH_PATTERNS if re.search(p, text_lower))
    bearish = sum(1 for p in BEARISH_PATTERNS if re.search(p, text_lower))
    if bullish > bearish: return 'bull'
    if bearish > bullish: return 'bear'
    return 'neutral'

def is_relevant(text):
    """过滤无关内容"""
    return not any(re.search(p, text.lower()) for p in IRRELEVANT_PATTERNS)

def is_semiconductor_related(text):
    """检查文本是否与半导体相关"""
    keywords = [
        'chip', 'semiconductor', 'memory', 'DRAM', 'NAND', 'HBM',
        'Nvidia', 'NVDA', 'AMD', 'Intel', 'INTC', 'Micron', 'MU',
        'SK Hynix', 'Samsung', 'TSMC', 'Broadcom', 'AVGO',
        'Qualcomm', 'QCOM', 'Marvell', 'MRVL', 'Applied Materials', 'AMAT',
        'ASML', 'Sandisk', 'SNDK', 'Western Digital', 'WDC', 'Seagate',
        'AI', 'GPU', 'foundry', 'wafer', 'lithography', '光刻',
        '芯片', '半导体', '存储', '海力士', '三星', '美光',
        '반도체', '하이닉스', '삼성전자', 'CXMT', '长鑫',
        'SOX', 'KOSPI', '费城', '코스피',
    ]
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

# ==================== 抓取逻辑 ====================
def scrape_rss(url, source_name):
    """抓取单个RSS源"""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:30]:  # 每个源最多30条
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            text = f"{title} {summary}"

            if not is_semiconductor_related(text):
                continue
            if not is_relevant(text):
                continue

            published = entry.get('published', entry.get('updated', ''))
            sentiment = classify_sentiment(text)

            articles.append({
                'title': title,
                'source': source_name,
                'url': entry.get('link', ''),
                'time': published[:25] if published else '',
                'sentiment': sentiment,
            })
    except Exception as e:
        print(f"  ⚠️ {source_name} RSS 失败: {e}")
    return articles

def scrape_html(url, source_name):
    """抓取HTML页面标题作为RSS备选"""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'lxml')
        # 尝试多种标题选择器
        headlines = soup.find_all(['h2', 'h3'], limit=30)
        for h in headlines:
            title = h.get_text(strip=True)
            if len(title) < 20 or not is_semiconductor_related(title):
                continue
            sentiment = classify_sentiment(title)
            articles.append({
                'title': title,
                'source': source_name,
                'url': url,
                'time': datetime.now().strftime('%Y-%m-%d'),
                'sentiment': sentiment,
            })
    except Exception as e:
        print(f"  ⚠️ {source_name} HTML 失败: {e}")
    return articles

def scrape_all():
    """主抓取函数"""
    print(f"\n{'='*60}")
    print(f"📡 SemiWatch 新闻抓取器")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    all_articles = []

    # RSS源
    print("📰 抓取 RSS 源...")
    for url, name in RSS_FEEDS:
        print(f"  → {name}...")
        articles = scrape_rss(url, name)
        all_articles.extend(articles)
        print(f"    获取 {len(articles)} 条半导体相关新闻")

    # HTML备用源
    print("\n🌐 抓取 HTML 源（备用）...")
    for url, name in HTML_SOURCES:
        print(f"  → {name}...")
        articles = scrape_html(url, name)
        all_articles.extend(articles)
        print(f"    获取 {len(articles)} 条半导体相关新闻")

    # 去重（按标题相似度）
    seen = set()
    unique = []
    for a in all_articles:
        key = a['title'][:60]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # 按时间排序
    unique.sort(key=lambda x: x.get('time', ''), reverse=True)

    # 统计
    bulls = sum(1 for a in unique if a['sentiment'] == 'bull')
    bears = sum(1 for a in unique if a['sentiment'] == 'bear')
    neutrals = sum(1 for a in unique if a['sentiment'] == 'neutral')
    total = len(unique)
    bias = round((bulls - bears) / max(total, 1), 2)

    # 构建输出
    output = {
        'generated_at': datetime.now().isoformat(),
        'total': total,
        'bullish': bulls,
        'bearish': bears,
        'neutral': neutrals,
        'bias': bias,
        'articles': unique[:50],  # 最多50条
        'sources_used': [name for _, name in RSS_FEEDS] + [name for _, name in HTML_SOURCES],
    }

    # 写入JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 摘要
    print(f"\n{'='*60}")
    print(f"✅ 抓取完成")
    print(f"📊 总计: {total} 条 | 🟢 {bulls} | 🔴 {bears} | 🟡 {neutrals}")
    print(f"📈 消息偏度: {bias:+.2f} {'🟢 偏正面' if bias > 0.1 else '🔴 偏负面' if bias < -0.1 else '🟡 中性'}")
    print(f"💾 已保存: {OUTPUT_FILE}")
    print(f"{'='*60}\n")

    return output

# ==================== 价格数据服务 ====================
PRICE_FILE = os.path.join(os.path.dirname(__file__), 'price_data.json')
PRICE_SYMBOLS = {
    'SOX': '^SOX', 'VIX': '^VIX', 'KOSPI': '^KS11',
    'SK_Hynix': '000660.KS', 'SKHY': 'SKHY',
    'MU': 'MU', 'MRVL': 'MRVL', 'NVDA': 'NVDA',
    'SMH': 'SMH', 'SOXX': 'SOXX',
}

_price_cache = {}
_last_price_fetch = None

# 价格符号映射到Google Finance
GF_SYMBOLS = {
    'SOX': 'SOX', 'VIX': 'VIX', 'KOSPI': 'KOSPI',
    'SK_Hynix': 'KRX:000660', 'SKHY': 'NASDAQ:SKHY',
    'MU': 'NASDAQ:MU', 'MRVL': 'NASDAQ:MRVL',
    'NVDA': 'NASDAQ:NVDA', 'SMH': 'NYSEARCA:SMH', 'SOXX': 'NASDAQ:SOXX',
}

def fetch_prices():
    """获取实时价格（多源降级）"""
    global _price_cache, _last_price_fetch

    if _last_price_fetch and (datetime.now() - _last_price_fetch).seconds < 30:
        return _price_cache

    result = {}

    # 方法1: yfinance
    try:
        import yfinance as yf
        for name, symbol in PRICE_SYMBOLS.items():
            try:
                t = yf.Ticker(symbol)
                info = t.info
                p = info.get('regularMarketPrice') or info.get('currentPrice')
                prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
                if p and prev:
                    result[name] = _make_quote(p, prev)
                time.sleep(0.08)
            except: pass
        if len(result) >= 3:
            return _save_prices(result)
    except: pass

    # 方法2: 如果yfinance全部失败，返回之前的缓存
    if _price_cache:
        return _price_cache

    # 方法3: 返回空数据
    result['generated_at'] = datetime.now().isoformat()
    result['error'] = 'all sources failed'
    return result

def _make_quote(price, prev):
    chg = price - prev
    return {
        'price': round(price, 2),
        'change': round(chg, 2),
        'changePct': round(chg / prev * 100, 2) if prev else 0,
    }

def _save_prices(result):
    global _price_cache, _last_price_fetch
    result['generated_at'] = datetime.now().isoformat()
    _price_cache = result
    _last_price_fetch = datetime.now()
    with open(PRICE_FILE, 'w') as f:
        json.dump(result, f, indent=2)
    return result

# ==================== 简易HTTP服务 ====================
class APIHandler(SimpleHTTPRequestHandler):
    """自定义Handler，添加API端点"""
    def do_GET(self):
        if self.path == '/api/prices':
            try:
                prices = fetch_prices()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(prices).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path == '/api/news':
            try:
                with open(OUTPUT_FILE, 'r') as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
            except:
                self.send_response(500)
                self.end_headers()
        else:
            super().do_GET()

def serve_http(port=8765):
    """启动简易HTTP服务器"""
    import threading

def serve_http(port=8765):
    """启动简易HTTP服务器"""
    import threading

    # 先运行一次抓取
    scrape_all()
    fetch_prices()

    # 定时抓取（每30分钟）
    def periodic_scrape():
        while True:
            time.sleep(1800)
            print("\n⏰ 定时抓取...")
            scrape_all()
            fetch_prices()

    threading.Thread(target=periodic_scrape, daemon=True).start()

    # HTTP服务
    os.chdir(os.path.dirname(__file__))
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f"\n🌐 HTTP服务已启动: http://localhost:{port}")
    print(f"📈 价格API: http://localhost:{port}/api/prices")
    print(f"📰 新闻API: http://localhost:{port}/api/news")
    print(f"🛑 按 Ctrl+C 停止\n")
    server.serve_forever()

# ==================== CLI入口 ====================
if __name__ == '__main__':
    if '--serve' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8765
        serve_http(port)
    else:
        scrape_all()
