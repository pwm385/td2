# -*- coding: utf-8 -*-
"""英文名 → 中文名映射。

约定：
  1. 不带 ※ 的，是已经核实过的官方简中/通用译名；
  2. 带 ※ 的，是怀疑但不保证准确的译名，界面上会标出来；
  3. 表里都没有的，进「待补全」，页面会提示，绝不悄悄显示英文。
想改名字：直接改本文件或 names.json（后者优先），推送后几分钟生效。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ---------------------------------------------------------------- 品牌
BRAND_NAMES = {
    "5.11 Tactical": "5.11 战术",
    "Airaldi Holdings": "阿尔拉蒂企业",
    "Alps Summit Armament": "阿尔卑斯山峰军事",
    "Alps Summit Armaments": "阿尔卑斯山峰军事",
    "Badger Tuff": "贝哲陶夫",
    "Belstone Armory": "贝尔斯通军火",
    "Ceska Vyroba s.r.o.": "捷克出产自律组织",
    "Ceska Vyroba S.R.O.": "捷克出产自律组织",
    "China Light Industries Corporation": "中国光能工业公司",
    "China Light Industries": "中国光能工业公司",
    "Douglas & Harding": "道格拉斯与哈定企业",
    "Empress International": "女皇国际",
    "Fenris Group AB": "芬里斯集团公司",
    "Gila Guard": "毒蜥守卫队",
    "Golan Gear Ltd": "戈兰装备有限公司",
    "Grupo Sombra S.A.": "影子军团股份有限公司",
    "Habsburg Guard": "哈布斯堡禁卫",
    "Hana-U Corporation": "哈瑙公司",
    "Imminence Armaments": "灾祸装备",
    "Murakami Industries": "村上工业",
    "Overlord Armaments": "霸主军备公司",
    "Petrov Defense Group": "彼得罗夫防御集团",
    "Providence Defense": "天命防御公司",
    "Richter & Kaier GmbH": "李希特与凯萨有限公司",
    "Sokolov Concern": "索寇罗夫企业",
    "Unit Alloys": "联合合金※",
    "Walker, Harris & Co.": "沃克与哈里斯企业",
    "Wyvern Wear": "飞龙纺织",
    "Yaahl Gear": "耶尔装甲",
    "Zwiadowka Sp. z o.o.": "侦察兵",
    "Zwiadowka Sp. z o.o": "侦察兵",
    # 以下为未核实的补充译名
    "Brazos de Arcabuz": "阿卡布兹之臂※",
    "Ember Engine": "余烬引擎※",
    "Legatus S.p.A.": "雷加图斯※",
    "Lengmo": "冷魔※",
    "Palisade Steelworks": "栅栏钢铁厂※",
    "Uzina Getica": "乌兹娜·格蒂卡※",
}

# ---------------------------------------------------------------- 套装
SET_NAMES = {
    "Tipping Scales": "倾斜天平",
    "Ortiz: Exuro": "奥提兹：燃烬",
    "Ortiz Exuro": "奥提兹：燃烬",
    "Ortiz: Reficere": "奥提兹：重塑※",
    "Ortiz Reficere": "奥提兹：重塑※",
    "Aces & Eights": "王牌与八点※",
    "Aegis": "宙斯盾※",
    "Breaking Point": "极限点※",
    "Cavalier": "骑士※",
    "Concentrated Company": "精锐连※",
    "Core Strength": "核心力量※",
    "Eclipse Protocol": "日蚀协议※",
    "Electrique": "电气※",
    "Foundry Bulwark": "铸城壁垒※",
    "Future Initiative": "未来行动※",
    "Hard Wired": "硬连线※",
    "Heartbreaker": "碎心者※",
    "Hotshot": "神枪手※",
    "Hunters Fury": "猎人之怒※",
    "Measured Assembly": "度量装配※",
    "Negotiators Dilemma": "谈判者困境※",
    "Ongoing Directive": "持续指令※",
    "Refactor": "重构※",
    "Rigger": "索具工※",
    "Strikers Battlegear": "突袭者战甲※",
    "Tip of the Spear": "矛尖※",
    "True Patriot": "真爱国者※",
    "Umbra Initiative": "暗影行动※",
    "Urban Lookout": "城市瞭望※",
    "Virtuoso": "名家※",
}

# ---------------------------------------------------------------- 部位
SLOT_NAMES = {
    "Backpack": "背包", "Backpacks": "背包",
    "Body Armor": "护甲", "Chest": "护甲", "Chest Pieces": "护甲",
    "Gloves": "手套", "Glove": "手套",
    "Holster": "枪套", "Holsters": "枪套",
    "Kneepad": "护膝", "Kneepads": "护膝",
    "Mask": "面具", "Masks": "面具",
    "Assault Rifle": "突击步枪", "Assault Rifles": "突击步枪",
    "Rifle": "步枪", "Rifles": "步枪",
    "SMG": "冲锋枪", "SMGs": "冲锋枪",
    "Shotgun": "霰弹枪", "Shotguns": "霰弹枪",
    "LMG": "轻机枪", "LMGs": "轻机枪",
    "MMR": "精确射手步枪", "MMRs": "精确射手步枪",
    "Pistol": "手枪", "Pistols": "手枪",
    "Gear Mods": "装备模块※", "Skill Mods": "技能模块※",
}

# ---------------------------------------------------------------- 任务
MISSION_NAMES = {
    "ViewPoint Museum": "观点博物馆",
    "Coney Island Ballpark": "康尼岛球场",
    "Coney Island Amusement Park": "康尼岛游乐园",
    "Capitol Building": "国会大厦",
    "Potomac Event Center": "波托马克活动中心",
    "Grand Washington Hotel": "华盛顿大酒店",
    "Jefferson Trade Center": "杰斐逊贸易中心",
    "Lincoln Memorial": "林肯纪念堂",
    "American History Museum": "美国历史博物馆",
    "Air & Space Museum": "航空航天博物馆",
    "Space Administration HQ": "太空管理局总部",
    "Federal Emergency Bunker": "联邦紧急掩体",
    "Jefferson Plaza": "杰斐逊广场",
    "Manning National Zoo": "曼宁国家动物园",
    "Camp White Oak": "白橡树营地",
    "The Pentagon": "五角大楼",
    "Tidal Basin": "潮汐盆地",
    "Stranded Tanker": "搁浅油轮",
    "Wall Street": "华尔街",
    "Two Bridges": "双桥",
    "Liberty Island": "自由岛",
    "The Tombs": "坟墓",
    "Bank Headquarters": "银行总部",
    "DARPA Research Labs": "DARPA 研究实验室",
    "DCD Headquarters": "DCD 总部",
    "District Union Arena": "区联盟竞技场",
    "Pathway Park": "路径公园",
    "Roosevelt Island": "罗斯福岛",
    "The Art Museum": "艺术博物馆",
}

# ---------------------------------------------------------------- 阵营
FACTION_NAMES = {
    "Black Tusk": "暗牙", "True Sons": "真实之子", "Hyenas": "鬣狗",
    "Outcasts": "流亡者", "Cleaners": "清洁工", "Rikers": "赖克斯帮",
}

# 图片路径 → 类别（最可靠的分类依据）
SRC_CATEGORY = {
    "/brandsets/": "brand",
    "/gearsets/": "set",
    "/gear/": "slot",
    "/weapons/": "slot",
}

_PUNCT = re.compile(r"[^a-z0-9]+")


def normalize(name: str) -> str:
    return _PUNCT.sub("", (name or "").strip().lower())


def _lookup(table: dict, name: str):
    if name in table:
        return table[name]
    key = normalize(name)
    for en, cn in table.items():
        if normalize(en) == key:
            return cn
    if key.endswith("s"):
        for en, cn in table.items():
            if normalize(en) == key[:-1]:
                return cn
    return None


def _load_override(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k: v for k, v in raw.items() if not k.startswith("_")}
    except Exception:
        return {}


class Resolver:
    def __init__(self, override_path: str | Path | None = None):
        self.override_path = Path(override_path) if override_path else Path(__file__).with_name("names.json")
        self.overrides = _load_override(self.override_path)

    def reload(self):
        self.overrides = _load_override(self.override_path)

    def resolve(self, name: str, src: str | None = None) -> dict:
        """返回 {cn, category, uncertain}。查不到时 cn 为 None、category 为 unknown。"""
        if name in self.overrides:
            cn = self.overrides[name]
            return {"cn": cn, "category": self._guess_category(src), "uncertain": "※" in cn}

        tables = [("brand", BRAND_NAMES), ("set", SET_NAMES), ("slot", SLOT_NAMES)]
        hint = self._guess_category(src)
        if hint:
            order = [t for t in tables if t[0] == hint] + [t for t in tables if t[0] != hint]
        else:
            order = tables
        for cat, table in order:
            cn = _lookup(table, name)
            if cn:
                return {"cn": cn, "category": cat, "uncertain": "※" in cn}
        return {"cn": None, "category": "unknown", "uncertain": False}

    @staticmethod
    def _guess_category(src: str | None) -> str | None:
        if not src:
            return None
        for frag, cat in SRC_CATEGORY.items():
            if frag in src:
                return cat
        return None

    def mission(self, name: str) -> str:
        return MISSION_NAMES.get(name, name)

    def faction(self, name: str | None) -> str:
        if not name:
            return ""
        return FACTION_NAMES.get(name, name)

    def cache_name(self, label: str) -> str:
        if "Gear" in label:
            return "原型装备缓存"
        if "Weapon" in label:
            return "原型武器缓存"
        return label
