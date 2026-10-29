# -*- coding: utf-8 -*-
"""
纯函数解析器：把 prototrack.gg 服务端渲染的 HTML 解析成结构化数据。

本模块不做任何网络请求，输入 HTML 字符串、输出字典，方便用夹具单测。

页面锚点（已对照真实页面确认）：
  任务行   <tr class="[priority-row]"> <td data-label="Mission"> <div class="tl-mission">
             <img class="tl-faction-icon" src=... alt="Black Tusk faction">
             <span>任务名</span></div></td>
           <td data-label="Target Loot"><div class="tl-loot">
             [<span class="priority-mark" aria-label="Priority loot">!</span>]
             <img data-loot="Ortiz: Reficere" src=".../gearsets/xxx.png" ...><span>英文名</span>
           </div></td>
           <td data-label="Loot History"><div class="tl-history">
             <div><span>Appearances</span><strong>12 times</strong></div>
             <div><span>Last seen</span><strong class="tl-last-seen">3 days ago</strong></div>
           </div></td>
  缓存卡   <article class="tl-vendor-card" aria-label="Prototype Gear Cache">
             <span class="tl-cache-type">...</span>
             <div class="tl-loot"><img src="/assets/division2/gear/mask.png" alt=""><span>Masks</span></div>
             <div class="tl-history">…同上…</div>
           </article>
  顶部信息 div.loot-info-bar > div.loot-info-field（Loot date / Rotation week / Last updated / Next reset）
"""
from __future__ import annotations

import re
from datetime import date as date_cls
from datetime import timedelta
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# 相对时间换算（"3 days ago" → 绝对日期）
# ---------------------------------------------------------------------------
_DAYS_AGO_RE = re.compile(r"(?:(\d+)\s+days?\s+ago|yesterday|today)", re.IGNORECASE)


def parse_relative_seen(text: str, loot_date: date_cls) -> str | None:
    """把页面上的相对时间（如 "3 days ago"）按服务端语义换算成绝对日期。

    该相对时间表示「该掉落上次出现的日期距离本次轮换日（loot_date）的天数」，
    因此换算基准是 loot_date。返回 ISO 格式字符串；无法解析返回 None。
    """
    if not text:
        return None
    # 兼容 str（ISO）与 date 对象
    if isinstance(loot_date, str):
        try:
            loot_date = date_cls.fromisoformat(loot_date)
        except ValueError:
            return None
    m = _DAYS_AGO_RE.search(text.strip())
    if not m:
        return None
    if m.group(1) is not None:
        days = int(m.group(1))
        return (loot_date - timedelta(days=days)).isoformat()
    word = m.group(0).lower()
    if word == "today":
        return loot_date.isoformat()
    if word == "yesterday":
        return (loot_date - timedelta(days=1)).isoformat()
    return None


def parse_appearances(text: str) -> int | None:
    """从 "12 times" 这类文本提取数字；解析失败返回 None。"""
    if not text:
        return None
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else None


def parse_date_iso(text: str) -> str | None:
    """规范化 YYYY-MM-DD 或 "28 Oct 2026" 为 ISO 日期。"""
    if not text:
        return None
    text = text.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return text
    # "28 Oct 2026" / "02 Nov 2026" 形式（页面 Rotation week 用）
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", text)
    if m:
        day, mon, year = m.group(1), m.group(2).capitalize(), m.group(3)
        if mon in months:
            return f"{year}-{months[mon]:02d}-{int(day):02d}"
    return None


months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


# ---------------------------------------------------------------------------
# 轻量 DOM 解析（标准库 html.parser，不做任何网络请求）
# ---------------------------------------------------------------------------
class _Elem:
    __slots__ = ("tag", "attrs", "text", "children", "parent")

    def __init__(self, tag: str, attrs: dict):
        self.tag = tag
        self.attrs = attrs
        self.text: list[str] = []
        self.children: list["_Elem"] = []
        self.parent: "_Elem | None" = None

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text_content(self) -> str:
        return " ".join(t for t in self.text if t).strip()

    def find_all(self, tag: str, cls: str | None = None) -> list["_Elem"]:
        """递归查找所有匹配的子元素（深度优先）。"""
        out: list[_Elem] = []
        for c in self.children:
            if c.tag == tag and (cls is None or cls in c.classes):
                out.append(c)
            out.extend(c.find_all(tag, cls))
        return out

    def find(self, tag: str, cls: str | None = None) -> "_Elem | None":
        """递归查找第一个匹配的后代元素（深度优先）。"""
        for c in self.children:
            if c.tag == tag and (cls is None or cls in c.classes):
                return c
            hit = c.find(tag, cls)
            if hit is not None:
                return hit
        return None


class _PageParser(HTMLParser):
    """把页面构建成树，并额外记录 td 的 data-label。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Elem("#root", {})
        self._stack: list[_Elem] = [self.root]

    def _current(self) -> _Elem:
        return self._stack[-1]

    def handle_starttag(self, tag, attrs):
        elem = _Elem(tag, dict(attrs))
        self._current().children.append(elem)
        elem.parent = self._current()
        self._stack.append(elem)

    def handle_startendtag(self, tag, attrs):
        # <img/>、<input/> 等自闭合标签：无文本子节点，直接挂到父级
        elem = _Elem(tag, dict(attrs))
        self._current().children.append(elem)
        elem.parent = self._current()

    def handle_endtag(self, tag):
        if len(self._stack) <= 1:
            return
        # 弹出到匹配的标签（容忍未闭合的标签）
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._stack and data.strip():
            self._stack[-1].text.append(data)


# ---------------------------------------------------------------------------
# 主解析入口
# ---------------------------------------------------------------------------
def parse_escalation(html_text: str) -> dict:
    """解析 prototrack.gg 的 escalation 页面 HTML。

    返回结构：
      {
        "loot_date": "2026-10-28" | None,
        "rotation_week": {"start": "...", "end": "..."} | None,
        "last_updated": "28 Oct · 09:01" | None,
        "missions": [ {kind, name_en, faction, loot_en, loot_src, priority,
                       appearances, last_seen_en, last_seen_date}, ... ],
        "caches":   [ {kind, name_en, loot_en, loot_src, priority,
                       appearances, last_seen_en, last_seen_date}, ... ],
      }
    """
    parser = _PageParser()
    try:
        parser.feed(html_text or "")
        parser.close()
    except Exception:
        # 解析失败抛出，由调用方决定回退缓存；此处保持纯函数语义
        raise
    root = parser.root

    # ---- 顶部信息 ----
    info = {"loot_date": None, "rotation_week": None, "last_updated": None}
    info_bar = root.find("div", "loot-info-bar")
    if info_bar:
        fields = [c for c in info_bar.children if c.tag == "div" and "loot-info-field" in c.classes]
        for f in fields:
            strong = f.find("strong")
            label = f.find("span")
            label_txt = label.text_content() if label else ""
            if "Loot date" in label_txt:
                t = strong.find("time") if strong else None
                if t:
                    info["loot_date"] = parse_date_iso(t.attrs.get("datetime") or t.text_content())
            elif "Rotation week" in label_txt:
                times = strong.find_all("time") if strong else []
                if len(times) >= 2:
                    info["rotation_week"] = {
                        "start": parse_date_iso(times[0].attrs.get("datetime") or times[0].text_content()),
                        "end": parse_date_iso(times[1].attrs.get("datetime") or times[1].text_content()),
                    }
            elif "Last updated" in label_txt:
                if strong:
                    info["last_updated"] = strong.text_content()
            # "Next reset" 由前端按北京时间计算，服务端不需要

    loot_date = info["loot_date"]

    # ---- 任务行 ----
    missions: list[dict] = []
    for tr in root.find_all("tr"):
        td_mission = None
        td_loot = None
        td_history = None
        for td in tr.children:
            if td.tag != "td":
                continue
            label = td.attrs.get("data-label")
            if label == "Mission":
                td_mission = td
            elif label == "Target Loot":
                td_loot = td
            elif label == "Loot History":
                td_history = td
        if td_mission is None:
            continue  # 不是任务行

        # 阵营 + 任务名（tl-mission 内：faction img alt + 末尾 span）
        faction = None
        mission_name = None
        mission_div = td_mission.find("div", "tl-mission")
        if mission_div:
            for img in mission_div.find_all("img"):
                alt = (img.attrs.get("alt") or "").strip()
                if alt.endswith("faction") and alt[:-7].strip():
                    faction = alt[:-7].strip()
            for sp in mission_div.find_all("span"):
                txt = sp.text_content()
                if txt:
                    mission_name = txt

        # 掉落：tl-loot 内 data-loot 属性 / src / 文本 / priority-mark
        loot_en = None
        loot_src = None
        priority = False
        loot_div = td_loot.find("div", "tl-loot") if td_loot else None
        if loot_div:
            for sp in loot_div.children:
                if sp.tag == "span" and "priority-mark" in sp.classes:
                    priority = True
            for img in loot_div.find_all("img"):
                dl = img.attrs.get("data-loot")
                if dl:
                    loot_en = dl.strip()
                src = img.attrs.get("src") or ""
                if src:
                    loot_src = src
            for sp in loot_div.find_all("span"):
                if loot_en is None:
                    txt = sp.text_content()
                    if txt:
                        loot_en = txt

        # 历史：appearances / last seen
        appearances = None
        last_seen_en = None
        last_seen_date = None
        hist_div = td_history.find("div", "tl-history") if td_history else None
        if hist_div:
            for item in hist_div.find_all("div"):
                strong = item.find("strong")
                if not strong:
                    continue
                label_sp = item.find("span")
                label_txt = label_sp.text_content() if label_sp else ""
                strong_txt = strong.text_content()
                if "Appearances" in label_txt:
                    appearances = parse_appearances(strong_txt)
                elif "Last seen" in label_txt or "tl-last-seen" in strong.classes:
                    last_seen_en = strong_txt
                    if loot_date:
                        last_seen_date = parse_relative_seen(last_seen_en, loot_date)

        missions.append({
            "kind": "mission",
            "name_en": mission_name,
            "faction_en": faction,
            "loot_en": loot_en,
            "loot_src": loot_src,
            "priority": priority,
            "appearances": appearances,
            "last_seen_en": last_seen_en,
            "last_seen_date": last_seen_date,
        })

    # ---- 每日缓存卡 ----
    caches: list[dict] = []
    for art in root.find_all("article", "tl-vendor-card"):
        cache_name = art.attrs.get("aria-label")
        loot_en = None
        loot_src = None
        priority = False
        loot_div = art.find("div", "tl-loot")
        if loot_div:
            for img in loot_div.find_all("img"):
                dl = img.attrs.get("data-loot")
                if dl:
                    loot_en = dl.strip()
                src = img.attrs.get("src") or ""
                if src:
                    loot_src = src
            for sp in loot_div.find_all("span"):
                if loot_en is None:
                    txt = sp.text_content()
                    if txt:
                        loot_en = txt
        appearances = None
        last_seen_en = None
        last_seen_date = None
        hist_div = art.find("div", "tl-history")
        if hist_div:
            for item in hist_div.find_all("div"):
                strong = item.find("strong")
                if not strong:
                    continue
                label = item.find_all("span")
                label_txt = label[0].text_content() if label else ""
                strong_txt = strong.text_content()
                if "Appearances" in label_txt:
                    appearances = parse_appearances(strong_txt)
                elif "Last seen" in label_txt or "tl-last-seen" in strong.classes:
                    last_seen_en = strong_txt
                    if loot_date:
                        last_seen_date = parse_relative_seen(last_seen_en, loot_date)
        caches.append({
            "kind": "cache",
            "name_en": cache_name,
            "faction_en": None,
            "loot_en": loot_en,
            "loot_src": loot_src,
            "priority": priority,
            "appearances": appearances,
            "last_seen_en": last_seen_en,
            "last_seen_date": last_seen_date,
        })

    return {"loot_date": loot_date, "rotation_week": info["rotation_week"],
            "last_updated": info["last_updated"], "missions": missions, "caches": caches}