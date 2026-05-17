#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watch_result.json を読み、Discord Webhook に週次結果を通知する。"""
import json, os, sys, urllib.request

ROOT = __file__.rsplit("/scripts/", 1)[0]
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

if not WEBHOOK:
    print("[warn] DISCORD_WEBHOOK_URL 未設定。通知をスキップ。", file=sys.stderr)
    sys.exit(0)

try:
    with open(f"{ROOT}/scripts/watch_result.json", encoding="utf-8") as f:
        r = json.load(f)
except Exception as e:
    print(f"[warn] watch_result.json 読込失敗: {e}", file=sys.stderr)
    sys.exit(0)

date = r.get("date", "")
added = r.get("added_count", 0)
total = r.get("total_count", 0)
highlights = r.get("highlights", [])

if added > 0:
    lines = [
        f"【KMST補助金ウォッチ】カタログを更新しました（{date}）",
        f"今週の新着: {added}件をマスターカタログに追記",
        f"カタログ総件数: {total}件",
    ]
    if highlights:
        h = highlights[0]
        lines.append(f"締切が近い新着: {h['name'][:36]}（{h['deadline']}）")
    lines.append("カタログ: https://kmst-zenkoku-hojokin.vercel.app/")
    content = "\n".join(lines)
else:
    content = (f"【KMST補助金ウォッチ】今週は対象となる新着公募はありませんでした（{date}）\n"
               f"カタログ総件数: {total}件 / https://kmst-zenkoku-hojokin.vercel.app/")

req = urllib.request.Request(
    WEBHOOK,
    data=json.dumps({"content": content}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(f"[info] Discord通知 完了 (HTTP {resp.status})")
except Exception as e:
    print(f"[error] Discord通知失敗: {e}", file=sys.stderr)
    sys.exit(1)
