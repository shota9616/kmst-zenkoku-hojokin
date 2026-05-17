#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週次補助金ウォッチ — Jグランツ API 一次ソース版
JグランツAPIで「システム投資・AI領域」の新着公募を取得し、
既存カタログ(data.js)との差分だけを追記する。
依存: 標準ライブラリのみ（urllib）。GitHub Actions上で実行。
"""
import json, re, sys, time, datetime, urllib.parse, urllib.request

ROOT = __file__.rsplit("/scripts/", 1)[0]
DATA_JS = f"{ROOT}/data.js"
RESULT_JSON = f"{ROOT}/scripts/watch_result.json"

# 直近この日数以内に募集開始した補助金を「新着」とみなす
WINDOW_DAYS = 14
# システム投資・AI領域の検索キーワード
KEYWORDS = ["AI", "DX", "デジタル", "IT導入", "システム", "省力化",
            "クラウド", "ロボット", "業務効率化", "生産性向上", "ICT"]

SEARCH_URL = "https://api.jgrants-portal.go.jp/exp/v1/public/subsidies"
DETAIL_URL = "https://api.jgrants-portal.go.jp/exp/v2/public/subsidies/id/"

PREF_REGION = {
    "北海道": "北海道",
    "青森県": "東北", "岩手県": "東北", "宮城県": "東北", "秋田県": "東北",
    "山形県": "東北", "福島県": "東北", "新潟県": "東北",
    "茨城県": "関東", "栃木県": "関東", "群馬県": "関東", "埼玉県": "関東",
    "千葉県": "関東", "東京都": "関東", "神奈川県": "関東",
    "富山県": "中部", "石川県": "中部", "福井県": "中部", "山梨県": "中部",
    "長野県": "中部", "岐阜県": "中部", "静岡県": "中部", "愛知県": "中部", "三重県": "中部",
    "滋賀県": "関西", "京都府": "関西", "大阪府": "関西", "兵庫県": "関西",
    "奈良県": "関西", "和歌山県": "関西",
    "鳥取県": "中国", "島根県": "中国", "岡山県": "中国", "広島県": "中国", "山口県": "中国",
    "徳島県": "四国", "香川県": "四国", "愛媛県": "四国", "高知県": "四国",
    "福岡県": "九州", "佐賀県": "九州", "長崎県": "九州", "熊本県": "九州",
    "大分県": "九州", "宮崎県": "九州", "鹿児島県": "九州", "沖縄県": "沖縄",
}

USE_KEYWORDS = {
    "AI研修": ["研修", "人材育成", "リスキリング", "スキル", "訓練", "教育", "人材開発", "学び直し"],
    "広告": ["広告", "プロモーション", "PR"],
    "販促": ["販路", "展示会", "出展", "販売促進", "EC", "マーケティング", "ブランディング", "商談会"],
}


def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kmst-subsidy-watch"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                print(f"[warn] fetch失敗: {url} -> {e}", file=sys.stderr)
                return None
            time.sleep(2)
    return None


def search_keyword(kw):
    q = urllib.parse.quote(kw)
    url = f"{SEARCH_URL}?keyword={q}&sort=created_date&order=DESC&acceptance=1"
    d = fetch_json(url)
    return (d or {}).get("result", []) if d else []


def fetch_detail(sid):
    d = fetch_json(DETAIL_URL + sid)
    res = (d or {}).get("result", []) if d else []
    return res[0] if res else None


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def region_of(area):
    if not area:
        return "全国"
    if "全国" in area:
        return "全国"
    for pref, reg in PREF_REGION.items():
        if pref in area:
            return reg
    return "全国"


def fmt_amount(yen):
    try:
        yen = int(yen)
    except Exception:
        return "未確認"
    if yen <= 0:
        return "未確認"
    if yen >= 100000000:
        oku = yen / 100000000
        return f"{oku:.1f}".rstrip("0").rstrip(".") + "億円"
    man = yen // 10000
    return f"{man:,}万円"


def classify_uses(text):
    uses = []
    for u, kws in USE_KEYWORDS.items():
        if any(k in text for k in kws):
            uses.append(u)
    if "system投資" not in uses:
        uses.insert(0, "system投資")  # 当ウォッチは常にシステム投資軸
    return uses


def slugify(jid):
    return "jgrants-" + jid.lower().replace("_", "-")


def as_text(v):
    """jGrantsのフィールドを安全に文字列化。dict（添付ファイル等）は空にする。"""
    if v is None:
        return ""
    if isinstance(v, dict):
        return ""  # 添付ファイルオブジェクト等はテキストとして扱わない
    if isinstance(v, list):
        parts = [as_text(x) for x in v]
        return " ".join(p for p in parts if p)
    return str(v)


# システム投資・AI領域の判定用語（補助金タイトルにこれが無ければ対象外）。
# jGrantsのuse_purposeには汎用的に「AI・IoT活用」分類が付くため、判定はタイトルのみで行う。
CORE_TERMS = ["AI", "ＡＩ", "DX", "ＤＸ", "デジタル", "IT", "ＩＴ", "システム",
              "クラウド", "ロボット", "IoT", "ＩｏＴ", "省力化", "自動化", "情報化",
              "ICT", "ＩＣＴ", "テレワーク", "ソフトウェア", "電子化", "スマート", "DX化"]
# IT投資の原資になりやすい汎用支援系（タイトルにこれがあれば対象に含める）
GENERAL_TERMS = ["生産性向上", "経営改善", "賃上げ環境", "競争力強化", "業務改善",
                 "業務効率", "効率化", "省人化", "人材育成", "リスキリング", "販路開拓"]


def load_catalog():
    with open(DATA_JS, encoding="utf-8") as f:
        txt = f.read()
    m = re.search(r"const data=\[(.*?)\n\];", txt, re.S)
    if not m:
        raise SystemExit("data.js の data 配列が見つかりません")
    arr = json.loads("[" + m.group(1) + "\n]")
    return txt, m, arr


def norm_name(s):
    s = re.sub(r"\s+", "", s or "")
    s = re.sub(r"令和\d+年度|令和\d+年|\d{4}年度|（第\d+[回次]）|第\d+[回次]", "", s)
    return s


def main():
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=WINDOW_DAYS)
    txt, m, catalog = load_catalog()

    existing_jids = {d.get("jgrants_id") for d in catalog if d.get("jgrants_id")}
    existing_names = {norm_name(d.get("name", "")) for d in catalog}

    # 1. キーワード検索で候補収集（idで重複排除）
    seen, candidates = set(), []
    for kw in KEYWORDS:
        for r in search_keyword(kw):
            sid = r.get("id")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            candidates.append(r)
        time.sleep(0.5)
    print(f"[info] Jグランツ候補(受付中): {len(candidates)}件")

    # 2. 直近WINDOW_DAYS以内に募集開始 かつ 既存カタログに無いものを抽出
    new_entries = []
    for r in candidates:
        start = parse_dt(r.get("acceptance_start_datetime"))
        if not start or start < cutoff:
            continue
        jid = r.get("name", "")  # S-xxxxxxxx
        if jid in existing_jids:
            continue
        if norm_name(r.get("title", "")) in existing_names:
            continue
        det = fetch_detail(r["id"])
        time.sleep(0.4)
        title = as_text((det or {}).get("title")) or as_text(r.get("title"))
        area = as_text(r.get("target_area_search"))
        outline = as_text((det or {}).get("outline_of_grant"))
        catch = as_text((det or {}).get("subsidy_catch_phrase"))
        # 正のフィルタ: タイトルにコア用語/汎用支援用語が無ければシステム・AI領域外として除外
        if not any(t in title for t in CORE_TERMS + GENERAL_TERMS):
            continue
        summary = (catch or outline).strip().replace("\n", " ").replace("\r", " ")
        summary = re.sub(r"\s+", " ", summary)
        if len(summary) > 90:
            summary = summary[:88] + "…"
        entry = {
            "slug": slugify(jid or r["id"]),
            "name": title,
            "scope": "国(Jグランツ)" if region_of(area) == "全国" else area.split("/")[0],
            "category": as_text((det or {}).get("institution_name")) or ("国(Jグランツ)" if region_of(area) == "全国" else area.split("/")[0]),
            "region": region_of(area),
            "industry": "全業種",
            "uses": classify_uses(title),
            "max": fmt_amount(r.get("subsidy_max_limit")),
            "rate": (as_text((det or {}).get("subsidy_rate")).strip() or "未確認"),
            "deadline": (str(parse_dt(r.get("acceptance_end_datetime"))) if parse_dt(r.get("acceptance_end_datetime")) else "未確認"),
            "url": (det or {}).get("front_subsidy_detail_page_url") or f"https://www.jgrants-portal.go.jp/subsidy/{r['id']}",
            "summary": summary or "Jグランツ掲載の補助金。詳細は公式ページを参照。",
            "detail": "",
            "added": str(today),
            "jgrants_id": jid,
        }
        new_entries.append(entry)

    print(f"[info] 真の新着(差分): {len(new_entries)}件")

    # 3. data.js へ追記
    if new_entries:
        merged = catalog + new_entries
        lines = [json.dumps(d, ensure_ascii=False, separators=(",", ":")) for d in merged]
        new_block = "const data=[\n" + ",\n".join(lines) + "\n];"
        new_txt = txt[:m.start()] + new_block + txt[m.end():]
        # 検証
        vm = re.search(r"const data=\[(.*?)\n\];", new_txt, re.S)
        json.loads("[" + vm.group(1) + "\n]")
        with open(DATA_JS, "w", encoding="utf-8") as f:
            f.write(new_txt)
        print(f"[info] data.js 更新: {len(catalog)} -> {len(merged)}件")
        total = len(merged)
    else:
        total = len(catalog)

    # 4. 結果サマリー出力（GitHub Actionsが読む）
    def deadline_key(e):
        return e["deadline"] if re.match(r"\d{4}-\d{2}-\d{2}", e["deadline"]) else "9999"
    highlights = sorted(new_entries, key=deadline_key)[:3]
    result = {
        "date": str(today),
        "added_count": len(new_entries),
        "total_count": total,
        "highlights": [{"name": e["name"], "deadline": e["deadline"]} for e in highlights],
    }
    with open(RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("[info] watch_result.json 出力完了")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
