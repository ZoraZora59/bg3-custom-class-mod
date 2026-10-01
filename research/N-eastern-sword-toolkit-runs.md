# 东方剑修：Toolkit 实际运行记录

日期：2026-10-01。本文记录正式 `EasternSwordCultivator` 的实际编辑器观察；设计与模拟测试覆盖矩阵见 [M](M-eastern-sword-validation.md)。正式模块 UUID 为 `6560ea02-fe1e-5fdb-8631-b41a2e53af90`，与旧 Skeleton 测试工程不同。**当前`629ADB...`包的第十二轮Toolkit严格门禁已通过，可进入正式客户端测试；本包直接实测1–3级及四支三级选择。旧`6EE20F`包正式游戏创角后一级职业能力为空，G-01未通过；当前包G-01至G-12仍待客户端实测。**

## 第一次载入：未通过

编辑器 `Glasses 4.1.1.6931813`。项目浏览器出现 `EasternSwordCultivator`，选择后窗口标题及原生日志均确认载入的是该正式工程。源文件安装、快照和恢复记录在 `build/sword-cultivator/toolkit-environment/`。

实际观察到的阻断问题：

- `Progression.cpp:177` 明确报告 `UnlockSpell boost is forbidden in progressions! Use AddSpell selector`。这是编辑器真实断言；此前 StatParser 的零诊断没有发现这一限制。
- `TextureAtlas.cpp:219` 报告图集资源 UUID `b7a5697a-ce9a-5536-aa45-886eb81beaa1` 未找到。安装时还没有把可读 `_merged.lsx` 编译为原生 `_merged.lsf`。
- 界面显示 `Missing MetaData`，指出本模块 `Mods/<folder>/GUI` 缺失纹理元数据。

原生 Shared 中 `Projectile_TEST_Chair_Throw` 的轨迹模板也产生两个 GlobalTemplate 缺失断言；native agent 在已安装 Shared 原版编辑器表中找到相同 GUID，故暂归为原版测试数据噪声，不能混作本模块起始装备的错误。首次加载还包含原版 DLC 元数据、标签、重复效果等诊断，后续需要按模块归属核对，不能宣布所有日志为空。

本轮没有加载 Basic_Level_A，也没有测试职业升级或技能生效。在错误未修复时取消关卡选择并正常退出编辑器。关机后保留完整 Data 与最新日志快照，再恢复本项目测试目录。

证据快照：`build/sword-cultivator/toolkit-environment/capture-20260929-124528-008018/`；原生日志为 `logs/log.2026-09-29T12-43-01-866613.txt`，`capture.json` 记录每个文件 SHA256。日志内部时间与文件名时区不同。快照只证明当时的文件与诊断，不等于游戏测试通过。

## 已准备的修复，待第二次编辑器复测

- 把进阶中的直接 UnlockSpell 改为独立 SpellLists 与 AddSpells selectors。
- 增加 GUI 的非空纹理 metadata，并在安装时将 metadata 与资源库 LSX 编译为 LSF。
- 安装／恢复脚本只操作本模块的确切 UUID 目录，保留修改前备份与编辑器产物。正式客户端部署要求当前版本 Toolkit 报告通过；此时尚无通过报告，第八轮结果见文末。

## 第二轮载入：崩溃，原因已定位到原生长度限制

相同源版本分别通过直接启动和 Steam 标准启动载入后，进程退出。Windows Application 1000 记录 `CoreLib.dll`、异常 `0xc0000005`、偏移 `0x357c6`。改回标准入口后得到原生日志 `log.2026-09-29T12-48-42-414752.txt`，其中 `GSTNodeStorage.cpp:50` 明确报告：固定字符串不支持超过 2048 字节，本次请求为 2665 字节。随后栈为 `StatsObject::SetValue` → `RPGStats::ParseDataLine` → `LoadStats`。

这构成具体的 Stats 字段长度故障证据，不能归因为纹理 Template 字段，也不能用静态解析成功反驳原生崩溃。native agent 已收到日志，需拆分长字段并复测；validation agent 添加原生长度契约。

本日志还报告 Skills 与 Abilities 用分号拼接后被当作单一枚举值，需改为原生列表支持的逗号格式。旧 Skeleton 的 Toolkit 导出 SkillLists 已保存合法逗号例子。

第二轮保留快照为 `build/sword-cultivator/toolkit-environment/capture-20260929-125027-974102/`。确认编辑器进程终止后恢复临时项目目录。当前仍没有职业创建、升级或资源显示通过证据。

## 第三轮：工程、关卡和职业选择可用，职业纹理未通过

正常载入正式工程后，项目封面实际显示；选择 `Basic_Level_A`，聚焦视口后以 `Ctrl+Enter` 进入内置 Game Mode。使用官方编辑器控制台 `ccStartRespec`，职业列表底部出现 `Eastern Sword Cultivator`，可以选择；界面显示中文职业描述、Actions、Cantrips、Class Features 和长剑、短剑、长弓、短弓熟练。

本轮未再出现前两轮的 UnlockSpell 禁用、图集 UUID 缺失、GUI 缺元数据、2048 字节长字段或技能/属性列表枚举错误。但重设界面原生日志报告 `GUI/Assets/ClassIcons/hotbar/ClassEasternSwordCultivator.DDS` 无法实例化，职业图标确实为空。native agent 核实源此前只提供 PNG，已准备符合请求路径的 DDS 和低清根目录；该修复待下一次同步复测。

选择职业后界面有未完成的必选项。第四轮进一步操作确认该提示来自重设角色保留旧职业的技能熟练，需要重新选择东方剑修的两项熟练；第三轮仅凭提示将其归因到属性分配并不准确。独立源码审查另行发现旧 Skeleton 遗留的 `SelectAbilityBonus` 给了设计未授权的 +2/+1，下一版移除，同时修复兼职初次加入时共享剑术 selector 被误删。该源码问题与界面必选项属于不同证据。

结束 Game Mode 并正常退出编辑器后，保留不可变快照 `capture-20260929-130436-834791/`，日志 `log.2026-09-29T12-54-22-860781.txt`。测试 UUID 目录已恢复，编辑器产物保留在 `retired-20260929-130443-116563/`。四条分支 1–12 级升级、完整图标与技能验证仍待完成，正式客户端仍受 Toolkit 通过报告约束。

## 第四轮：职业徽章及行歌连续升级已实际操作，最终版本仍待复测

本轮安装时间 `2026-09-29T13:05:04`，日志 `log.2026-09-29T13-05-10-968037.txt`。项目、Basic_Level_A 和 Game Mode 正常载入。重设角色时主职业徽章在职业列表、角色信息栏和技能书中实际显示；3级分支页逐个选择太玄、天倾、血魇、行歌，四个不同颜色的徽章与对应描述均显示，最终确认行歌。

初次重设角色的技能熟练为 0/2，选择 Athletics 与 Insight 后成为 2/2 并可以 Confirm；属性页额外分配点为0。保留的 Astarion 初始属性为 `8/15/14/12/13/10`，不是新角色推荐属性的验证。2级技能书可打开，4项初始职业技能图标显示、剑元计数为6；3级热栏计数为10。

随后逐级实际确认 1→2→3→4→5→6→7→8→9→10→11→12。4级选择 Alert，8级选择 Ability Improvement 并将 Wisdom 从13加到15，12级选择 Great Weapon Master。各次均能确认并进入下一级，没有遗漏必须选择项导致卡住。12级技能书显示行歌、Lv12、剑元上限50及完整进阶技能图标；测试角色 HP 为100。生命增量只验证原生进阶，不证明 Script Extender 的分支生命乘数。

本轮仍报告三个本模块问题：资源图 `Assets/Shared/Resources/ESC_SwordYuan.png` 缺失；主职业推荐属性 preset 缺失；表达式 `MeleeOffHandWeaponRange` 不能解析。native agent 已准备源修复，包括两质量资源 PNG/DDS、5个合法27点推荐属性 preset、技能推荐，以及明确3m的主副手近战范围。此次 Data 安装早于这些修改，因此第四轮不能用来给最终源签署通过报告。

Basic_Level_A 的原版 Astarion 图标缺相机／点触发器、动画、零色号和近零 culling plane 诊断持续存在，需与本模块路径问题分开归属。Toolkit 内没有加载正式客户端 Script Extender，复杂逐段伤害、协同选择、伤害分担和控制解除仍未在本轮验证。

第四轮结束后确认编辑器进程已关闭，保留不可变快照 `capture-20260929-132321-894055/`，并恢复 UUID 测试目录；产物保留于 `retired-20260929-132324-082613/`。第五轮重新安装最终原生源，修复项需要此轮新证据。

## 第五轮：太玄升级至 7 级；资源状态纹理仍不完整

第五轮于 `2026-09-29T13:23:41` 安装新的原生源，载入正式项目和 `Basic_Level_A`。内置 Game Mode 的 Gale 重设为本职业，推荐属性直接显示 `8/14/15/8/15/10`，两个推荐技能已满足必选条件，重设可确认。一级生命为 12。授予调试经验后，逐次确认 2、3、4、5、6、7 级；3 级默认选择太玄，4 级选 Alert。各级可进入下一页，生命依次显示 20、28、36、44、52、60；5—7 级太玄技能、额外攻击和相关图标出现。7→8 级界面已进入升级动画，但本轮没有取得 8—12 级确认画面，因此不能算太玄全程通过。

本轮原生日志 `log.2026-09-29T13-23-52-390660.txt` 未再出现此前的推荐属性或 `MeleeOffHandWeaponRange` 错误；但可明确归属于本模块的缺失图像路径包括 `Assets/Tooltips/Icons/ESC_badge_sword_cultivator.png` 及 `Assets/Shared/Resources/{Highlight,Missing,Used}/ESC_SwordYuan.png`。太玄 `Projectile_ESC_taixuan_zhaoxi` 的条件伤害在 `StatsDescriptionHelper.cpp:1988` 被报告无法用于 Tooltip 伤害参数。这些是新的复测对象；不能以原图文件存在、静态检查通过代替实际 UI 验证。

2026-09-30 复工时已确认编辑器进程不存在，保留 Data 和完整日志快照 `build/sword-cultivator/toolkit-environment/capture-20260930-191754-063463/`，然后恢复本模块 UUID 测试目录，编辑器产物保留于 `retired-20260930-191800-834589/`。Windows Application Error 事件1000与 WER事件1001确认编辑器于 `2026-09-29 13:52:11` 崩溃：`Glasses.exe`／`CoreLib.dll`，异常 `0xc0000005`、偏移 `0x93371`、Report ID `ef2df1e1-7a47-4c6b-8b8e-8ccd46802ce8`。日志末尾也有 `EoCPlugin.dll` 严重断言；崩溃根因及是否与本模块有关尚未证明，故不能视为正常退出。第五轮安装早于之后的普通剑击伤害与完整资源纹理修复，也不能为最终 PAK 签署 Toolkit 通过报告。

## 第六轮：最终资源修复后太玄完成 1–12；退出崩溃

主agent在正式模块编辑器中完成太玄 1→12 与技能书界面检查。不可变快照为 `build/sword-cultivator/toolkit-environment/capture-20260930-200105-722737/`，日志为 `logs/log.2026-09-30T19-38-21-608000.txt`。独立日志分析 `build/sword-cultivator/toolkit-sixth-log-analysis.json`：561,716行，直接归属ESC的资源缺图、条件Tooltip及StatParser问题0项，修复目标未再出现。这里的“0”仅表示该次日志未观察到相关错误，不等于所有技能已在游戏中生效。

退出时原生日志出现 `EXCEPTION_ACCESS_VIOLATION`，栈含Noesis与 `ls::ResourceManager::UninstallGameUI`；Windows事件1000在2026-09-30 20:00:28记录 `Glasses.exe`／`CoreLib.dll` `0xc0000005` 偏移`0x933eb`，Report ID `920767ca-8c97-4762-861f-8939da3633eb`。本轮不能判为正常退出或Toolkit总通过。之后在已经恢复ESC目录的旧Skeleton工程加载时，Toolkit也发生 `KhonsuBinding.dll` `0xc0000005`，提示宿主本身可能另有不稳定性，但不能由此证明ESC与上述退出崩溃无关。

## 第七轮：最终PAK四支升级界面已覆盖；退出崩溃仍在

主agent报告此轮使用最终PAK对应源，在Toolkit内完成天倾、血魇、行歌三支各自1→12升级界面；结合第六轮同版太玄1→12及其技能书检查，四支原生成长界面路径已实际操作。此证据限定为Toolkit内职业、分支和升级UI，不证明Script Extender逐段伤害、动作资源、伤害分担、飞行路径或正式客户端战斗。更细的每级技能／能力语义仍按独立静态与客户端case分别核验。

快照为 `build/sword-cultivator/toolkit-environment/capture-20260930-204420-311008/`；日志为 `logs/log.2026-09-30T20-08-20-492359.txt`。只读分析 `build/sword-cultivator/toolkit-seventh-log-analysis.json` 扫描1,016,338行，直接归属ESC的缺图、条件Tooltip、Stats解析等错误 **0项**。但原生日志第1,016,259行出现未处理异常，第1,016,262行确认为 `EXCEPTION_ACCESS_VIOLATION`，栈第1,016,281／283行涉及Noesis、第1,016,289行涉及 `ls::ResourceManager::UninstallGameUI`。这是该轮退出崩溃，根因和ESC归属未证，因此当时不能写成Toolkit整体通过；后续第八轮已完成正常退出复测。

第七轮之后曾为隔离客户端诊断加显式退出崩溃override，绑定旧PAK SHA `83e273f0cbe1a5f5cb8d147504a0fd0d173eec5408133be15feec98780dde416`及该轮capture/分析。这是历史测试路径，不生成或伪造Toolkit通过报告；第八轮通过及新PAK形成后不再用该旧SHA作为当前放行依据。完整门禁边界见[M](M-eastern-sword-validation.md)。

## 第八轮：驱动更新后同源复测，正式Toolkit报告通过

不可变快照 `build/sword-cultivator/toolkit-environment/capture-20260930-215321-662466/` 中正式项目和 `Basic_Level_A` 成功加载；主agent观察到职业列表的主职业徽章、英文名称及中文描述，职业选择界面的Actions、Cantrip与Class Feature图标渲染。第六／七轮已实测同源四支的1→12升级界面及分支徽章。三个capture各477项清单文件中475项哈希一致，只有重新生成的 `GUI/metadata.lsf` 与`[PAK]_ESC_UI/_merged.lsf`二进制不同；第八轮477个物理文件均与自身清单SHA一致。资源图标实测范围限于上述编辑器界面，不含每个战斗VFX。

本轮日志 `logs/log.2026-09-30T21-44-14-954571.txt` 共103,685行。`build/sword-cultivator/toolkit-eighth-log-analysis.json` 可从原日志重算得到相同JSON：直接归属本模块错误0项、未检测到原生崩溃；主agent确认使用Alt+F4后Glasses正常退出。此前第五至七轮崩溃记录仍保留，不追溯标为正常。正式`build/sword-cultivator/toolkit-validation.json`在2026-09-30 21:53:24+08:00记录`project_load`、`class_and_subclasses`、`level_1_to_12`、`spells_and_icons`、`editor_log`五项PASS，整体PASS；该报告绑定的旧PAK SHA256 `6EE20F4D0BDDB5FDCE1254C9DBB68BC90C1B0977648DB645B58287D1A6989F84`在当时与文件及build-report一致。

这一通过只覆盖旧包编辑器UI和日志。正式客户端后续已创角，但G-01暴露一级能力缺失；G-01至G-12仍无完整通过证据。新包版本边界见下一节。

## 正式客户端旧包首测：G-01部分完成且失败

主agent在旧`6EE20F`包的正式游戏中创建`ESC_Test_01`、进入鹦鹉螺，确认职业名称／描述本地化和徽章正确。一级Actions、Class Features、Cantrips均为空；唯一可见火焰箭来自高精灵原生种族。Starter选择的提示还继承了回气／回血说明。这是实测故障，不能把角色入图当作职业技能验证通过。

`build/sword-cultivator/game-first-log-analysis.json`对应首测`Extender Runtime 2026-09-30 14-00-35.log`：1,107行，234次错误。`Runtime.lua:891`在ExecuteFunctor中访问不存在的Source/Target属性共28次，`:913`／`:934`以无效`.Item`组件访问实体共206次；正式客户端SE日志门禁FAIL。旧PAK与第八轮Toolkit capture中14个Stats、Progressions、Lists、ClassDescriptions文件逐项哈希相同，故不是漏包。正式SpellLists 35项和Skill／AbilityLists各1项缺`Name`，但Toolkit Editor表自动补名，原版对应节点均有；这是已修复的格式差异，尚不能证明其导致能力缺失。

后续只读收束确认：地图通用栏已出现的 `Shout_ESC_StartingSword` 来自一级 SpellList 的原生 `AddSpells` 授予，源码 Lua 没有手动解锁此技能；因此至少一条原生授予路径生效，不能把现象归为全部进阶表未加载。一级 Progression 的 TableUUID 与 ClassDescription 的 ProgressionTableUUID 一致。同一节点还包含精通 Boosts 和三项 PassivesAdded，尚未找到解释这些能力缺失的确定结构错误。专用测试存档只读解包的 `SaveInfo.json` 确认主职业 `EasternSwordCultivator`、等级1、经验0、地图 `TUT_Avernus_C` 和正式游戏版本 `4.1.1.7631656`；存档及回读文件哈希记录在 `build/sword-cultivator/game-first-save-readback-evidence.json`，原存档未改写。下一轮需读取实际 SpellBook、被动、精通/Boosts 和加载解析日志，才能进一步定位授予阶段。

源已补37个Lists `Name`、清空Starter继承Tooltip并修正Runtime实体代理访问。此阶段PAK `E34EEB000124EF928B536A7095BB8A5850E569D7EF6C1F79028A294B0F738C63`为21,176,099字节，94/94静态／Lua模拟回归通过、StatsParser 0诊断、回读PASS。**第八轮Toolkit报告仍绑定旧SHA，不能给新包放行。**测试环境已恢复且无其他PAK差异，第九轮前Toolkit新源安装活动；此后已捕获并恢复。桌面黑屏／拒绝访问期间没有进行新客户端操作。G-01需从新包一级法术／被动／Starter提示和SE日志重新验证，G-02至G-12仍待正式游戏证据。

## 第九轮：原生Publish Local成功，一级／二级UI可用

桌面恢复可操作后，主agent在Toolkit正式工程中正常进入／停止Game Mode，并以Wyll运行`ccStartRespec`。选择东方剑修时1级Starter、剑击和两项被动出现；接受重设回到地图时HP为12。随后Ctrl+Shift+L升级到2级并接受，HP为20，调息与气护图标出现。这些是Toolkit UI与升级路径实测，不代表正式客户端新包的一级能力已修复。此轮Toolkit `Publish Local`也实际成功生成原生PAK。

不可变快照 `build/sword-cultivator/toolkit-environment/capture-20260930-234739-263044/` 已保存，随后原测试目录已恢复，主agent确认Game Mode正常停止、Alt+F4退出且无Glasses/bg3进程。独立运行`scripts/analyze-sword-toolkit-log.py`得到`build/sword-cultivator/toolkit-ninth-log-analysis.json`：日志`logs/log.2026-09-30T22-23-40-822297.txt`共126,871行，直接归属ESC的错误0类，未检测到原生崩溃；分析器退出码0只证明这份日志的边界。

本轮曾观察到金色主职业徽章，但未将其形状与源图比对，“generic”是误判，不能据此认定引擎fallback。原生导出包与脚本包的只读对照见 `build/sword-cultivator/native-toolkit-export/comparison.json`及`comparison.md`：原生PAK `6BA40D8C15A861BADAFA3474E61E44C6ADBF5CF68095CCC9D91B010A99AABF4B`，脚本PAK `E34EEB000124EF928B536A7095BB8A5850E569D7EF6C1F79028A294B0F738C63`。五个核心ClassDescriptions／Progressions／SpellLists／SkillLists／AbilityLists文件逐字节一致，所有其他共同游戏文件除meta、GUI metadata和UI LSF外也相同。native GUI metadata只含188个PNG键，主职业PNG键指向缺失文件，虽有同名DDS却未注册该键；这是文件契约差异，不能从中断定UI回退。native包还没有脚本包的根目录已编译LOCA，且meta中文描述乱码，故不可直接替代脚本包。旧`toolkit-validation.json`仍绑定`6EE20F`，未因第九轮自动改为通过。

## 第十轮：源图徽章已观察，一级选择可见；日志证据有限

此轮使用`8E6B81D10163146EB6EC1B5B0B59FB8026474956FE4DBF9DC7B54C20D95F9120`包对应源，主agent以Karlach（Zariel Tiefling）重洗到一级东方剑修。主类金色圆环剑徽章与Source `GUI/Assets/ClassIcons/ClassEasternSwordCultivator.png`（300px）实体经图像比对形状相符，Starter、剑击、两项被动以及中文职业描述可见。**本轮未接受重洗，也未升级**；前轮Wyll的12／20HP结果不能冒充本轮结果。`ProjectSettings`中文Description仍乱码，BOM探针失败后已撤销为安装副本ASCII XML字符引用，结果仍待下一轮核实。

主agent正常停止Game Mode、Alt+F4退出并确认无Glasses/bg3进程；不可变快照`build/sword-cultivator/toolkit-environment/capture-20260930-235754-524631/`已保存并恢复安装目录。`build/sword-cultivator/toolkit-tenth-log-analysis.json`对该capture内日志报告126,871行、直接ESC问题0、未见原生崩溃；但**这份日志与第九轮capture中的文件逐字节相同**，是沿用日志，不能单独证明第十轮日志清洁。退出结论来自主agent的进程／UI观察。

只读[核心表连续性](../build/sword-cultivator/toolkit-tenth-core-continuity.json)比较当前`629ADB849FA98A5777AF28C746549732B8415498B6243A77582943238FFAC57D`源与第六／七轮capture：Public的ClassDescriptions、Progressions及Editor对应.tbl均同SHA；三类Public Lists各不同，因为35个SpellList、1个SkillList、1个AbilityList从无`Name`变为全有，Editor Lists.tbl同SHA。当前源10个对应文件与本轮capture全同SHA。旧四支1→12 UI可用于说明**未变化的核心成长表**曾被实际操作，不能代替新Lists的正式客户端或第十一轮同包验证。主agent现已重建`629ADB...`包（22,702,124字节、96/96回归、StatsParser 0诊断、封包回读PASS），旧`toolkit-validation.json`仍绑定`6EE20F...`。下一轮计划对新包做正式Toolkit gate及LocalPublish，正式游戏G-01至G-12仍待新包验证。

## 第十二轮：当前629包的Toolkit同版门禁通过

主agent在当前`629ADB849FA98A5777AF28C746549732B8415498B6243A77582943238FFAC57D`包对应正式项目载入`Basic_Level_A`，以Astarion运行`ccStartRespec`。主职业金色圆环剑徽章、中文描述、起始赠剑动作、剑击戏法和两项职业被动显示；一级接受后地图HP12。Ctrl+Shift+L按正式升级界面升二级并接受，HP20、两项戏法可见；三级界面HP28，太玄、天倾、血魇、行歌四支逐一选择时各自徽章、中文描述和能力均显示。接受行歌三级后，热键栏出现该分支技能和徽章。此处只记录实际操作到三级，不把第六／七轮四支1→12写成本轮重测。

正常Ctrl+Enter停止Game Mode并Alt+F4退出，主agent确认Glasses进程不存在；安装目录已恢复。不可变快照为`build/sword-cultivator/toolkit-environment/capture-20261001-003234-760301/`。本轮新日志`logs/log.2026-10-01T00-11-47-847560.txt`的[分析JSON](../build/sword-cultivator/toolkit-twelfth-log-analysis.json)扫描159,281行，直接归属ESC的缺图／Stats／引用问题0，未见原生崩溃。与第十轮沿用旧日志不同，这是第十二轮新增的日志。快照清单507项均逐个复核物理哈希。

[连续性JSON](../build/sword-cultivator/toolkit-twelfth-continuity.json)显示当前包481个同名文件与第十二轮capture逐字节相同，Toolkit改写了meta、GUI metadata和UI LSF三个文件；当前Public／Editor职业与成长表及Editor Lists表与第六／七轮同SHA。三类Public Lists比旧轮多37个`Name`字段，不能仅靠旧轮推出新版所有技能语义；本轮对1–3级新Lists入口已直接复验。第六轮太玄及第七轮另三支1→12升级UI仅作**未改核心成长表**的历史连续性证据。`build/sword-cultivator/toolkit-validation.json`已按当前PAK SHA记录五项PASS，严格默认部署门禁允许进入正式游戏测试；它不表示4→12本包重新操作，也不表示SE／战斗／存档验证通过。当前包G-01至G-12仍待客户端证据。

## 第十三轮：小图标恢复，配剑选择移除；条件提示映射仍需修复

本轮对应包 `356E198FC73054D7FAA3DE22EFCBD70990EDBD6172BD57720B4BC3BEE01D5B30`，99/99自动检查及封包、图集、封面回读通过。图集文件与引用统一为小写扩展名 `ESC_Icons.dds`，独立编译TextureBank资源，DDS包含11级mip。Toolkit项目列表可显示封面；这不能证明正式客户端模组列表封面已恢复。

在正式项目 `Basic_Level_A` Game Mode 中，以Lae'zel重洗为东方剑修，一级主职业徽记、戏法和两项职业特性的小图标可见；接受后HP12，剑击与御剑术快捷栏小图可见，没有“选择初始配剑”入口。二级接受后HP20，调息和气护图标显示。三级HP28，逐一选择太玄、天倾、血魇、行歌，四支徽记、中文描述、动作、戏法、被动小图均显示；接受行歌后快捷栏新增分支图标可见。本轮直接操作到三级，未重跑四支4–12级，也未测试正式游戏或Script Extender战斗机制。

正常Ctrl+Enter停止Game Mode、Alt+F4退出，确认Glasses及游戏进程均不存在。不可变快照 `capture-20261001-012422-497745/` 已保存，Toolkit测试UUID目录已恢复。新日志 `log.2026-10-01T01-04-44-295548.txt` 共182,990行；[日志分析](../build/sword-cultivator/toolkit-thirteenth-log-analysis.json)未检测到原生崩溃，但有5次 `CE_Status_ESC_MAIN_SWORD_False` 条件错误提示映射缺失。**因此本轮日志门禁失败，不能给356包签署全部通过；需补映射并重建复测。** 原版测试关的Lae'zel头像相机／触发器与近零culling plane诊断另行保留，不归为本职业小图缺失。

## 第十四轮：6DD包的界面复验完成，缺少本轮通用日志

当前包 SHA256 `6DD25F0AB73B5CF1994233F34D46AD6A4EC173B405BB0F253663CB0C25D6ED75`，22,784,703字节，487项。新增22条原生条件错误提示，Public `ConditionErrors.lsx`、Editor对应表和中英本地化逐项一致；106/106自动检查通过，StatsParser 0诊断，PAK、图集、封面回读通过。生产源及包在测试期间未修改。

主agent直接启动Toolkit，载入正式ESC项目的 `Basic_Level_A`，以Wyll重洗。项目列表封面、主职业徽章、一级剑击与两项职业被动小图可见，没有“选择初始配剑”。接受一级、二级、三级后地图生命值分别12、20、28；三级太玄、天倾、血魇、行歌依次选择，各自徽记、中文描述及动作／戏法／特性小图可见，最后接受行歌。地图快捷栏显示对应小图。打开问路的近战副手／御剑副手变体，均显示 `Requires an off-hand sword.`；近身剑术主手佩剑变体显示 `Requires Qi Sword mode.`。**普通MAIN_SWORD条件失败提示未直接观察**，不借此宣称所有22种提示都已逐个实测。本轮没有测试正式游戏、战斗伤害或SE回调。

正常Ctrl+Enter停止Game Mode并Alt+F4退出，随后进程检查确认Glasses/bg3/bg3_dx11均不存在。快照 `capture-20261001-020412-062917/` 已保存，源目录恢复至 `retired-20261001-020456-622121/`。[连续性报告](../build/sword-cultivator/toolkit-fourteenth-continuity.json)复核509/509个清单文件，当前包Mods/Public485项均存在于capture，482项逐字节相同；另3项为Toolkit安装副本meta的ASCII描述及两个语义相同的重编译LSF。Public／Editor职业与成长表和旧轮同SHA，四支1–12仅保留第六／七轮未变成长图的历史证据，本包直接操作到三级。

本轮新 `osirislog.2026-10-01T01-40-41-924240.log` 写至02:01；但capture中的 `log.2026-10-01T01-04-44-295548.txt` 及thoth日志与第十三轮逐字节相同，原文件修改时间也早于本轮安装。[第十四轮日志分析](../build/sword-cultivator/toolkit-fourteenth-log-analysis.json)只是对旧文件的重算，其中5条条件提示错误属于第十三轮，**不能解释为6DD包的新错误，也不能证明第十四轮日志无错**。因此当前 `editor_log` 仍为pending，总门禁pending，禁止凭旧日志刷新正式客户端PAK。将采集脚本改为只接受本轮安装之后产生的日志，并记录stale/missing证据，再补一轮Toolkit日志核验。

### 第十五轮补测尝试：屏幕控制失败，未启动Toolkit

02:13安装同一6DD包对应源后，主agent尝试以Computer Use返回的 `steam://rungameid/2934770` 启动Toolkit。接口返回 `GetCursorPos failed: 拒绝访问。 (0x80070005)`，Steam窗口捕获全黑；没有发现Glasses进程，因此本次没有执行任何Toolkit UI验证。已向用户请求恢复桌面，未尝试绕过安全桌面或改用其他UI控制方式。

采集脚本修复及4项临时目录回归通过。`capture-20261001-022228-039418/capture.json` 的 `log_evidence` 将三个旧日志类型明确记为stale，未复制旧日志；这只检验了证据采集和未启动状态，不是新的Toolkit通过证据。随后正常执行restore，源产物保留于 `retired-20261001-022239-959632`，活动Toolkit测试目录已回收。当前正式游戏仍保留旧629包，本轮未刷新客户端PAK、未操作游戏。待桌面恢复后仍需同一冻结6DD源的新日志核验。

## 第十六轮：同一冻结6DD源的新日志补验

08:25确认桌面重新可操作，08:26安装冻结6DD包对应源。通过Steam的Toolkit库页面启动编辑器，Glasses进程23732启动时间08:27:11；本轮通用日志文件名时间08:27:15，晚于安装。未启动正式游戏。项目浏览器封面可见，打开EasternSwordCultivator并载入Basic_Level_A。以Shadowheart运行ccStartRespec，选择东方剑修：主职业徽章、一级剑击与两项职业特性小图可见，没有起始配剑选择动作；接受后为12HP。地图御剑术容器的三个变体图标可见，副手变体tooltip大图和原生装备限制可见；普通MAIN_SWORD自定义失败文字本轮仍未直接观察，不能宣称22种提示逐个实测。影心头像为空且日志明确缺Icon_Origin_Shadowheart相机／点触发器；不把这个原版测试关现象归为ESC图集故障。

正常Ctrl+Enter停止Game Mode、Alt+F4退出后，进程检查确认Glasses/bg3/bg3_dx11均不存在。不可变快照 `capture-20261001-084136-305942` 已保存，restore将测试源留存于 `retired-20261001-084204-496348` 并恢复原目录。capture的三个日志类型均标记captured/fresh，旧轮文件仍记录为stale而未用于本轮放行。新通用日志 `log.2026-10-01T08-27-15-966616.txt` 共41,563行；[分析报告](../build/sword-cultivator/toolkit-sixteenth-log-analysis.json)直接归属ESC问题0项、未检测到原生崩溃、分析器退出码0。

本轮仅补一级界面和新日志，当前6DD包的1–3级及四支三级入口直接UI证据来自第十四轮同SHA；第六／七轮四支1–12只作未变核心成长表的历史参考，当前4–12没有重新操作。生产包和源码未重建。正式客户端的小图、模组列表封面和Script Extender战斗／存档验证继续交给用户。

独立agent复核通过后，当前6DD的五项Toolkit门禁已写PASS，build-report的ToolkitTest为pass、GameTest仍pending。随后仅执行 `sword-test-environment.py refresh`：已安装PAK由629更新为同SHA的6DD，旧包在 `test-environment/package-upgrades/` 备份，15个其他PAK／配置文件前后哈希不变。详情见 `game-package-refresh-evidence.json`；没有启动正式游戏或触碰存档。

## 第十七轮：官方 Toolkit 上传与在线封面补齐（2026-10-01）

用户授权上传到 mod.io，并自行完成 Toolkit 认证。网页 Add Mod 明确禁止直接上传 BG3 包；因此按官方发布手册使用 Toolkit Project Settings → Publish。已生成真实 Mod ID `6417135`、文件 ID `8269084`，网页文件版本显示 `1.0.0.2`，仅 Windows 平台，扫描为 `No virus detected`、`Approved and live`。管理页一度显示 Live / Public，随后已保存为 **Live (Private)**；这不是待扫描草稿，也不是公开正式版。

Toolkit 已上传列表封面，但 General Settings → Media 的 Image gallery 最初为空。按官方手册将同一640×360 PNG封面加入图库并保存，模组主页已直接显示封面和中文介绍、外置SE32要求、Just Testing标签及私有状态。结果图在 `build/sword-cultivator/modio-upload-20261001/modio-cover-live-private.jpg`，主页 https://mod.io/g/baldursgate3/m/easternswordcultivator 。**在线封面通过；正式游戏内Mod Manager封面仍由用户复测。**

下载真实在线文件并解包，与冻结6DD包独立比对：在线PAK SHA256 `045051F64F73B04942FB6F2E23F5B57E0DCBE4DFFF0A852883A7C92BEDAB5930`；7个SE文件、14个核心职业/Lists/Stats文件、455个GUI实物资源及封面相同。两语言各269条XML与冻结根LOCA语义相同，官方Adding Localisation允许Mods目录XML布局。TextureBank解码相同。GUI metadata原生重建为188个高质量PNG键，与冻结对应键逐项同；冻结额外566个DDS/LowRes/Illustration键未注册，但实物均保留。不能仅以键数断言坏图，也不能据静态比对宣称低画质/手柄等价；仍待客户端复测。详细报告 `online-8269084-compare-6dd.json`。

正常退出Toolkit，捕获 `capture-20261001-094546-181064`；临时安装已restore，留存 `retired-20261001-094728-504290`。未启动或操作正式游戏、未替换已安装6DD包。构建器重置PublishHandle=0的问题另行修复，避免后续构建丢失真实线上关联。

### 发布关联持久化收尾

构建规格已持久化 `PublishHandle=6417135`，生成器仅修改本模组的ModuleInfo，GustavX依赖的PublishHandle仍为0。新本地包Version64为 `36028797018963971`，SHA256 `1BD21169D0BFCEBFAAD3927979BE2EB481F57B1ED85C0BF7D9E34C33A00AA117`；111/111回归通过，静态错误与警告均0，StatsParser 0诊断，包内meta回读通过。新旧均487项，无新增或删除；内容变化仅发布ID、版本及GeneratedSpec对应字段，两项LSF重新序列化但解码内容相同。原6DD包另存 `modio-upload-20261001/frozen-6dd.pak`。

此关联包未安装、未上传，线上仍为文件8269084／版本1.0.0.2；新版Toolkit和游戏验证均pending，旧6DD门禁结果不转移到新SHA。具体证据见 `modio-upload-20261001/publish-handle-persistence-report.json`。仓库根AGENTS.md已加入用户要求的“遇到不确定事项先查官方资料及手册，再参考社区经验，最后进行可撤销实验”的工作规则。
