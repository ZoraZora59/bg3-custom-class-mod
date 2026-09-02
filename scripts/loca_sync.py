#!/usr/bin/env python3
"""多语言本地化同步工具（以 English 为源）。

用法：
  python3 scripts/loca_sync.py sync  <Source/Mods/<Mod>/Localization> [--langs Chinese,French,...]   # 缺省 = 官方全部 15 种语言
  python3 scripts/loca_sync.py check <Source/Mods/<Mod>/Localization>                                # 各语言完成度
  python3 scripts/loca_sync.py diff  <旧 English.xml> <新 English.xml>                               # handle 变更清单（供 changelog）

规则：
- 每种语言一个 xml（与 English 同文件名）；缺失条目用英文原文占位并加前缀 "[TODO] "，已译条目原样保留。
- English 里删除的 handle 会从其它语言移除（避免残留）；version 跟随 English。
- 语言目录名固定为官方 15 种（docs/08 §1）。
"""
import os
import sys
import xml.etree.ElementTree as ET

LANGS = ["BrazilianPortuguese", "Chinese", "ChineseTraditional", "English", "French", "German", "Italian",
         "Japanese", "Korean", "LatinSpanish", "Polish", "Russian", "Spanish", "Turkish", "Ukrainian"]
TODO = "[TODO] "


def read(path: str) -> dict[str, tuple[str, str]]:
    """handle -> (version, text)"""
    out: dict[str, tuple[str, str]] = {}
    if not os.path.exists(path):
        return out
    for c in ET.parse(path).getroot().iter("content"):
        out[c.get("contentuid", "")] = (c.get("version", "1"), c.text or "")
    return out


def write(path: str, entries: dict[str, tuple[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    root = ET.Element("contentList")
    for h, (v, t) in entries.items():
        e = ET.SubElement(root, "content", contentuid=h, version=v)
        e.text = t
    ET.indent(root, space="  ")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="utf-8"?>\n')
        fh.write(ET.tostring(root, encoding="unicode"))
        fh.write("\n")


def english_file(loc: str) -> str:
    d = os.path.join(loc, "English")
    xmls = [f for f in os.listdir(d)] if os.path.isdir(d) else []
    xmls = [f for f in xmls if f.lower().endswith(".xml")]
    if len(xmls) != 1:
        sys.exit(f"English 目录需要且只能有 1 个 xml，当前：{xmls}")
    return xmls[0]


def cmd_sync(loc: str, langs: list[str]) -> None:
    name = english_file(loc)
    en = read(os.path.join(loc, "English", name))
    for lang in langs:
        if lang == "English":
            continue
        if lang not in LANGS:
            sys.exit(f"未知语言目录 {lang}，官方名单：{', '.join(LANGS)}")
        path = os.path.join(loc, lang, name)
        cur = read(path)
        out: dict[str, tuple[str, str]] = {}
        added = kept = 0
        for h, (v, t) in en.items():
            if h in cur and not cur[h][1].startswith(TODO) and cur[h][1].strip():
                out[h] = (v, cur[h][1])
                kept += 1
            else:
                out[h] = (v, TODO + t)
                added += 1
        removed = len(set(cur) - set(en))
        write(path, out)
        print(f"{lang:20s} 已译 {kept:4d}  待译 {added:4d}  移除 {removed:3d}  -> {os.path.relpath(path)}")


def cmd_check(loc: str) -> int:
    name = english_file(loc)
    en = read(os.path.join(loc, "English", name))
    worst = 0
    print(f"{'语言':20s} {'完成':>6s} {'待译':>6s} {'缺失':>6s}")
    for lang in LANGS:
        cur = read(os.path.join(loc, lang, name))
        missing = [h for h in en if h not in cur]
        todo = [h for h, (_, t) in cur.items() if t.startswith(TODO) or not t.strip()]
        done = len(en) - len(missing) - len(todo)
        worst = max(worst, len(missing) + len(todo))
        print(f"{lang:20s} {done:6d} {len(todo):6d} {len(missing):6d}")
    return 1 if worst else 0


def cmd_diff(old: str, new: str) -> None:
    a, b = read(old), read(new)
    for h in b:
        if h not in a:
            print(f"ADDED    {h}: {b[h][1][:60]}")
        elif a[h] != b[h]:
            print(f"CHANGED  {h}: v{a[h][0]} -> v{b[h][0]} | {b[h][1][:60]}")
    for h in a:
        if h not in b:
            print(f"REMOVED  {h}")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "sync":
        langs = LANGS
        if "--langs" in argv:
            langs = argv[argv.index("--langs") + 1].split(",")
        cmd_sync(argv[2], langs)
        return 0
    if cmd == "check":
        return cmd_check(argv[2])
    if cmd == "diff" and len(argv) == 4:
        cmd_diff(argv[2], argv[3])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
