# 全国補助金カタログ ＆ 週次自動ウォッチ

中小企業が「システム投資・AI領域」に活用できる全国の補助金・助成金カタログ。
公開URL: https://kmst-zenkoku-hojokin.vercel.app/

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | カタログ表示（用途/エリア/自治体/業種の4軸フィルタ・NEWバッジ） |
| `data.js` | カタログデータ本体（`const data=[...]`・単一の真実のソース） |
| `reports/` | 主要補助金の詳細レポート（個別HTML） |
| `scripts/weekly_watch.py` | Jグランツ API で新着を取得し data.js に差分追記 |
| `scripts/notify_discord.py` | 週次結果を Discord に通知 |
| `.github/workflows/weekly-watch.yml` | 毎週月曜の自動実行ワークフロー |

## 週次自動ウォッチの仕組み

GitHub Actions が毎週月曜 8:00（マレーシア時間 / 0:00 UTC）に自動実行:

1. **Jグランツ API**（`api.jgrants-portal.go.jp`）から受付中の補助金を取得
2. システム・AI領域の関連語を含む補助金のうち、直近14日以内に募集開始したものを抽出
3. `data.js` の既存エントリと照合し、**真の新着だけ**を差分追記（`added` 日付付き）
4. 変更があれば `data.js` をコミット → Vercel 本番デプロイ
5. Discord に結果を通知

データ取得・差分・デプロイは全て機械処理（Jグランツの構造化データを使用）。

## 必要な GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で以下を登録:

| Secret 名 | 内容 | 取得先 |
|---|---|---|
| `VERCEL_TOKEN` | Vercel デプロイ用トークン | https://vercel.com/account/tokens |
| `DISCORD_WEBHOOK_URL` | 通知先 Discord Webhook URL | Discordチャンネル設定 → 連携サービス → ウェブフック |

## 手動実行

GitHub の Actions タブ → 「Weekly Subsidy Watch」→ 「Run workflow」。

## 補足

- Jグランツ未登録の市区町村レベルの補助金は本ウォッチの対象外（定期的な手動深掘り調査で補完）。
- カタログは追記方式。締切切れエントリの整理は別途実施。
