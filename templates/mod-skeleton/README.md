# mod-skeleton：职业 mod 结构骨架（未在游戏内验证）

用途：验证"Mac 编辑 → 校验 → Windows 打包 → 游戏内加载"的流水线，并作为新职业 mod 的起点。
所有 UUID 都是占位（`00000000-0000-4000-8000-0000000000xx`），handle 都以 `hExample` 开头，
用 `python3 scripts/gen_ids.py --rewrite-placeholders <目标目录> --rename ExampleClass <NewName>` 一次性替换。

```
Source/
  Mods/ExampleClass/meta.lsx                          mod 元数据（Folder=Name=目录名）
  Mods/ExampleClass/Localization/English|Chinese/*.xml 本地化（Chinese 目录名为官方语言名）
  Mods/ExampleClass/GUI/Assets/ClassIcons/            类图标位置说明
  Public/ExampleClass/ClassDescriptions/ClassDescriptions.lsx  职业 + 1 个子职业
  Public/ExampleClass/Progressions/Progressions.lsx   1..12 级 + 多职业行 + 子职业 3/6/10 级
  Public/ExampleClass/Lists/SkillLists.lsx, AbilityLists.lsx
  Public/ExampleClass/Stats/Generated/Data/Passive.txt 两个示例被动
  Public/ExampleClass/Stats/Generated/Equipment.txt    起始装备
```

已知待验证点（docs/07 V3/V4）：Lists 分隔符、`PrimaryAbility` 枚举、`LearningStrategy`、hotbar 图标尺寸。
打包：Windows 侧 `Divine.exe -g bg3 -a create-package -s Source -d build/ExampleClass.pak`，或 Multitool / Toolkit Publish Local。
