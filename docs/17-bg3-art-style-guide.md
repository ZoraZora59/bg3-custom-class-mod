# BG3 美术风格调研与东方剑修视觉指南

调研日期：2026-09-29（Asia/Shanghai）。

用途：为后续职业／子职业徽记、技能与状态图标、技能特效概念图和生图提供共同基准。本文不改变职业机制，也不代表资产已完成导入或游戏内验证。

**建议方向：保留东方剑修的意象，用 BG3 的纹章、手绘符号和三维魔法材质来表达。** 不能用一条“BG3 风格”提示词包办所有资产：职业徽记、技能图标和实时特效属于不同视觉体系。

## 1. 调研证据与可信度

- **直接观察**：读取并显示了 4 枚官方网站职业徽记，以及 bg3.wiki 所收录的 9 枚原版技能图标和 1 枚战士徽记；另观察了 2 张媒体刊载实机截图。具体样本见第 3、10 节。
- **官方技术文档**：直接读取职业图标、技能／物品图标、AllSpark 特效制作与 MEI 绑定教程。[S1–S4]
- **原制作人员作品入口**：核对了 Larian 的 ArtStation Art Blast，找到 Gameplay VFX 与动画作品集入口。[S5] ArtStation 单独作品页正文受动态页面限制，浏览器预览连续超时；未把无法完整查看的作品细节写成事实。
- **未完成的验证**：没有进入本机游戏，没有逐帧观看原版技能录像，没有测量原版特效时长、颜色值或粒子预算。截图只能支持静态外观观察，不能证明完整运动节奏。媒体截图可能包含早期版本界面，不作为当前版本像素级模板。
- 下文“风格归纳”是对成品的分析；“我们的建议”是拟定创作方向；只有明确引用官方文档的尺寸／接入要求属于技术事实。

## 2. 游戏整体的视觉气质

**风格归纳：有真实材质和空间感的高幻想，配合经过设计的轮廓、光色和装饰。** 写实是材质与场景关系的基础，不意味着每个图标都要画成照片。

| 层面 | 观察与归纳 | 对我们制作的意义 |
|---|---|---|
| 场景／人物 | 石材、木材、布料、皮革、金属各有不同表面；魔法会形成鲜明的局部亮区 | 剑与装备要有实体感；光效需要与人物、地面和命中点建立关系 |
| 光色 | 可同时存在暖火光、冷魔法光、日照与阴影；魔法的饱和度显著高于部分环境材质 | 不把 BG3 等同于全画面暗棕色；冷色仙气也可以融入环境 |
| 界面 | 所观察截图里，深色承载面配合金属色线框、卷曲装饰和纹章符号 | 新资产需要在原界面里成立；技能本体不必再烘焙一圈厚重 UI 框 |
| 图标 | 技能多为发光手绘符号；职业徽记则有金属、宝石、器物的绘画细节 | 分别建立模板，避免把职业徽记的复杂材质带进每枚技能图标 |
| 爆发特效 | 截图可见白亮核心、彩色过渡、粒子／碎屑和场景内明暗关系 | 强烈闪光可以用于命中峰值；持续效果应保留目标与地面的辨识度 |

这些结论来自样本观察，不是 Larian 对美术风格的官方命名。Art Blast 是进一步研究角色、环境、动作和 VFX 的原团队作品入口。[S5]

## 3. 三套资产语言需要分别设计

### 3.1 职业／子职业徽记：器物与纹章

直接观察了官方网站的战士、牧师、法师、游荡者徽记。[S6]

- 结构紧凑，以中心器物和外围放射／卷曲装饰构成整体。
- 战士可见剑与护盾式底板，法师可见书册与法器，游荡者可见刀刃和钥匙等主题物件。
- 有金属高光、较深的凹陷、暖金边缘、局部宝石色；外轮廓在透明背景上也成立。
- 既有对称结构，也有主题需要的非对称变化；不应把“所有徽记必须严格镜像”当成规则。

**我们的建议**：主职业用一柄中央直剑配合环绕剑气／传承印记，四支延续同一柄剑的基本轮廓，改变外围结构。东方剑形与纹样可以保留；装饰需要支撑剑的辨识度。

| 资产 | 初步构图建议 | 需要防止的误读 |
|---|---|---|
| 东方剑修 | 中央直剑＋收拢的气流／环形传承印 | 不默认加入阴阳鱼、八卦、龙或已存在的门派标志 |
| 太玄 | 纤长剑身＋疏朗、闭合的环／云气 | 月、星、阴阳均为可选意象，不是已确认设定 |
| 天倾 | 宽厚主剑＋裂开的外围结构／向外锋芒 | 不自动等同火焰、雷电或圣骑士 |
| 血魇 | 锐长主剑＋倒钩／回卷血气 | 不依赖大面积血肉描绘，也不改变广义掠夺机制 |
| 行歌 | 主剑＋两侧相互照应的弧线／护持结构 | 不因为名字“歌”就改成乐器或吟游诗人 |

### 3.2 技能图标：有笔触的发光符号

直接显示的原版样本如下，重点观察笔画、留白与构图，而不是只取颜色。[S7]

| 原版样本 | 直接观察到的画法 | 可借鉴的结构 |
|---|---|---|
| Magic Missile | 红色晕底，数条淡亮轨迹汇成有方向的投射结构 | 多段御剑的轨迹汇聚；主体不需要画敌人脸部 |
| Eldritch Blast | 同样有红色底，但采用锯齿投射与星状撞击符号 | 同色技能通过轮廓区分；不能推断红色必然代表火或鲜血 |
| Main Hand Attack | 暖色底上的明亮斜剑，内外缘有深浅层次 | 最基础剑招用一柄清楚的剑即可 |
| Cleave | 数条大弧线包围中央攻击符号 | 范围横扫用动作路径表达，不需要绘出完整战场 |
| Misty Step | 蓝色底，靴子轮廓与横向流动线 | 移动能力以主体＋离开／抵达方向表达 |
| Blade Ward | 暖色底，手掌被一圈明亮边界包围 | 护身能力用环绕关系和闭合轮廓表达 |
| Spirit Guardians | 金黄底，持剑的人形与展开的翼状轮廓 | 护持／领域可以保留一个强中心符号 |
| Hunger of Hadar | 蓝色底，多股卷曲形围绕中央留白 | 域、吞噬与包围可通过环形结构表达 |
| Healing Word | 青绿色底，明亮十字与外围细小符号 | 恢复的中心符号明确，外围装饰只作次要层 |

**共同画法**：主色晕底、偏浅的亮线、轻微毛边与粗细变化、有限的柔光、少量点状装饰。不是精密矢量线稿，也不是完整场景插画。样本中的点饰不能据此解释成等级、资源或隐藏规则。

**我们的建议**：每枚图标只有一个主要动作／关系；用一条主轮廓和一组辅助轨迹说明技能。需要人物时只保留姿态与轮廓。放大画稿可保留笔触，最终 64px 图标要适当加粗关键线条、删掉微小装饰。

### 3.3 技能动效：场景内的剑、气流与命中反馈

技能图标里的亮线是抽象符号；实时特效中的剑气需要体积、方向、时间与空间关系。不要直接把图标贴成一张面对镜头的巨大平面符号。

官方工具将特效交给 AllSpark 制作；MEI 负责组合与绑定效果，可指定骨骼、textkey 事件与显示条件，再关联到技能对应字段。[S3–S4]

**我们的建议**：每个技能分别设计准备、释放／移动、命中、持续、消散；这是一份美术分镜，不要求每门技能都有全部阶段。优先确定剑路和命中点，再补辉光、粒子与地面反馈。

## 4. 东方剑修的共同视觉骨架

沿用已经确认的职业设定：[职业概念](10-eastern-sword-cultivator-design.md)、[招式](11-signature-techniques-draft.md)、[绝技](15-ultimate-techniques-expansion-draft.md)、[动作与资源](16-actions-and-resources-draft.md)。

- **共同母题**：剑锋、御剑轨迹、剑气的聚散。东方感主要来自剑形、出招轨迹、凝气方式与节奏。
- **实体佩剑与气剑分开**：启蒙御剑术使用实体佩剑；太玄／血魇以气为核心，天倾／行歌以实体佩剑为主。实体剑保留金属明暗与护手；气剑应仍有剑尖、刃向和剑身轮廓，不能只有一团光。
- **统一精度**：全套图标使用接近的笔画力度、光晕宽度与主体占比；不要一枚写实油画、一枚扁平标志、一枚动漫贴纸。
- **不同技能用不同关系**：攻击＝剑路与命中；护身＝包围与偏转；恢复＝回流／聚合；解控＝破开束缚；团队＝呼应与连接；持续剑域＝明确边界＋稀疏内部活动。
- **超凡强度仍需可读**：力量感可以来自剑路尺度、骤停后的集中释放、击中的密度与目标反馈，不要求全屏常亮。
- **允许仙侠表达**：可以有气剑归一、血影、巨剑坠落等鲜明意象；选择适合 BG3 场景的材质、透明度和光效层次，不必削弱已确认的职业幻想。

## 5. 四支视觉方向草案

本节配色与形状是助手建议，尚未成为用户确认的美术设定。色值是便于试样的起点，没有从原版像素采样。

| 分支 | 建议主色／亮部 | 形状语言 | 建议运动方式 | 对应气质 |
|---|---|---|---|---|
| 太玄 | 青蓝 `#4EAFAE`／淡玉白 `#DBF5E8` | 细长直线、窄弧、疏朗闭环、汇聚点 | 稳定悬停、精确转向、先散后归一 | 从容、清明、精准、超脱 |
| 天倾 | 赭金 `#B77839`／淡金 `#FFE1A0`，辅以深灰 | 厚剑、宽弧、楔形、裂隙、放射线 | 重量感蓄势、猛然扩张、下坠、冲击后余威 | 压倒、强横、摧毁抵抗 |
| 血魇 | 深绯 `#A82042`／浅绯 `#FFB0BA`，辅以近黑紫 | 锐刺、倒钩、破碎弧、向内回卷 | 突进、残影、围杀、能量回流 | 危险、癫狂、掠夺 |
| 行歌 | 青绿 `#368F86`＋旧金 `#BC9756`／浅暖白 `#EEE3BD` | 开放弧、成对轨迹、衔接线、护持结构 | 出招与同伴呼应、接应、跟进、短暂保护 | 仗剑入世、同行、救场 |

颜色负责辅助识别，轮廓与运动负责主要识别。太玄与行歌都使用青色时，前者突出孤立、汇聚与精确点破，后者突出开放、连接与相互照应。

金色不自动代表光耀伤害，青色不自动代表寒冷，绯红不自动代表火焰或黯蚀。图标配色、特效外观与伤害类型是不同决策。

血魇对无血目标也能掠夺力量：可在活体上增加少量血气，在构装／亡灵等目标上表达为碎裂能量、灵性烟缕或力量回流；核心识别仍保持一致。

## 6. 已确认招式的视觉映射草案

下表用等级与能力识别技能，避免把尚未确认的候选招名固定到资产里。只建议表现方式，不确定目标数量、持续时间、伤害类型或动画实现。

| 能力 | 图标主要关系 | 动效概念重点 |
|---|---|---|
| 共同启蒙：御剑术 | 单剑＋一去一回的轨迹 | 实体佩剑离手、击中、归手；剑保持可辨认 |
| 共同：御剑飞行 | 剑托举简化人物＋前进线 | 剑承托角色移动，风迹辅佐；不能画成通过实体墙的传送 |
| 太玄6：单体多段追击 | 多条窄剑路汇入一个目标点 | 多段气剑有出手顺序与命中间隔 |
| 太玄7：解围护身反制 | 外推剑弧＋内层闭合护环 | 初次压退与后续偏转／反击分别可辨 |
| 太玄9：剑域 | 有边界的域＋数柄下落气剑 | 气剑落点清楚、友敌表现区分、重点目标命中更集中 |
| 太玄12：归一贯穿 | 多线收束为一条锋锐主线 | 气剑聚合、穿入首敌、继续沿线；穿墙伤害不能表现成墙被摧毁 |
| 天倾6：扇斩 | 一柄厚剑＋开放大扇弧 | 扇形剑势外推，主目标命中强调 |
| 天倾7：巨剑冲阵 | 宽剑沿直线推开两侧 | 剑锋、角色移动和冲阵路径的关系清楚 |
| 天倾9：化剑坠击 | 向下巨剑＋落点放射线 | 升空／化剑／坠击分镜，爆点后保留近身余威 |
| 天倾12：八方灭阵 | 中央剑＋八向扩张 | 径向同时扩张；与从天落斩保持不同拓扑 |
| 天倾12：天地剑劫 | 多柄巨剑指向同一区域 | 上方剑势集中落斩，目标区域明确 |
| 血魇6：穿行追斩 | 折返锐轨迹＋多个命中点 | 快速追斩有路径，支持分散与集中目标的表现 |
| 血魇7：周身血剑反扑 | 从中心炸开的锐剑 | 爆发外放与收益回流分层；癫狂强化不只增加亮度 |
| 血魇9：移动掠夺剑域 | 围绕人物的回卷环 | 边界随施术者移动，持续伤敌与回流可辨 |
| 血魇12：气凝血影围杀 | 数道持剑影形向内合拢 | 影形围杀、收束；避免表现成有独立回合的召唤队伍 |
| 行歌6：破围接应 | 开口剑弧＋受援者 | 先开缺口，再提示安全移动；不擅自加上强制共同传送 |
| 行歌7：即时合击 | 多条剑路会聚同一点 | 自身出手引导同伴即时跟进 |
| 行歌9：分担伤害 | 同伴与自己之间的承接弧 | 伤害向施术者承接，自身承伤与恢复强化作为次级表现 |
| 行歌12：持续团队爆发 | 相互呼应的剑路与多个节点 | 团队进攻增益与御剑跟进分别可辨，循环粒子保持克制 |

已有常态、4／8级强化、疗伤、解控、资源与被动仍需建立独立资产清单；不能把“17门绝技”误当作全职业只有17枚图标。

## 7. 动效节奏与实现边界

### 建议分层

1. **核心**：剑模型／气剑轮廓／斩击轨迹，表达动作方向。
2. **辅助**：薄雾、少量粒子、辉光、短残影，表达力量性质。
3. **命中**：局部亮闪、破开／偏转／回流，根据能力选择。
4. **持续**：领域边缘、人物附近的有限活动，避免长期遮住目标。
5. **退出**：粒子与残影逐步结束；状态结束时边界明确消散。

太玄的强大靠精准与汇聚，天倾靠体量、冲击与扩张，血魇靠速度、围杀与回流，行歌靠接应与协同。终极比基础技能提高核心形状的层级，而不是只增加粒子数量。

### 官方技术要求与建议分开

- 官方教程中，循环效果使用 Lead In／Loop／Lead Out；非循环的 cast、impact 不要求同样的 phase 结构。教程里的秒数是示例，不能当成全部技能的时长标准。[S3]
- AllSpark 的 `.lsefx` 是编辑源文件，需要编译为引擎使用的 `.lsfx`；官方教程要求效果具有覆盖整个生命周期的 Bounding Sphere／Box。[S3]
- MEI 将效果关联骨骼、事件等，并绑定 PrepareEffect、CastEffect、TargetEffect 等对应字段。[S4]
- **生图产物**可包括特效关键帧、概念分镜、气流／光斑／烟缕纹理候选；它不会自动成为可运行的 MEI、粒子系统或角色动画。
- 实体剑飞行、巨剑、血影可能需要模型／材质或已有资源组合；角色位移与骨骼动作要另外实现。2D 连续帧是否适合某个 emitter／材质，需在 Toolkit 中核对，不能预先承诺。
- 动作规则允许同一次剑术动作组合多种出手时，动效需要能衔接；不为强调蓄势擅自增加准备回合。[职业动作记录](16-actions-and-resources-draft.md)

## 8. 图标制作与交付规格

### 官方要求

| 类别 | 官方资产规格 | 接入区别 |
|---|---|---|
| 技能快捷栏 | 64×64 PNG；atlas 中的单格为64×64 | Texture Atlas Editor 生成图集；技能 Stats 的 Icon 引用名称 |
| 技能手柄菜单 | 144×144 PNG，透明背景 | Convert UI Assets 转换相应 ControllerUIIcons 资源 |
| 技能悬浮说明 | 380×380 PNG，透明背景并带淡出效果 | Convert UI Assets 转换 Tooltips 图标资源 |
| 职业／子职业 | 官方职业教程要求300×300 PNG，转换DDS | 按 ClassDescriptions 的 Name 命名，职业与 hotbar 资源有各自目录 |

前三种技能图标同名配套，不能只提供快捷栏版本。职业图标不能直接套用技能的三尺寸规则。[S1–S2]

### 我们的制作建议

- 先以较高分辨率制作主体母版，例如1024×1024；这是工作尺寸建议，不是游戏导入要求。
- 保留主体／主色晕／辉光／装饰的分层版本；徽记与技能图标使用不同母版。
- 快捷栏版本在64px下重新检查主线粗细与深浅；大尺寸版本保留柔和边缘与透明淡出。不能把实心背景图缩放三次就当作完成。
- 透明淡出允许半透明色晕；“透明背景”不等于删掉所有底色和辉光。具体淡出范围应与对应原版样本并排调整。
- 先检查1024母版，再以64／48／32px预览检查剑尖、动作方向和相邻技能区别；48／32仅为压力检查，不是导出要求。
- 临时使用ASCII技术名和版本号，避免文件名依赖候选中文招名；正式接入时以实际数据表名称与 Icon ID 为准。
- 透明边缘需在深色、浅色与实际界面底上检查，避免白边／黑边；颜色外观还应在实际DDS转换后确认。
- 本项目文档使用UTF-8与LF；Windows脚本显式指定编码。生产输出文件名与命令参数避免混用花式引号。

## 9. 后续生图提示词模板

这些是尚未试生成的制作模板；首批生图后须根据结果修订。需要精确匹配时附原版样本作为风格参考，并附已选定的原创母版维持一致性。参考图用途是画法对齐，不是直接挪用原有技能符号。

### 技能图标

```text
Create one square fantasy RPG ability icon for an original sword-cultivator class.
Subject: [one concrete sword action or relationship].
Use one unmistakable dominant silhouette, softly luminous hand-painted strokes,
slight variation in line thickness, worn brush edges, a restrained [color] pigment
halo, pale contrasting highlights, and generous negative space.
Match the supplied Baldur's Gate 3 ability-icon references in stroke character,
visual density and readability. The subject must remain recognizable at 64 pixels.
Keep only [one essential secondary motif]. Preserve the alpha fade around the
subject and halo. One icon only, no text, no lettering, no UI frame, no montage.
```

例：太玄多段追击的 Subject 可写为 `three slender spectral sword paths converging on one small impact point`；“three”只是首轮构图数量，不据此确定实际攻击次数。

避免出现：`epic cinematic illustration`、完整人物面部、拥挤战场、摄影材质、密集花纹、整屏霓虹、巨大星空。生成透明母版时还必须在图像工具中启用透明背景选项，不能只靠提示词。

### 职业徽记

```text
One original fantasy class emblem: [central sword and surrounding structure].
A compact heraldic silhouette, painted antique metal, recessed dark details,
selective gemstone accents, and restrained ornamental rays or curved filigree.
Match the supplied Baldur's Gate 3 class-emblem references in material treatment
and visual density. Preserve the identity of an eastern straight sword.
Centered composition, transparent background, no text, one emblem only.
```

### 特效关键帧概念图

```text
One in-game VFX concept keyframe for [ability], shown from a readable tactical
three-quarter camera in a grounded fantasy environment with stone and wood.
Show [exact motion phase] and make the sword path, target and impact point clear.
Use [branch shape language], [core color], a limited pale luminous core,
translucent energy edges and restrained secondary particles.
Keep character scale consistent and the surrounding battlefield readable.
Prioritize a plausible real-time effect structure. No UI, no title, no montage.
```

分镜按“准备／释放／命中／持续／消散”逐帧单独生成；每帧附同一锚点参考以保持镜头、人物、剑形和配色。概念图允许画环境；真正用于粒子的纹理需单独生成并核对材质要求。

## 10. 参考来源与后续复核

| 编号 | 来源 | 本次用途与读取状态 |
|---|---|---|
| S1 | [Adding Skill and Item Icons](https://docs.baldursgate3.game/Adding_Skill_and_Item_Icons) | 官方正文直读；技能三尺寸、透明处理、同名、atlas与接入 |
| S2 | [Adding Classes and Subclasses](https://docs.baldursgate3.game/Adding_Classes_and_Subclasses) | 官方正文直读；职业300px与命名／DDS／hotbar目录要求 |
| S3 | [VFX – Part 1: Making Effects](https://docs.baldursgate3.game/VFX_%E2%80%93_Part_1:_Making_Effects) | 官方正文直读；AllSpark、循环阶段、包围体、源文件与编译 |
| S4 | [VFX – Part 3: Assigning and Testing Effects](https://docs.baldursgate3.game/VFX_%E2%80%93_Part_3:_Assigning_and_Testing_Effects) | 官方正文直读；MEI、骨骼／事件、技能字段与测试流程 |
| S5 | [Larian Studios BG3 Art Blast](https://magazine.artstation.com/2023/09/larian-studios-baldurs-gate-3-art-blast/) | 汇总正文直读；原团队概念、角色、场景、动画与VFX作品入口 |
| S6 | [BG3 官网](https://baldursgate3.game/)；[战士](https://baldursgate3.game/classes/fighter.png)、[牧师](https://baldursgate3.game/classes/cleric.png)、[法师](https://baldursgate3.game/classes/wizard.png)、[游荡者](https://baldursgate3.game/classes/rogue.png) | 网站及4枚PNG原图直接读取并显示，作为徽记观察样本 |
| S7 | [Magic Missile](https://bg3.wiki/wiki/Magic_Missile)、[Eldritch Blast](https://bg3.wiki/wiki/Eldritch_Blast)、[Main Hand Attack](https://bg3.wiki/wiki/Main_Hand_Attack)、[Cleave](https://bg3.wiki/wiki/Cleave)、[Misty Step](https://bg3.wiki/wiki/Misty_Step)、[Blade Ward](https://bg3.wiki/wiki/Blade_Ward)、[Spirit Guardians](https://bg3.wiki/wiki/Spirit_Guardians)、[Hunger of Hadar](https://bg3.wiki/wiki/Hunger_of_Hadar)、[Healing Word](https://bg3.wiki/wiki/Healing_Word) | 社区收录的原版资产；9枚图标原图直接读取并显示，仅用来分析外观 |
| S8 | [战士页面](https://bg3.wiki/wiki/Fighter) | 社区收录的战士300px徽记直接显示，对照官网版本 |
| S9 | [Multiplayer.it 魔法指南](https://multiplayer.it/soluzioni/baldurs-gate-3-la-guida-alla-magia-alle-classi-magiche-e-agli-incantesimi.html)；[实机原图](https://multiplayer.net-cdn.it/thumbs/images/2023/08/10/altri_spell_jpg_800x0_crop_upscale_q85.jpg) | 原图直接显示；冷色冰魔法与暖色室内、角色与快捷栏的静态关系；文章未作机制来源 |
| S10 | [JeuxActu 截图库](https://www.jeuxactu.com/jeu/images-baldur-s-gate-3-20343-5.htm)；[实机原图](https://i.jeuxactus.com/datas/jeux/b/a/baldur-s-gate-iii/xl/baldur-s-gate-iii-64cbe7679052c.jpg) | 原图直接显示；火光、碎屑、户外材质与界面；不作为当前UI像素模板 |
| S11 | [Jessica Lecours Gameplay VFX Reel](https://www.youtube.com/watch?v=77_hinfZZEo) | 链接由Art Blast核对；本次未播放逐帧审阅，后续用于真实节奏采样 |
| S12 | [Cliff Laureys 符号设计](https://www.artstation.com/artwork/Zaq4GX) | 搜索发现，作品正文／原图未成功完整查看；只保留入口，不据此断言画法 |

本次原图通过直接读取字节显示，未将原版素材复制进项目，也未生成新图或修改游戏资产。

### 首批制作的建议顺序

1. 先做主职业徽记与共同御剑术，校准两种不同画法。
2. 做四支各一枚常态或代表技能，与原版图标并排检查；确认四支视觉差异后再扩展全套。
3. 太玄多段追击、天倾坠击、血魇穿行、行歌合击各做一组关键帧，校准气剑、实体剑、体量与协同表现。
4. 在游戏快捷栏、手柄菜单、悬浮说明和不同亮度场景中验证；状态叠加与多人特效重叠也要检查。
5. 再进入完整绝技、被动／资源／状态图标与持续领域制作。

后续每个资产记录：对应技能／分支、核心意象、主体构图、配色、参考来源、提示词、版本、导出规格、游戏内截图与修改结果。最终标准是“东方剑修身份清楚，并且放进 BG3 界面与战场中协调”。
