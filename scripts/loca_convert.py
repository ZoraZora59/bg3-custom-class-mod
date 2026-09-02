#!/usr/bin/env python3
"""BG3 .loca <-> .xml 转换（纯 Python，Mac/Linux/Windows 均可，不依赖 LSLib/.NET）。

用法：
  python3 scripts/loca_convert.py to-xml  <in.loca> [out.xml]        # 单文件 loca -> xml
  python3 scripts/loca_convert.py to-loca <in.xml>  [out.loca]       # 单文件 xml  -> loca
  python3 scripts/loca_convert.py batch   <dir> --to xml|loca [--delete-source]   # 递归批量
  python3 scripts/loca_convert.py check   <file.xml|file.loca>       # 校验：重复 handle / 超长 handle / 非法子元素
  python3 scripts/loca_convert.py selftest                           # 内存往返自测

格式依据（research/H §2.1，来源 LSLib LSLib/LS/Localization.cs）：
  文件头 12 字节：uint32 签名 0x41434F4C("LOCA") / uint32 条目数 / uint32 文本区偏移（= 12 + 70*N）
  条目 70 字节：byte[64] handle（UTF-8，NUL 填充）/ uint16 version / uint32 length（含结尾 NUL）
  文本区：按条目顺序 UTF-8 + b"\\0"；全部小端，无压缩无对齐。
  XML：<contentList><content contentuid="…" version="1">文本</content></contentList>，
       正文里的 <LSTag>/<br> 必须是转义实体（&lt; &gt;），不能是真实子元素。

注意：本脚本按 LSLib 源码实现并做了字节级往返自测，但**尚未用游戏真实 .loca 文件验证**（列入 docs/07 待验证项）。
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import xml.etree.ElementTree as ET
from io import BytesIO

LOCA_SIG = 0x41434F4C
HEADER = struct.Struct("<III")
ENTRY = struct.Struct("<64sHI")
Entry = tuple[str, int, str]  # (handle, version, text)


# ---------- .loca ----------
def read_loca_bytes(data: bytes) -> list[Entry]:
    if len(data) < HEADER.size:
        raise ValueError("文件太短，不是 .loca")
    sig, n, texts_off = HEADER.unpack_from(data, 0)
    if sig != LOCA_SIG:
        raise ValueError(f"签名不对：0x{sig:08X}（期望 0x{LOCA_SIG:08X} 'LOCA'）")
    table = []
    pos = HEADER.size
    for _ in range(n):
        key, ver, length = ENTRY.unpack_from(data, pos)
        pos += ENTRY.size
        table.append((key.split(b"\0", 1)[0].decode("utf-8"), ver, length))
    out: list[Entry] = []
    pos = texts_off
    for handle, ver, length in table:
        if length < 1:
            raise ValueError(f"{handle}: length 字段为 0，文件损坏")
        text = data[pos:pos + length - 1].decode("utf-8")
        pos += length  # 跳过结尾 NUL
        out.append((handle, ver, text))
    return out


def write_loca_bytes(entries: list[Entry]) -> bytes:
    bodies = []
    table = []
    for handle, ver, text in entries:
        hb = handle.encode("utf-8")
        if len(hb) > 64:
            raise ValueError(f"handle 超过 64 字节：{handle}")
        if not (0 <= ver <= 0xFFFF):
            raise ValueError(f"{handle}: version 超出 uint16 范围：{ver}")
        tb = text.encode("utf-8")
        bodies.append(tb)
        table.append(ENTRY.pack(hb.ljust(64, b"\0"), ver, len(tb) + 1))
    header = HEADER.pack(LOCA_SIG, len(entries), HEADER.size + ENTRY.size * len(entries))
    return header + b"".join(table) + b"".join(b + b"\0" for b in bodies)


# ---------- .xml ----------
def read_xml_bytes(data: bytes) -> list[Entry]:
    root = ET.parse(BytesIO(data)).getroot()  # 二进制解析可容忍 BOM
    if root.tag != "contentList":
        raise ValueError(f"根元素应为 contentList，实际为 {root.tag}")
    out: list[Entry] = []
    for el in root:
        if el.tag != "content":
            raise ValueError(f"未知元素 <{el.tag}>（LSLib 也会拒绝）")
        if len(el):
            raise ValueError(f"{el.get('contentuid')}: <content> 内含真实子元素 <{el[0].tag}>，"
                             "富文本标签必须写成 &lt;…&gt; 实体")
        handle = el.get("contentuid")
        if not handle:
            raise ValueError("有 <content> 缺少 contentuid")
        ver = int(el.get("version", "1"))
        out.append((handle, ver, el.text or ""))
    return out


def write_xml_bytes(entries: list[Entry]) -> bytes:
    root = ET.Element("contentList")
    for handle, ver, text in entries:
        el = ET.SubElement(root, "content", contentuid=handle, version=str(ver))
        el.text = text
    ET.indent(root, space="\t")
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="utf-8"?>\n' + body + "\n").encode("utf-8")


# ---------- 通用 ----------
def load(path: str) -> list[Entry]:
    with open(path, "rb") as fh:
        data = fh.read()
    return read_loca_bytes(data) if path.lower().endswith(".loca") else read_xml_bytes(data)


def save(path: str, entries: list[Entry]) -> None:
    data = write_loca_bytes(entries) if path.lower().endswith(".loca") else write_xml_bytes(entries)
    with open(path, "wb") as fh:
        fh.write(data)


def check(entries: list[Entry]) -> list[str]:
    problems = []
    seen: dict[str, int] = {}
    for i, (h, v, t) in enumerate(entries):
        if len(h.encode("utf-8")) > 64:
            problems.append(f"#{i} handle 超过 64 字节：{h}")
        if any(c.isspace() for c in h):
            problems.append(f"#{i} handle 含空白：{h!r}")
        if h in seen:
            problems.append(f"#{i} 重复 handle：{h}（首次出现于 #{seen[h]}）")
        seen.setdefault(h, i)
        if t.startswith("[TODO]"):
            problems.append(f"#{i} 仍带 [TODO]：{h}")
    return problems


def default_target(src: str, to: str) -> str:
    base = src[:-5] if src.lower().endswith(".loca") else src[:-4]
    if to == "xml":
        # a.loca -> a.loca.xml 与 Multitool 约定一致；a.xml 不变
        return src + ".xml" if src.lower().endswith(".loca") else src
    # xml -> loca：a.loca.xml -> a.loca；a.xml -> a.loca
    return base if base.lower().endswith(".loca") else base + ".loca"


def selftest() -> int:
    sample: list[Entry] = [
        ("h00a33f75ge607g4aa2ga34ag4e2849aa53f9", 1, "Text Here"),
        ("MyNewString", 2, "你好，<LSTag Type=\"Spell\" Tooltip=\"Bless\">祝福术</LSTag>造成 [1] 伤害 & 更多<br>换行"),
        ("h" + "0" * 36, 1, ""),
        ("emoji_and_multibyte", 65535, "🗡️ 剑 — ünïcödé"),
    ]
    loca = write_loca_bytes(sample)
    sig, n, off = HEADER.unpack_from(loca, 0)
    assert sig == LOCA_SIG and n == len(sample) and off == 12 + 70 * n, "文件头字段不符"
    assert len(loca) == off + sum(len(t.encode("utf-8")) + 1 for _, _, t in sample), "文件长度不符"
    back = read_loca_bytes(loca)
    assert back == sample, "loca 往返不一致"
    xml = write_xml_bytes(sample)
    assert b"&lt;LSTag" in xml and b"&amp;" in xml, "XML 未转义 <>&"
    back2 = read_xml_bytes(xml)
    assert back2 == sample, "xml 往返不一致"
    assert write_loca_bytes(read_xml_bytes(write_xml_bytes(read_loca_bytes(loca)))) == loca, "loca->xml->loca 字节不一致"
    # 读取带 BOM 与 date 属性的 LSLib 风格 xml
    lslib_style = ("﻿<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<contentList date=\"18/07/2023 18:07\">\n"
                   "\t<content contentuid=\"h1\" version=\"3\">a &gt; b</content>\n</contentList>").encode("utf-8")
    assert read_xml_bytes(lslib_style) == [("h1", 3, "a > b")]
    try:
        read_xml_bytes(b"<contentList><content contentuid=\"x\"><LSTag/></content></contentList>")
        raise AssertionError("应拒绝真实子元素")
    except ValueError:
        pass
    print(f"selftest OK: {n} 条，loca {len(loca)} 字节，xml {len(xml)} 字节")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("to-xml"); p.add_argument("src"); p.add_argument("dst", nargs="?")
    p = sub.add_parser("to-loca"); p.add_argument("src"); p.add_argument("dst", nargs="?")
    p = sub.add_parser("batch"); p.add_argument("dir"); p.add_argument("--to", choices=["xml", "loca"], required=True)
    p.add_argument("--delete-source", action="store_true", help="转换成功后删除源文件（打包前只留 .loca 时用）")
    p = sub.add_parser("check"); p.add_argument("file")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "check":
        probs = check(load(a.file))
        print("\n".join(probs) if probs else f"OK: {a.file} 无问题")
        return 1 if probs else 0
    if a.cmd in ("to-xml", "to-loca"):
        to = "xml" if a.cmd == "to-xml" else "loca"
        dst = a.dst or default_target(a.src, to)
        entries = load(a.src)
        save(dst, entries)
        print(f"{a.src} -> {dst}（{len(entries)} 条）")
        return 0
    if a.cmd == "batch":
        want_src = ".loca" if a.to == "xml" else ".xml"
        count = 0
        for root, _, files in os.walk(a.dir):
            for f in files:
                if not f.lower().endswith(want_src):
                    continue
                src = os.path.join(root, f)
                dst = default_target(src, a.to)
                entries = load(src)
                save(dst, entries)
                if a.delete_source:
                    os.remove(src)
                count += 1
                print(f"{src} -> {dst}（{len(entries)} 条）")
        print(f"共转换 {count} 个文件")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
