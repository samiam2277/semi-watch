#!/bin/bash
# ==========================================
# SemiWatch 一键启动脚本
# 用法: bash start.sh
# ==========================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  📡 SemiWatch 半导体监控面板"
echo "  ============================"
echo ""

# 启动新闻抓取HTTP服务（后台）
echo "🔄 启动新闻抓取器（后台，端口8765）..."
cd "$SCRIPT_DIR/scraper"
python3 news_scraper.py --serve &
SCRAPER_PID=$!
sleep 3

# 打开仪表盘
echo "🌐 打开监控面板..."
DASHBOARD="$SCRIPT_DIR/semiconductor-dashboard.html"
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$DASHBOARD"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$DASHBOARD"
fi

echo ""
echo "  ✅ 服务已启动"
echo "  📊 面板: $DASHBOARD"
echo "  📰 新闻API: http://localhost:8765/news_data.json"
echo "  🛑 停止: kill $SCRAPER_PID"
echo ""
echo "  按 Ctrl+C 停止所有服务"

trap "kill $SCRAPER_PID 2>/dev/null; echo '  👋 已停止'; exit 0" INT
wait
