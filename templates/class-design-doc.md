# 职业设计单（GDD）模板 —— <职业名>

> 对应 docs/06 的阶段 0–3。每一栏都要写；"justify"栏空着就不能过 gate 1。

## 0. 概念（阶段 0）
- **一句话职业幻想**：
- **影子基线**（最接近的原版职业，用于逐级对比）：
- **与 Patch 8 十二个新子职业 / 现有同类 mod 的差异**：
- **SE 决策**：☐ 纯数据（可上 mod.io/主机）　☐ 需要 SE（仅 Nexus/PC）—— 理由：
- **目标平台 / 渠道**：☐ Nexus　☐ mod.io　☐ 主机
- **等级范围**：☐ 1–12　☐ 1–20（兼容 UnlockLevelCurve）
- **子职业数量与解锁等级**：

## 1. 基础参数（映射到 ClassDescriptions.lsx）
| 项 | 值 | 备注 |
|---|---|---|
| Name（技术名，无空格，加前缀） | | 类图标文件名 = Name |
| DisplayName / ShortName | | |
| PrimaryAbility / SpellCastingAbility | | 1=STR 2=DEX 3=CON 4=INT 5=WIS 6=CHA（待 V4 核对） |
| BaseHp / HpPerLevel | | 对比影子基线 |
| 施法类型 | ☐ 无 ☐ 全施法 ☐ 半施法 ☐ 三分之一 ☐ 契约 | 不自创曲线 |
| MustPrepareSpells / CanLearnSpells | | |
| 熟练项（护甲 / 武器 / 豁免 / 技能数） | | |
| 起始装备（Equipment.txt） | | |
| 自定义资源（ActionResourceDefinitions） | | 尽量复用原版或隐藏资源（图标依赖 ImpUI） |

## 2. 逐级特性表（阶段 1）
| 等级 | 特性 | 类型（被动/法术/资源/选择器） | 影子基线同级特性 | 差异与 justify | 实现路径（Boosts / PassivesAdded / Selectors / Stats） | 风险 |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | 子职业选择 | | | | SubClasses | |
| 4 | 专长/ASI | | | | AllowImprovement | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | 专长/ASI | | | | AllowImprovement | |
| 9 | | | | | | |
| 10 | | | | | | |
| 11 | | | | | | |
| 12 | 专长/ASI | | | | AllowImprovement | |
| 多职业 1 级 | 只保留多职业应得的熟练/选择器 | | | | IsMulticlass=true | |

## 3. 子职业（每个一张）
- 名称 / ShortName / 幻想一句话：
- 节点（BG3 建议 3/6/10 或 1/6/10）：

| 等级 | 特性 | 影子基线子职业同级 | justify | 实现路径 | 风险 |
|---|---|---|---|---|---|

## 4. 法术与被动清单
| 名称（加前缀） | 类型（Spell_Target/…/Passive/Status/Interrupt） | 触发（StatsFunctorContext / InterruptContext） | 条件 | Functors | 图标（64/144/380 或占位） | 本地化 handle |
|---|---|---|---|---|---|---|

## 5. 纸面平衡（阶段 2）
- **DPR 表**（tier 1: 1–4，tier 2: 5–10，tier 3: 11–12）vs 影子基线：
- **资源节奏**（短休/长休资源数量与回复）：
- **动作经济**（附赠动作 / 反应占用）：
- **复杂度**：crunch（建卡选择）数量 ＝　；grit（每回合要跟踪的效果）＝　（目标：0–1）
- **横向选项数**（可选法术/被动总数）vs 影子基线：

## 6. 技术拆解与依赖（阶段 3）
- 依赖：☐ 无 ☐ Compatibility Framework（可选）☐ Community Library ☐ SE 模块 ☐ 5e Spells ☐ 其它
- Conflicts 声明：
- UUID 对照表（职业 / 子职业 / TableUUID / 各 List / 各 Progression）：见 `uuids.md`
- 图标需求清单（类 ×2、子职业 ×2、技能 ×N×3）：
- VFX：☐ 复用原版（列出 EffectBank/MEI）☐ VFX 库依赖 ☐ 自制
- 本地化：English + Chinese + ChineseTraditional；文本变更清单随版本维护

## 7. 法务自检
- ☐ 名称/特性/文本全部自创或 SRD（已附 CC-BY-4.0 署名）
- ☐ 未使用 WotC 专名 / 第三方 IP
- ☐ 图标、字体、音效许可已记录在 ASSETS-LICENSE.md
