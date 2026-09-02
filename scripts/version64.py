#!/usr/bin/env python3
"""Version64 <-> Major.Minor.Revision.Build 互转。

位布局来自 LSLib `LSLib/LS/Resource.cs`（research/E-scripting-infra.md §2.4.3）：
  Major = (v >> 55) & 0x7f, Minor = (v >> 47) & 0xff, Revision = (v >> 31) & 0xffff, Build = v & 0x7fffffff
校验值：1.0.0.0 == 36028797018963968（bg3.wiki meta.lsx 模板示例）。

用法：
  python3 scripts/version64.py encode 1.2.3.4
  python3 scripts/version64.py decode 36028797018963968
"""
import sys


def encode(major: int, minor: int, revision: int, build: int) -> int:
    if not (0 <= major <= 0x7F and 0 <= minor <= 0xFF and 0 <= revision <= 0xFFFF and 0 <= build <= 0x7FFFFFFF):
        raise ValueError("范围：major 0-127, minor 0-255, revision 0-65535, build 0-2147483647")
    return (major << 55) | (minor << 47) | (revision << 31) | build


def decode(v: int) -> tuple[int, int, int, int]:
    return (v >> 55) & 0x7F, (v >> 47) & 0xFF, (v >> 31) & 0xFFFF, v & 0x7FFFFFFF


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("encode", "decode"):
        print(__doc__)
        return 2
    if argv[1] == "encode":
        parts = [int(x) for x in argv[2].split(".")]
        while len(parts) < 4:
            parts.append(0)
        print(encode(*parts[:4]))
    else:
        print(".".join(str(x) for x in decode(int(argv[2]))))
    return 0


if __name__ == "__main__":
    assert encode(1, 0, 0, 0) == 36028797018963968
    assert decode(36028797018963968) == (1, 0, 0, 0)
    sys.exit(main(sys.argv))
