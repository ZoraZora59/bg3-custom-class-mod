#!/usr/bin/env python3
"""职业 mod 源目录的静态校验（Mac 侧，打包前的兜底；不能替代 Toolkit / 游戏内验证）。

用法：python3 scripts/check_mod.py <Source 目录>   （Source 下应有 Mods/<Folder> 与 Public/<Folder>）

检查项（依据 docs/04、docs/02）：
  E1 所有 .lsx / .xml 可解析
  E2 meta.lsx：Folder 与 Mods/<Folder>、Public/<Folder> 目录名一致；Name 不含 "-b"；UUID/Version64 可解析
  E3 UUID 全局唯一（所有 lsx 的 attribute id="UUID"）
  E4 每个基础职业（无 ParentGuid）的 ProgressionTableUUID 有 Level 1 的 Progression 节点；子职业至少有一个节点
  E5 Progression 的 SubClasses/SubClass.Object 指向存在的 ClassDescription，且其 ParentGuid 指向该进阶表所属职业
  E6 lsx 与 stats txt 里引用的本地化 handle 在 English 本地化中存在（其它语言缺失只警告）
  W1 Selectors 引用的列表 UUID 不在本 mod 的 Lists 中（可能是原版列表，需人工确认）
  W2 PassivesAdded 引用的被动不在本 mod 的 Passive.txt 中（可能是原版被动）
  W3 ClassEquipment 在 Equipment.txt 中不存在
退出码：有 E 级错误 → 1，否则 0。
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HANDLE_IN_TXT = re.compile(r'data\s+"(?:DisplayName|Description|ExtraDescription|ShortDescription|TooltipUpcastDescription)"\s+"([^";]+)(?:;\d+)?"')
NEW_ENTRY = re.compile(r'^new entry "([^"]+)"', re.M)
NEW_EQUIPMENT = re.compile(r'^new equipment "([^"]+)"', re.M)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def walk(root: str, exts: set[str]) -> list[str]:
    out = []
    for dp, _, names in os.walk(root):
        for n in names:
            if os.path.splitext(n)[1].lower() in exts:
                out.append(os.path.join(dp, n))
    return sorted(out)


def attrs(node: ET.Element) -> dict[str, str]:
    d = {}
    for a in node.findall("attribute"):
        d[a.get("id", "")] = a.get("value", a.get("handle", ""))
    return d


def main(src: str) -> int:
    src = os.path.abspath(src)
    mods_dir, public_dir = os.path.join(src, "Mods"), os.path.join(src, "Public")
    if not os.path.isdir(mods_dir):
        err(f"缺少目录 {mods_dir}")
        return report()

    # E1 解析所有 lsx/xml
    trees: dict[str, ET.ElementTree] = {}
    for f in walk(src, {".lsx", ".xml"}):
        try:
            trees[f] = ET.parse(f)
        except ET.ParseError as e:
            err(f"E1 XML 解析失败 {rel(src, f)}: {e}")

    # E2 meta.lsx
    folders = [d for d in os.listdir(mods_dir) if os.path.isdir(os.path.join(mods_dir, d))]
    for folder in folders:
        meta = os.path.join(mods_dir, folder, "meta.lsx")
        if meta not in trees:
            err(f"E2 {rel(src, meta)} 不存在或无法解析")
            continue
        mi = trees[meta].getroot().find(".//node[@id='ModuleInfo']")
        if mi is None:
            err(f"E2 {rel(src, meta)} 缺少 ModuleInfo 节点")
            continue
        a = attrs(mi)
        if a.get("Folder") != folder:
            err(f"E2 meta.lsx Folder='{a.get('Folder')}' 与目录名 '{folder}' 不一致")
        if not os.path.isdir(os.path.join(public_dir, folder)):
            warn(f"E2 Public/{folder} 不存在（纯本地化/UI mod 可忽略）")
        if "-b" in a.get("Name", ""):
            err(f"E2 meta.lsx Name '{a.get('Name')}' 含 '-b'，社区记录会导致 mod 不加载")
        if not GUID.fullmatch(a.get("UUID", "")):
            err(f"E2 meta.lsx UUID 非法：{a.get('UUID')}")
        try:
            int(a.get("Version64", "x"))
        except ValueError:
            err(f"E2 meta.lsx Version64 非整数：{a.get('Version64')}")

    # 收集 UUID、ClassDescriptions、Progressions、Lists
    all_uuids: Counter = Counter()
    uuid_where: dict[str, list[str]] = defaultdict(list)
    classes: dict[str, dict] = {}
    progressions: list[dict] = []
    list_uuids: set[str] = set()
    handles_used: dict[str, list[str]] = defaultdict(list)
    for f, t in trees.items():
        if not f.endswith(".lsx"):
            continue
        root = t.getroot()
        for node in root.iter("node"):
            a = attrs(node)
            if "UUID" in a and node.get("id") not in ("ModuleShortDesc",):
                all_uuids[a["UUID"]] += 1
                uuid_where[a["UUID"]].append(f"{rel(src, f)}:{node.get('id')}")
            if node.get("id") == "ClassDescription":
                classes[a.get("UUID", "")] = {**a, "_file": rel(src, f)}
            elif node.get("id") == "Progression":
                subs = [attrs(s).get("Object", "") for s in node.findall("./children/node[@id='SubClasses']/children/node[@id='SubClass']")]
                progressions.append({**a, "_subs": subs, "_file": rel(src, f)})
            elif node.get("id") in ("SkillList", "AbilityList", "SpellList", "PassiveList", "EquipmentList"):
                list_uuids.add(a.get("UUID", ""))
            for at in node.findall("attribute"):
                if at.get("type") == "TranslatedString" and at.get("handle"):
                    handles_used[at.get("handle")].append(rel(src, f))

    # E3 UUID 唯一
    for u, c in all_uuids.items():
        if c > 1:
            err(f"E3 UUID {u} 重复 {c} 次：{', '.join(uuid_where[u])}")

    # E4/E5 职业与进阶表
    by_table: dict[str, list[dict]] = defaultdict(list)
    for p in progressions:
        by_table[p.get("TableUUID", "")].append(p)
    for cu, c in classes.items():
        table = c.get("ProgressionTableUUID", "")
        nodes = by_table.get(table, [])
        if not nodes:
            err(f"E4 {c.get('Name')} 的 ProgressionTableUUID {table} 没有任何 Progression 节点")
        elif not c.get("ParentGuid") and not any(p.get("Level") == "1" and p.get("IsMulticlass", "false").lower() != "true" for p in nodes):
            err(f"E4 基础职业 {c.get('Name')} 缺少 Level 1（非多职业）的 Progression 节点，角色创建不会显示它")
        if c.get("ParentGuid") and c["ParentGuid"] not in classes:
            err(f"E5 子职业 {c.get('Name')} 的 ParentGuid {c['ParentGuid']} 不是本 mod 的 ClassDescription（若指向原版职业请人工确认）")
    table_owner = {c.get("ProgressionTableUUID"): cu for cu, c in classes.items()}
    for p in progressions:
        owner = table_owner.get(p.get("TableUUID", ""))
        for s in p["_subs"]:
            if s not in classes:
                err(f"E5 {p['_file']} Level {p.get('Level')} 的 SubClass {s} 不存在于 ClassDescriptions")
            elif owner and classes[s].get("ParentGuid") != owner:
                err(f"E5 SubClass {classes[s].get('Name')} 的 ParentGuid 不指向进阶表所属职业 {classes[owner].get('Name')}")
        for m in re.finditer(r"(Select\w+|AddSpells)\(([^,)]+)", p.get("Selectors", "")):
            ref = m.group(2).strip()
            if GUID.fullmatch(ref) and ref not in list_uuids:
                warn(f"W1 {p['_file']} Level {p.get('Level')} {m.group(1)} 引用列表 {ref} 不在本 mod Lists 中（原版列表？请确认）")

    # stats txt
    passives: set[str] = set()
    equipment: set[str] = set()
    for f in walk(public_dir, {".txt"}) if os.path.isdir(public_dir) else []:
        with open(f, encoding="utf-8", errors="replace") as fh:
            s = fh.read()
        if os.path.basename(f).lower() == "passive.txt":
            passives.update(NEW_ENTRY.findall(s))
        if os.path.basename(f).lower() == "equipment.txt":
            equipment.update(NEW_EQUIPMENT.findall(s))
        for h in HANDLE_IN_TXT.findall(s):
            handles_used[h].append(rel(src, f))
    for p in progressions:
        for name in filter(None, re.split(r"[;,]\s*", p.get("PassivesAdded", ""))):
            if name not in passives:
                warn(f"W2 {p['_file']} Level {p.get('Level')} PassivesAdded '{name}' 不在本 mod Passive.txt（原版被动？请确认）")
    for c in classes.values():
        eq = c.get("ClassEquipment")
        if eq and eq not in equipment:
            warn(f"W3 ClassEquipment '{eq}' 不在本 mod Equipment.txt 中")

    # E6 本地化
    loca: dict[str, set[str]] = defaultdict(set)
    for f, t in trees.items():
        if "Localization" in f.split(os.sep) and f.endswith(".xml"):
            lang = f.split(os.sep)[f.split(os.sep).index("Localization") + 1]
            for c in t.getroot().iter("content"):
                loca[lang].add(c.get("contentuid", ""))
    if not loca:
        err("E6 没有找到任何 Localization/<Language>/*.xml")
    else:
        english = loca.get("English", set())
        for h, where in handles_used.items():
            if h == "ls::TranslatedStringRepository::s_HandleUnknown":
                err(f"E6 出现 s_HandleUnknown（先建本地化再填 DisplayName）：{where[0]}")
            elif h not in english:
                err(f"E6 handle {h} 在 English 本地化中不存在（引用于 {where[0]}）")
            for lang, hs in loca.items():
                if lang != "English" and h not in hs:
                    warn(f"W4 handle {h} 缺少 {lang} 翻译")
    return report()


def rel(src: str, f: str) -> str:
    return os.path.relpath(f, src)


def report() -> int:
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} 个错误，{len(warnings)} 个警告")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
