# -*- coding: utf-8 -*-
"""抓取 prototrack.gg 的恶化定向掉落，生成 data/YYYY-MM-DD.json。

用法：
    python scripts/fetch.py                 # 抓今天
    python scripts/fetch.py --date 2026-10-20
    python scripts/fetch.py --days 30       # 补抓最近 30 天（间隔 2 秒）
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_parser  # noqa: E402
from names import Resolver  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE_URL = "https://prototrack.gg/target-loot/target-loot.php?view=escalation"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    return datetime.now(CST)


def fetch_html(date: str | None, retries: int = 2) -> str:
    url = BASE_URL + (f"&date={date}" if date else "")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    last = None
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:                      # noqa: BLE001
            last = e
            if i < retries:
                time.sleep(3 * (i + 1))
    raise RuntimeError(f"抓取失败: {last}")


def build_day(html: str, resolver: Resolver) -> dict:
    parsed = page_parser.parse_escalation(html)
    if not parsed.get("missions"):
        raise RuntimeError("解析结果为空，可能是源站改版或页面异常")

    unknown: list[str] = []

    def row_base(item: dict) -> dict:
        res = resolver.resolve(item.get("loot_en"), item.get("loot_src"))
        if res["cn"] is None and item.get("loot_en"):
            unknown.append(item["loot_en"])
        return {
            "loot_en": item.get("loot_en"),
            "loot_cn": res["cn"],
            "category": res["category"],
            "uncertain": res["uncertain"],
            "appearances": item.get("appearances"),
            "last_seen": item.get("last_seen_date"),
            "last_seen_en": item.get("last_seen_en"),
            "priority": bool(item.get("priority")),
        }

    missions = []
    for m in parsed["missions"]:
        row = row_base(m)
        row.update({
            "mission": m.get("name_en"),
            "mission_cn": resolver.mission(m.get("name_en") or ""),
            "faction": m.get("faction_en"),
            "faction_cn": resolver.faction(m.get("faction_en")),
        })
        missions.append(row)

    caches = []
    for c in parsed["caches"]:
        row = row_base(c)
        row.update({
            "name": c.get("name_en"),
            "name_cn": resolver.cache_name(c.get("name_en") or ""),
        })
        caches.append(row)

    return {
        "date": parsed.get("loot_date"),
        "fetched_at": beijing_now().isoformat(timespec="seconds"),
        "updated": parsed.get("last_updated"),
        "rotation_week": parsed.get("rotation_week"),
        "missions": missions,
        "caches": caches,
        "unknown_names": sorted(set(unknown)),
    }


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def restamp(day: dict, resolver: Resolver) -> bool:
    """用当前名字表重新解析历史数据（改了 names.py 后无需重新抓取）。"""
    changed = False
    unknown = []
    for row in (day.get("missions") or []) + (day.get("caches") or []):
        res = resolver.resolve(row.get("loot_en"))
        if res["cn"] and res["cn"] != row.get("loot_cn"):
            row["loot_cn"] = res["cn"]
            row["category"] = res["category"]
            row["uncertain"] = res["uncertain"]
            changed = True
        if row.get("loot_cn") is None and row.get("loot_en"):
            unknown.append(row["loot_en"])
    if sorted(set(unknown)) != (day.get("unknown_names") or []):
        day["unknown_names"] = sorted(set(unknown))
        changed = True
    return changed


def rebuild_index(resolver: Resolver | None = None) -> None:
    """根据 data/ 下的日文件，重建 index.json 和 items.json。"""
    DATA.mkdir(parents=True, exist_ok=True)
    resolver = resolver or Resolver()
    days = []
    for f in sorted(DATA.glob("????-??-??.json"), reverse=True):
        try:
            day = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                            # noqa: BLE001
            continue
        if restamp(day, resolver):
            write_json(f, day)
        days.append(day)

    days.sort(key=lambda d: d.get("date") or "", reverse=True)
    index = {
        "latest": days[0].get("date") if days else None,
        "dates": [d.get("date") for d in days if d.get("date")],
        "updated_at": beijing_now().isoformat(timespec="seconds"),
    }

    items: dict[str, dict] = {}
    for d in sorted(days, key=lambda x: x.get("date") or ""):
        for row in (d.get("missions") or []) + (d.get("caches") or []):
            en = row.get("loot_en")
            if not en:
                continue
            it = items.setdefault(en, {
                "loot_en": en,
                "loot_cn": row.get("loot_cn"),
                "category": row.get("category"),
                "dates": [],
            })
            if row.get("loot_cn") and not it.get("loot_cn"):
                it["loot_cn"] = row["loot_cn"]
            it["dates"].append({"date": d.get("date"), "appearances": row.get("appearances")})

    write_json(DATA / "index.json", index)
    write_json(DATA / "items.json", {"items": sorted(items.values(), key=lambda x: -len(x["dates"]))})


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定日期 YYYY-MM-DD（源站支持回溯时才有数据）")
    ap.add_argument("--days", type=int, default=0, help="补抓最近 N 天")
    ap.add_argument("--rebuild-only", action="store_true", help="不抓取，只按新名字表重建索引")
    args = ap.parse_args()

    if args.rebuild_only:
        rebuild_index()
        print("已重建 index.json / items.json")
        return 0

    resolver = Resolver()
    targets: list[str | None]
    if args.days:
        today = beijing_now().date()
        targets = [(today - timedelta(days=i)).isoformat() for i in range(args.days)]
    else:
        targets = [args.date]

    written = 0
    skipped = 0
    for i, day in enumerate(targets):
        if i:
            time.sleep(2)
        if day:
            path = DATA / f"{day}.json"
            if path.exists():
                print(f"[跳过] {day} 已存在")
                skipped += 1
                continue
        try:
            html = fetch_html(day)
            data = build_day(html, resolver)
        except Exception as e:                       # noqa: BLE001
            print(f"[失败] {day or 'today'}: {e}", file=sys.stderr)
            continue
        out_date = data.get("date") or day or beijing_now().date().isoformat()
        data["date"] = out_date
        write_json(DATA / f"{out_date}.json", data)
        written += 1
        miss = " 待补全:" + ",".join(data["unknown_names"]) if data["unknown_names"] else ""
        print(f"[OK] {out_date}  任务 {len(data['missions'])}  缓存 {len(data['caches'])}{miss}")

    rebuild_index()
    print(f"完成，写入 {written} 天，共 {len(list(DATA.glob('????-??-??.json')))} 天数据")
    return 0 if (written or skipped) else 1


if __name__ == "__main__":
    raise SystemExit(main())
