#!/bin/bash
# SemiWatch 备份脚本 — 每次大改动前运行
BACKUP_DIR="$HOME/Desktop/dev/.backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp semiconductor-dashboard.html "$BACKUP_DIR/dashboard_$TIMESTAMP.html"
cp -r *.html "$BACKUP_DIR/charts_$TIMESTAMP/" 2>/dev/null
echo "✅ 备份已保存: $BACKUP_DIR/dashboard_$TIMESTAMP.html"
echo "   图表文件: $BACKUP_DIR/charts_$TIMESTAMP/"
ls "$BACKUP_DIR/" | tail -3
