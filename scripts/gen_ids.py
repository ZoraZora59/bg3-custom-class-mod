#!/usr/bin/env python3
"""生成 UUID / 本地化 handle；或把骨架里的占位符一次性换成真实值。

用法：
  python3 scripts/gen_ids.py --uuid 3            # 打印 3 个 v4 UUID
  python3 scripts/gen_ids.py --handle 2          # 打印 2 个 handle（社区惯例：h + 去连字符、g 分段的 UUID）
  python3 scripts/gen_ids.py --rewrite-placeholders mods/MyClass/Source [--rename ExampleClass MyClass]

规则：
- 占位 UUID 形如 00000000-0000-4000-8000-0000000000xx，同一占位在所有文件里换成同一个新 UUID。
- 占位 handle 形如 hExample<字母数字>，同样全局一致替换。
- --rename 会同时改文件内容与目录名（Mods/<Old>、Public/<Old>）。
官方文档允许自定义 handle 为任意无空格字母数字串（docs/02 §4）；这里生成的格式与 Multitool 的 handle 生成器一致。
"""
import argparse
import os
import re
import sys
import uuid

PLACEHOLDER_UUID = re.compile(r"00000000-0000-4000-8000-\d{12}")
PLACEHOLDER_HANDLE = re.compile(r"\bhExample[A-Za-z0-9]+\b")
TEXT_EXT = {".lsx", ".xml", ".txt", ".lua", ".json", ".md", ".lsj"}


def new_uuid() -> str:
    return str(uuid.uuid4())


def new_handle() -> str:
    return "h" + str(uuid.uuid4()).replace("-", "g")


def rewrite(root: str, rename: tuple[str, str] | None) -> None:
    uuid_map: dict[str, str] = {}
    handle_map: dict[str, str] = {}
    files: list[str] = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if os.path.splitext(n)[1].lower() in TEXT_EXT:
                files.append(os.path.join(dirpath, n))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            s = fh.read()
        for m in set(PLACEHOLDER_UUID.findall(s)):
            uuid_map.setdefault(m, new_uuid())
        for m in set(PLACEHOLDER_HANDLE.findall(s)):
            handle_map.setdefault(m, new_handle())
    for f in files:
        with open(f, encoding="utf-8") as fh:
            s = fh.read()
        orig = s
        for old, new in uuid_map.items():
            s = s.replace(old, new)
        for old, new in handle_map.items():
            s = re.sub(r"\b" + re.escape(old) + r"\b", new, s)
        if rename:
            s = s.replace(rename[0], rename[1])
        if s != orig:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(s)
    if rename:
        old, new = rename
        for dirpath, dirs, _ in os.walk(root, topdown=False):
            for d in dirs:
                if d == old:
                    os.rename(os.path.join(dirpath, d), os.path.join(dirpath, new))
        for dirpath, _, names in os.walk(root):
            for n in names:
                if old in n:
                    os.rename(os.path.join(dirpath, n), os.path.join(dirpath, n.replace(old, new)))
    print(f"替换 UUID {len(uuid_map)} 个，handle {len(handle_map)} 个，文件 {len(files)} 个")
    for k, v in sorted(uuid_map.items()):
        print(f"  {k} -> {v}")
    for k, v in sorted(handle_map.items()):
        print(f"  {k} -> {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uuid", type=int, metavar="N")
    ap.add_argument("--handle", type=int, metavar="N")
    ap.add_argument("--rewrite-placeholders", metavar="DIR")
    ap.add_argument("--rename", nargs=2, metavar=("OLD", "NEW"))
    a = ap.parse_args()
    if a.uuid:
        for _ in range(a.uuid):
            print(new_uuid())
    if a.handle:
        for _ in range(a.handle):
            print(new_handle())
    if a.rewrite_placeholders:
        rewrite(a.rewrite_placeholders, tuple(a.rename) if a.rename else None)
    if not (a.uuid or a.handle or a.rewrite_placeholders):
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
