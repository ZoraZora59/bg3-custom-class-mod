# 东方剑修正式模块：验证契约与证据矩阵

更新：2026-10-01。本文件由独立验证 agent 编写；UI证据由主 agent 维护。依据 `docs/20-eastern-sword-cultivator-gdd.md`，逐招参照 `docs/19-skill-specifications-draft.md`，玩家描述参照 `docs/21-player-facing-skill-text-draft.md`。

## 证据边界和测试顺序

1. 生成数据、原生 StatsParser、LSX/LOCA 与封包回读检查。
2. 实际生产 Lua 在确定性模拟 BG3 边界上的契约测试。
3. 当前 **EasternSwordCultivator** 在 Toolkit 内导入、加载、职业和升级编辑器及原生日志测试。
4. Toolkit 验证通过后，正式游戏客户端测试；SE事件签名、伤害钩子可写性、动作、路径、控制、资源 UI 和存读档必须在客户端验证。

第一、二层成功只证明数据和对应模拟语义。旧 `SkeletonToolkitTest` 的编辑器、游戏证据不构成本模块通过证据。首次游戏 Mod 列表识别只证明列表读取模块元数据，不证明职业和战斗可用。不得把 `Rules.lua` 算术正确替代 Runtime 生效验证。

## 可复现自动测试

- `python scripts/test-sword-cultivator.py` 运行静态、纯规则及真实生产 Engine/Runtime 监听器的模拟边界测试，任何契约失败返回非零。
- `scripts/tests/esc_engine_fixture.lua` 仅伪造实体、Osiris 和 SE事件边界，生产 Rules、Engine、Runtime 原文件原样加载。
- `scripts/tests/test_esc_bridge.py` 在模块加载时固定 Lua 源快照，避免测试过程中重新读取一半新一半旧实现。
- `build/sword-cultivator/regression-report.json` 保存实际测试数、失败、错误、跳过、case IDs及生产Lua/GeneratedSpec SHA256。测试过程中源文件变化时也判失败。
- 测试不伪造 native 命中骰、原生状态生命周期、墙/门路径或 Toolkit 源导入；这些仍需编辑器/客户端证据。

2026-09-29 首次桥接运行13项：10项通过、3项失败；合并主suite共28项，25项通过3项失败。原型 `Runtime.lua` SHA256 为 `316ae017c3f1b6f3cf19de1f5eefb52b7e53dff7a17e0caf2b0bcc01f1972895`。失败为重复 SessionLoaded 引起双倍战外癫狂衰减、相扶可治疗中立对象、剑术攻击和DC加值被全局赋予。已反馈给 Runtime agent。此记录是原型缺陷证据，后续最新结果以带SHA的JSON为准。

## 最新自动契约证据

当前构建 `EasternSwordCultivator.pak` SHA256 为 `6DD25F0AB73B5CF1994233F34D46AD6A4EC173B405BB0F253663CB0C25D6ED75`，22,784,703字节、487项；主 suite **106/106通过、0失败、0错误、0跳过**，StatsParser 0诊断，PAK回读、AtlasReadback和CoverReadback均PASS。`build/sword-cultivator/regression-report.json`保存实际case及生产源SHA；`build/sword-cultivator/build-report.json`绑定当前包。第十三轮`356E...`日志发现5次条件提示映射缺失，已补22条原生映射及中英文本；第十四轮6DD界面复验已完成；该轮通用日志沿用第十三轮，故**当时**`editor_log`仍未通过。第十六轮新鲜日志已独立重算：41,563行、直接ESC问题0、未见原生崩溃，足以补该日志证据；当前包总Toolkit门禁JSON已由主agent更新为同SHA五项PASS。此前`629ADB...`五项PASS和`356E...`FAIL保留为各自包的历史证据。静态与模拟测试不能替代正式游戏中小图、动作和存档验证。

第六轮新增独立静态断言：剑元／癫狂四资源状态、五职业徽章的高低清PNG与DDS共72条路径均有物理文件、格式文件头及Noesis GUI MapKey；155个原生技能的 `TooltipDamageList` 不含条件 `IF(`。这覆盖第五轮已见缺图／Tooltip原生限制的源码侧修复，不宣称Toolkit渲染已通过。

### 第五至十二轮 Toolkit 日志与退出证据

只读分析器 `python scripts/analyze-sword-toolkit-log.py --log <保存的日志> --output <JSON路径>` 把可直接归属 `ESC_`／`EasternSwordCultivator` 的诊断按问题去重，保留每次出现的原始日志路径与行号；原版无归属噪声不计为本模块错误。四项合成测试检验去重、条件Tooltip与状态错误、原版噪声和崩溃门禁。分析器返回0只表示**该日志**未见本模块错误且未见原生崩溃，不能证明界面和玩法正确。

| 保存的Toolkit日志 | 本模块直接诊断 | 退出证据 | 客观状态 |
|---|---|---|---|
| 第五轮 `capture-20260930-191754-063463/logs/log.2026-09-29T13-23-52-390660.txt` | 6类：4种资源图路径缺失（24/20/10/36次）、`Projectile_ESC_taixuan_zhaoxi` 条件Tooltip不支持10次、`CE_Status_ESC_MAIN_SWORD_False` 条件错误对象缺失1次；完整行号见 `toolkit-fifth-log-analysis.json` | 日志末尾原生access violation，Noesis／`UninstallGameUI` 栈；Windows事件1000：2026-09-29 13:52:11 `Glasses.exe`／`CoreLib.dll` `0xc0000005` 偏移`0x93371`，Report ID `ef2df1e1-7a47-4c6b-8b8e-8ccd46802ce8` | 模块诊断FAIL，退出FAIL，整体FAIL |
| 第六轮 `capture-20260930-200105-722737/logs/log.2026-09-30T19-38-21-608000.txt` | 0类；此前目标缺图／条件Tooltip错误未在此日志出现 | 日志第561635行起原生access violation，栈含Noesis与`ls::ResourceManager::UninstallGameUI`；Windows事件1000：2026-09-30 20:00:28 `Glasses.exe`／`CoreLib.dll` `0xc0000005` 偏移`0x933eb`，Report ID `920767ca-8c97-4762-861f-8939da3633eb` | 模块诊断“未观察到可归属错误”，退出FAIL，整体Toolkit仍FAIL／部分完成 |
| 第七轮 `capture-20260930-204420-311008/logs/log.2026-09-30T20-08-20-492359.txt` | 1,016,338行，直接ESC问题0类；完整证据见`toolkit-seventh-log-analysis.json` | 第1,016,259行未处理异常，第1,016,262行`EXCEPTION_ACCESS_VIOLATION`，Noesis第1,016,281／283行，`UninstallGameUI`第1,016,289行 | 四支1→12升级界面已由主agent同版完成；模块诊断“未观察到可归属错误”，退出FAIL，Toolkit总体仍FAIL |
| 第八轮 `capture-20260930-215321-662466/logs/log.2026-09-30T21-44-14-954571.txt` | 103,685行，直接ESC问题0类；独立重跑分析与保存的`toolkit-eighth-log-analysis.json`完全一致 | 日志无原生崩溃，主agent确认Alt+F4后Glasses正常退出 | 五项正式Toolkit case均PASS，仅适用于旧PAK `6EE20F...`；新包待同版复测 |
| 第九轮 `capture-20260930-234739-263044/logs/log.2026-09-30T22-23-40-822297.txt` | 126,871行，`toolkit-ninth-log-analysis.json`直接ESC问题0类 | 日志未检测到原生崩溃；主agent确认正常停止Game Mode并Alt+F4，Glasses/bg3进程均已退出 | `E34EEB...`源创角、一级与二级UI获实测；当时只观察金色徽章，未对照源PNG，后续第十轮已纠正“generic”误判 |
| 第十轮 `capture-20260930-235754-524631/logs/log.2026-09-30T22-23-40-822297.txt` | 生成`toolkit-tenth-log-analysis.json`，126,871行、直接ESC问题0类；**该日志与第九轮capture逐字节相同** | 主agent确认正常停止Game Mode、Alt+F4、无Glasses/bg3进程；复用日志不能独立证明本轮无日志异常 | `8E6B81...`源Karlach一级职业UI、描述和图标实测；未接受升级，整体门禁仍待第十一轮同包验证 |
| 第十二轮 `capture-20261001-003234-760301/logs/log.2026-10-01T00-11-47-847560.txt` | 159,281行，`toolkit-twelfth-log-analysis.json`直接ESC问题0类 | 日志无原生崩溃；主agent确认Ctrl+Enter停止Game Mode、Alt+F4正常退出且Glasses进程消失 | 当时`629ADB...`包一级至三级及四支三级选择实测；严格五项Toolkit门禁PASS，完整边界见下文 |

第五至七轮退出崩溃的根因和是否由ESC触发均未证明。恢复测试目录后，旧Skeleton工程载入时也发生`KhonsuBinding.dll` `0xc0000005`。驱动更新后第八轮同源编辑器正常退出；这不追溯改写旧轮故障。第六轮太玄和第七轮其余三支覆盖了当时同源1→12升级UI；比对三个capture，477项中475项哈希完全一致，仅重新生成的GUI metadata/UI LSF二进制不同。第八轮capture的477个实物文件与清单SHA一致。第八轮五项Toolkit case当时均PASS，但只绑定旧PAK SHA256 `6EE20F4D0BDDB5FDCE1254C9DBB68BC90C1B0977648DB645B58287D1A6989F84`；随后`629ADB...`使用第十二轮同版门禁，不沿用第八轮旧SHA；当前`6DD...`包不能沿用前述任何门禁。完整UI原始记录由主agent写在`research/N-eastern-sword-toolkit-runs.md`。

第七轮曾为诊断测试提供显式退出崩溃override，绑定更早的`83E273...`包；当前新包不能使用它或旧`6EE20F...`的Toolkit报告放行。正式游戏旧包首测后测试环境已恢复，第九轮之前Toolkit新源安装活动，现已捕获并恢复；第十二轮已为当时的`629ADB...`包完成同版Toolkit验证；当前`6DD...`包已用第十六轮新日志补齐同SHA门禁；主agent随后仅刷新本模块安装PAK。正式游戏旧包已创建角色并进入鹦鹉螺，但一级职业法术／被动为空，故**G-01仅部分完成且未通过；G-02至G-12仍无通过证据**。

第九轮已捕获并恢复Toolkit安装。主agent在Toolkit内用Wyll `ccStartRespec`选择职业：1级Starter、剑击和两项被动可见，接受后进入地图为12HP；以Ctrl+Shift+L升2级并接受后为20HP，调息、气护图标可见。Toolkit `Publish Local`原生包实际生成成功。`build/sword-cultivator/native-toolkit-export/comparison.json`与[文字对照](../build/sword-cultivator/native-toolkit-export/comparison.md)表明原生包和脚本包的五个核心ClassDescriptions／Progressions／SpellLists／SkillLists／AbilityLists文件逐字节相同。原生包GUI metadata只注册188个PNG键，其中主职业PNG键指向缺失文件，虽同包有DDS但该DDS键未注册；这是客观文件契约差异，**不能推断金色徽章是引擎fallback**。脚本包的meta本地化和GUI DDS键更完整，不应把原生包直接替代脚本包。旧`toolkit-validation.json`仍只绑定`6EE20F...`，新包门禁待重验。

第十轮`8E6B81D10163146EB6EC1B5B0B59FB8026474956FE4DBF9DC7B54C20D95F9120`源中，主agent以Karlach（Zariel Tiefling）重洗选一级剑修；主类金色圆环剑徽章与当前Source `GUI/Assets/ClassIcons/ClassEasternSwordCultivator.png`（300px）实体经图像比对形状一致，Starter、剑击、两项被动出现，中文职业描述正确。此轮**未接受角色、未升级**，不能借用第九轮Wyll的HP证据称本轮已过2级。`ProjectSettings`中文Description仍乱码；BOM探针失败后已撤销，改以安装副本ASCII XML字符引用处理，效果待后续验证。`build/sword-cultivator/toolkit-tenth-core-continuity.json`只读比对当前`629ADB...`源与第六／七轮：Public及Editor的ClassDescriptions、Progressions均逐字节相同，四支1→12的核心成长表UI历史证据可作同表参考；Public三类Lists与旧轮不同（37个Name从0变全有），旧UI证据不能证明新版Lists语义。当前源10个对应文件与第十轮capture均同SHA。第十轮日志是第九轮复用文件，不能作为第十轮独立日志通过证据。第十一轮将以最新包重新做正式Toolkit门禁和LocalPublish；G-01至G-12仍待新包正式客户端验证。

### 第十二轮当前包 Toolkit 放行边界

第十二轮生成的`toolkit-validation.json`五项PASS绑定当时PAK SHA256 `629ADB849FA98A5777AF28C746549732B8415498B6243A77582943238FFAC57D`。主agent在Astarion `ccStartRespec`观察主类徽章、中文描述、起始赠剑、剑击戏法和两项职业被动；接受一级为12HP，Ctrl+Shift+L升级接受二级为20HP及两戏法，三级为28HP。太玄、天倾、血魇、行歌四支在三级逐一选择，徽章、中文描述、能力出现；接受行歌三级，热键栏显示相应能力。第十二轮独立日志159,281行无直接ESC问题或原生崩溃，正常退出由主agent确认。`capture-20261001-003234-760301`的507个清单文件均与实物哈希一致；当前包481个同名文件与capture逐字节一致，另3个是Toolkit改写的meta、GUI metadata、UI LSF，不能将其称为原包逐字节相同。核心10文件与当前Source同SHA。

四支1→12完整升级UI并**非**本轮重新执行：太玄是第六轮，其他三支是第七轮。`toolkit-twelfth-continuity.json`与`toolkit-tenth-core-continuity.json`证实当时Public／Editor职业及成长表和Editor Lists表与旧轮逐字节相同；Public三类Lists仅新增37个`Name`字段，其当前1→3入口已由第十二轮直接实测。此组合当时足以放行`629ADB...`包进入正式游戏测试，但不证明4→12新版Lists运行、Script Extender回调、战斗机制、资源消耗或客户端创建。G-01至G-12尚无当前包通过证据。

### 当前6DD包：小图与起始配剑修复，第十六轮新日志已验证

用户在前版`629ADB...`正式客户端观察到：主职业徽章、御剑术tooltip大图正确，但角色创建页和热键栏的动作／戏法／被动小图缺失；游戏模组列表封面仍为X。只读封包对照确认前版图集LSX与TextureBank引用`ESC_Icons.dds`，PAK实物却是`ESC_Icons.DDS`，属于**大小写精确路径不一致的真实缺陷**。该缺陷与小图丢失相符，但尚未通过同包单变量游戏复测证明唯一因果；`Icons_`文件名前缀并无原生强制证据。

当前`6DD...`包回读中仅有精确小写`ESC_Icons.dds`，1024×1024 DXT5、11级mipmap；图集LSX的Path／UUID与独立`Content/[PAK]_Generated_<模块UUID>/<图集UUID>.lsf`一致，解码TextureBank的SourceFile、Type=1、SRGB=false、Streaming=true、1024×1024×1尺寸一致。它采用本机已安装Witcher／Saber模组的独立纹理资源形式，旧`Content/UI/[PAK]_ESC_UI/_merged.lsf`已消失。106项自动契约与AtlasReadback通过，说明修复进入包；正式客户端小图仍需用户复测。

现从职业初始装备直接取得普通长剑，不再授予四个一次性起始配剑`Shout_ESC_StartingSword*`按钮：新PAK中四个Spell定义和授予引用均为0。保留惰性`ESC_STARTING_SWORD_CHOSEN`状态供旧存档反序列化；Runtime在`SessionLoaded`只移除这四个旧Spell，不删除已选武器或旧状态。桥接测试覆盖旧档重复加载不重复移除。封面`mod_publish_logo.png`与当前`thumbnail.png`字节相同，后者与原`cover_lineage`缩放为640×360后的源图像素相同，CoverReadback PASS；这只证明包内封面有效，**游戏模组列表X仍待用户复测**。mod.io关联或缓存是否影响该列表仅是推断，没有直接证据。

第十四轮主agent以Wyll在当前6DD源直接实测1–3级（HP12→20→28）、四支三级徽记／中文描述／动作／戏法／被动小图，接受行歌后热键栏图标可见，起始配剑按钮不再出现。问路副手变体显示需要副手剑，近身剑术主手变体显示需要气剑模式；普通MAIN_SWORD失败提示未直接观察。正常停止Game Mode并退出；`capture-20261001-020412-062917`已保存和恢复。[连续性JSON](../build/sword-cultivator/toolkit-fourteenth-continuity.json)复核509项物理哈希，包Mods/Public485项存在、482相同、3项安装meta／重编译LSF语义差异有说明。新增22条条件提示跨表和本地化一致；未变职业／成长表仅沿用第六／七轮历史1–12界面。第十四轮通用日志与第十三轮完全相同，旧5条错误既不是本包新错误也不能证明本包无错；**这是第十四轮的历史日志缺口**。正式游戏G-01至G-12均待用户验证。

第十六轮仍为同一6DD PAK。主agent另见Toolkit项目封面、一级职业图标、剑击与两特性，接受后12HP和御剑术三个图标；原版影心头像缺触发器不能归给本模块。本轮未重新走二／三级和四分支，其完整当前包UI证据仍来自第十四轮。[第十六轮连续性JSON](../build/sword-cultivator/toolkit-sixteenth-continuity.json)核验不可变capture `capture-20261001-084136-305942` 509项实物SHA，506项与冻结Source逐字相同，安装meta仅英文描述fallback，另两LSF在Toolkit编译后语义与PAK一致；与第十四轮仅两LSF二进制改写，职业／成长／Lists及22条件映射源完全同SHA。`capture.json`的`log_evidence`标记本次三个日志均在安装时点后新建，文件大小与SHA逐项复核；独立重跑 `analyze-sword-toolkit-log.py` 与[保存的分析](../build/sword-cultivator/toolkit-sixteenth-log-analysis.json)完全一致：主日志41,563行、直接ESC问题0、原生崩溃0。采集器的时间界线使用安装时间；主agent另外直接读取Glasses启动时间为08:27:11，正常停止／退出由主agent观察。此日志证据补足第十四轮陈旧日志缺口，当前同SHA `toolkit-validation.json`五项已PASS；第六／七轮4–12界面仍仅历史连续性，正式游戏未因Toolkit日志而通过。

### 正式客户端首轮：旧包失败与新版待复测

主agent使用旧PAK `6EE20F...` 创建`ESC_Test_01`并进入鹦鹉螺；本地化职业名称／描述、职业徽章显示正确。一级职业Actions、Class Features、Cantrips页为空，唯一可见火焰箭来自高精灵原生种族；地图通用栏另有原生授予的`Shout_ESC_StartingSword`，所以不能说全部进阶授予失效。Starter选择提示错误继承回气／回血说明。`build/sword-cultivator/game-first-log-analysis.json`对原`Extender Runtime 2026-09-30 14-00-35.log`的1,107行作只读归并，记录**234次SE错误**：`ExecuteFunctor`对不存在的`AttackTargetContextData.Source`／`TargetContextData.Target`／`SourceContextData.Target`访问共28次，实体`.Item`无效访问206次。该日志门禁FAIL，不能将角色成功入图等同职业功能可用。

文件级调查发现旧PAK与第八轮Toolkit capture的14个Stats／Progressions／Lists／ClassDescriptions文件逐项SHA相等，已安装旧PAK与构建包相等，排除简单漏包；正式`SpellLists`35项、`SkillLists`和`AbilityLists`各1项均缺`Name`，而Toolkit Editor表自动补`Name`，原版SharedDev对应节点都有此字段。这是职业页能力缺失的结构候选，但地图通用栏已有Starter原生授予，不能断言全部进阶失效；须新版客户端复测确认因果。新版已在三类正式Lists补37个`Name`、清空Starter继承的Tooltip字段并修正Runtime代理访问；新PAK构建报告为21,176,099字节、SHA `E34EEB...`、94/94回归、StatsParser 0诊断、封包回读PASS。这些只证明修复已入包；`toolkit-validation.json`仍指向旧SHA，新源Toolkit和正式客户端结果待采集。

| 新增实际生产桥接／原生数据契约 | 模拟／静态验证结论 | 边界 |
|---|---|---|
| 太清开域先更新buff，再调用重点3次气剑；血海开域＋3后续调用4次 | 通过 | 捕获实际 `Osi.UseSpell` 调用，未伪造其命中和原生执行 |
| 15层投入15，攻前snapshot命中7，72原生伤害→234；后续按0层防护 | 通过 | 真实BeginCast和Damage监听器，原生命中骰需游戏测 |
| 同阶段两次1伤Functor合并，仅2元、1治疗、1血衣；每Hit两type合计取整 | 通过 | 真实回调账本；原生marker顺序需游戏日志确认 |
| 15层增伤1.75倍，1+1原伤同阶段合计3，下一阶段重新合计3 | 通过 | 真实阶段百分比累计，不把每Functor1.75分别取整成2 |
| 持剑者外职业FireBolt、装备独立燃烧不算剑击 | 通过 | 指定原生SpellId／StatusId归属负例 |
| 45%转伤在队友自定义盾后、行歌30%防护后结算；中立不转、transfer不递归 | 通过 | 真实Defense与Osi.ApplyDamage4参调用；fixture只模拟最终native扣HP，原生TemporaryHp与HP事件顺序待游戏 |
| 8点Fire/Cold原伤转3：ApplyDamage分别Fire1/Cold2，本人30%减伤合计2 | 通过 | 原伤害类型保留、接收方只对总额取整；装备原生抗性／免疫尚未模拟或实测 |
| 同舟只向3名实际party发选择请求；客户端选择后server验证再调用免费clone，中立不调用 | 通过 | 真实UI按钮／NetMessage／候选选择及clone；原nativeAP/装备被动仍需游戏 |
| 零伤Hit仍创建问路标；重复同Hit不重置资格，新施展才重置 | 通过 | 真实标记与每人奖励账本 |
| 仗剑AOE含全部原affected victims、不含旁观敌人；重施不重置已用资格 | 通过 | 执行真实延迟1ms回调后捕获echo调用；原nativeaffectedtargets仍需游戏 |
| KilledBy重复只奖一次；SessionLoaded重复仅一次实际战外衰减 | 通过 | 真实监听器及旧／新定时器token执行 |
| 受控自救客户端按钮发网络意图、server撤销时隐藏；伪token/其他peer/无BA/不足剑元均拒绝 | 通过 | 真实BootstrapClient、NetMessage及server授权函数，ImGui与通信边界mock |
| 战中非自己的回合不能用自救；战外可；双click只付一次；行歌7级不开启 | 通过 | 真实own-turn、等级、费用检查；nativecontrolled状态UI仍需游戏 |
| 每个stats value和每次AddBoosts字符串长度上限2048 UTF8bytes | 通过 | Stats限制由真实Toolkit崩溃日志支持；AddBoosts沿用上限属于保守预防 |
| Skill/AbilityLists逗号枚举与原版相同；所有7张Editor tbl/每个stats字段与正式源相等 | 通过 | XML/原生txt语义值比对，不替代Toolkit引擎枚举及UI导入；DefaultValues Skills单独比对映射 |
| 每支每级AddSpells名单严格符合GDD，共同表不漏入召剑/气剑/5级行歌解控 | 通过 | 独立GDD预期，不调用生成器的spells_at映射来断言自己 |
| 兼职进入专用AddSpells只授予共同剑击，保留起始选择排除；1级没有额外+2/+1 | 通过 | 静态成长选择器，不证明实际兼职／重洗界面 |
| 护体反击每次可选、无Reaction费用、反击不会再次反击 | 通过 | Native Interrupt定义／助手费用与排除条件静态契约，实际每段弹窗待游戏 |
| 一线天倒序伤害事件仍按几何位置衰减，力场免疫不占位，恢复Hit原始伤害 | 通过 | 真实监听读Hit.Damage.TotalDamage、Force索引14；模拟原伤101且已减到1，近敌101/远敌50/免疫0；穿墙及gear bypass待游戏 |

Toolkit 中已发现过纯静态检查未覆盖的真实阻断：日志 `E:/SteamLibrary/steamapps/common/Baldurs Gate 3 Toolkit/log.2026-09-29T12-48-42-414752.txt` 第355行，GSTNodeStorage不支持超过2048bytes字符串，请求2665bytes，随后原生StatsObject/ParseDataLine崩溃。已将这个真实界限加入回归契约。能力／技能列表曾使用分号，Toolkit把整串作为一个enum；原版逗号格式已经加入契约并修复。**当时91项通过仍不构成Toolkit已通过的证据**；后续第六至十轮结果见上文，不能把历史缺口当成当前结论。主agent在 `research/N-eastern-sword-toolkit-runs.md` 维护当前UI证据；本agent没有操作Toolkit或游戏。

### 后续增量审查：禁止沿用前轮全通过

生产监听诊断开关、1000条有序记录上限、输出JSON后关闭，同阶段两次1点受击在血魇11级合计损失1HP，真实 `Target_OffhandAttack`／`Projectile_OffhandAttack` 副手剑正例与非剑主手负例，盾／中重甲暂停自动拒控和旧token救援，恶意JSON parser抛错的权限负例均已加入真实生产桥接；这一批曾67项全部通过。

新增155招原生源的合法27点推荐属性（五职业）、推荐洞悉/察觉、天剑父容器免费而主副jump子各付一次AP+10元、真实impact保留W+26d8和DEX豁免半伤静态契约通过。乘风／回风以实际被援助队友为3m中心、排除施法者附近但远离队友的敌人、乘风选择副手助手的调用契约通过。首次重复同action的 `CastedSpell` 验证发现合作奖励和助手被执行两次；Runtime已加finished守卫，同一case复测两次事件仍只回3元、只调用两名原目标各一次。感知攻击属性覆盖已按本机原版SHILLELAGH/PactWeapon方式改为实际剑item的独立boost归属，不作用角色／弓；主副各自比较合法原属性，盾暂停／脱剑撤销的桥接契约通过。

native agent依据本机原版确认此前W技能多数缺 `ExecuteWeaponFunctors(MainHand/OffHand)`、副手melee应使用 `MeleeOffHandWeaponAttack`。第五轮源已修：所有实际W命中原生成功functor按手执行，WQ模式只有非气剑条件执行，纯Q不执行；副手近战攻击类型正确、单体目标半径3m，不存在非法 `MeleeOffHandWeaponRange`。独立静态契约通过。StatsParser或模拟UseSpell调用仍不能证明原生装备被动已经触发，需客户端实测。

### 第五轮冻结桥接新增契约

| 契约 | 自动证据 | 仍需原生验证 |
|---|---|---|
| 同舟协同候选可选武器／单体伤害戏法，放弃可切换排队请求 | 真实client按钮发意图，server一次授权后调用cost/CD清空clone；重复点击只一次；原招费用保留 | 实际UI权限路由、费用、命中及装备触发 |
| 协同拒绝伪token、其他peer、unknown、多目标、surface/explosion/extra projectiles、超距、本职业收费Level0招 | 真实候选函数、原生解析字段和NetMessage负例通过 | 真实SpellBook和原生Functor对象投影 |
| 协同实时重验party、hostility、alive、控制、line-of-sight、owner原turn；坏JSON不抛错 | 所有负例通过；旧nonce过期，新轮新请求仍可成功 | 联机peer归属及墙／实际被控状态 |
| failed/reload清理临时命中；failed之后迟到CastedSpell不赠机会；partial持久state安全默认值 | 真实CastSpellFailed／SessionLoaded及新／partial state通过 | 取消施法与原生费用提交顺序 |
| 无生15层花15，后新得2层，续招命中仍快照7 | 实际baseline1＋临时snapshot6，不叠加到8 | native投射回调与roll-time boost顺序 |
| 近战槽持剑不把普通主／副手弓误算剑击；御剑职业投射仍合法 | 普通弓不饮血／回元／杀敌奖励，classyujian正例通过 | 原生throwSword metadata |
| 行歌原生普通剑落空也恢复一次，免费clone亦一次，重复CastedSpell不二次；持盾暂停 | 真实Finish监听、meta.originalSpell与装备负例通过 | 原生常态攻击事件路由及AP费用 |
| 太清20%和团队30%可增益队友直接FireBolt，但不叠自己15层癫狂、不饮血 | 模拟原100伤→150；自回元／HP不变 | 外部buff与原生法术伤害钩子 |
| 域持盾暂停，脱盾在原expires恢复；暂停期间照常过期时钟，不续时 | 真实Equipped/Turn/Unequipped后原expires不变 | 原生持续status显示与秒/turn同步 |
| 分担ApplyDamage可嵌套完整Deal/Before/Dealt，不反向奖励／污染cast.targets | fixture额外模式模拟继承原action、SpellId最不利上下文：原10伤只2元及ceil25%=3HP一次；4点转伤本人DR后2HP | 实际ApplyDamage事件是否嵌套及native减伤／护盾顺序 |
| 感知与武器原属性较高者兼容Pact/SpellCastingAbility，排除自有override递归 | 实际weapon BoostsContainer读外部CHA+6：WIS+4不盖、WIS+8可盖；SpellCastingAbility→CHA仍+6，外部附魔状态移除后恢复本职WIS；E.sword(nil)安全 | 原生BoostContainer实体投影及附魔状态事件时序 |
| 共同近身剑击主副手原生定义必须非空，不能只因继承名就判可用 | 两手真实Attack/实体W/HitMarker/weaponfunctor、3m与AP1独立正契约通过；气剑positive与negative均要求太玄或血魇实际branch，1–2级残留QI标志不会开放 | 真实命中／伤害、武器与感知roll时机、重洗状态 |

## 正式设计覆盖矩阵：初始原型审计基线

下表记录初始原型的缺口定位，新增桥接后对应项目的最新模拟证据见上一节。它不把后续未测机制自动判为通过。“模拟已检”不表示游戏通过；“待检”禁止判为已实现。

| 设计承诺 | 已有自动证据 | Toolkit 必验 | 正式客户端必验／原型缺口 |
|---|---|---|---|
| 1–12本职成长、四支3级选择、4/8/12专长、启蒙术替换 | 成长链、容量和专长节点静态已检 | 创建职业、每支3→12逐级界面，能力/专长共存 | 全程升级、兼职职业level与ClassLevel不混淆；不保证13–20 |
| 初始技能七选二、剑类熟练、初始普通长剑 | 初始装备`EQP_CC_ESC`与长剑静态已检；四个旧赠剑Spell已退役 | 技能选数与初始装备可见；旧按钮不再出现 | 初始长剑可用、旧档武器不丢、手动双持副手仅一次bonus常态 |
| 82静态图片、80图集映射、连城v2选中、DDS透明通道 | 当前包精确小写路径、独立LSF、11级mipmap、80键及CoverReadback已检 | 当前Toolkit一级至三级和四支入口小图已出现；本轮新日志待补 | 游戏热键栏小图、成图清晰、alpha边缘、状态图、长描述、模组列表无X丢图待用户复测 |
| 剑元6→50、百分比回元向上取整、上限、费用失败原子性 | 实际Engine资源Row模拟已检；纯规则成长已检 | 容量UI/费用工具提示 | 战中战外调息、治疗3→4级费用替换、存读档、重洗 |
| 成长HP×分支倍率、兼职只倍本职部分、重洗清理 | Engine3级太玄extra25和退出职业模拟已检 | 生命字段/成长表 | Constitution变更、兼职其他职业HP、额外HP不再倍；必须客户端测 |
| 持盾暂停、太玄行歌中重甲暂停、天倾血魇熟练、失剑支援可用 | Engine攻击/支援分离模拟已检 | 技能条件文字 | 暂停范围不能错停非职业技能，已经释放持续效果保留 |
| 感知或原武器较高值，仅剑术攻击和DC加值 | 全局boost污染负契约已检（原型失败） | 原生统计解析 | 非剑/其他职业法术完全不获剑术bonus；非灵巧原武器STR与感知比较 |
| 连贯出剑3/4或2；额外完整AP整套，单次额外攻击1 | 纯机会函数已检 | 原生额外攻击/被动可读 | 实际AP/bonus/reaction数量、Haste/ActionSurge、单次extraattack |
| 御剑飞行bonus、独立24m、不扣普通移动、3m起飞门槛 | 纯距离函数已检 | 原生路径参数 | 可落脚/封闭门/墙/沟壑、飞行途中接近敌人合法；原型未接起飞验证 |
| 太玄照隙零伤命中仍标、自己的后续attack+2/20%/破抗留免疫 | 仅伤害比例纯规则已检 | 标记状态/source条件 | 归属隔离、免疫/抗性/装备、护体和剑域也生效；原型标记效果未桥接 |
| 太玄护体强弱系列、弱招不续强招、每独立来袭可选免费反击 | 守护过期/弱不刷强生产监听模拟已检 | 护体图标及原生reaction结构 | 玩家可选、落空/减伤事件、18m、每阶段、反击不递归；原型只有ready标记 |
| 四轮太玄/血魇剑域：开域＋随后3轮；第4先过期 | 实际Runtime domain状态时钟及纯4次算术已检 | 周期载体/光环状态 | 真实4次落剑、开域先展开20%buff、即时离开移除、重点可选；原型无周期伤害 |
| 天倾击退/减速/破甲各最强独立计时、弱效复归 | 待检 | 原生SpellSuccess和Save条件 | 天崩主目标附14d8；免伤友方仍不能受cc；原型多人主目标缺口 |
| 天倾9级余威敌回合、4轮40%增伤/25%减伤 | 纯乘加规则已检 | 技能和状态 | 敌方轮开始6d8、持续失剑保留、倒地结束；原型无周期与实际移动 |
| 天倾终极友/中立25%、自己免伤、三段独立命中/首次cc | 待检 | 每段定义与目标类型 | 每敌每段、多段阶段归属、控制仅敌；不会重复触发主target特效 |
| 血魇癫狂15、received实际HPloss、阈值+2、盾吸收无层 | 原生damage边界零HP loss模拟已检，纯边界阈值已检 | 数值与投入选择器 | 背景DoT也受伤积狂、主动耗血不重复；伤害钩子字段live验证 |
| 7/12投入0..held、消耗前attack/伤害快照、消耗后防护剩余 | 纯snapshot15→attack7/3.25x已检 | 选择0..15可见性／本次容量 | BeginCast早于原生roll、取消返还/费用原子性；原型aliases未接 |
| 血魇同剑本体+附加伤害合并一次饮血/回元/血衣；每段每敌单独 | 追加生产事件多Functor合并契约 | 原生段与HitMarker顺序 | shields/overkill都计、装备独立DoT排除、斩杀once；原型每Functor奖励错误 |
| 燃血非致死、HP阈值不能支付、+4不重复获得受伤层 | 生产cast监听模拟已检 | 受伤时可以发动／失败提示 | 费用不触发其他转伤、生命费用原子性；原型按GuaranteedSetHP需live检查 |
| 战外6秒衰减、战内不衰减、死亡倒地清零、reload不双定时器 | reload双衰减负契约已检（原型失败） | 状态显示 | 重新进战立即停止、存读档恢复、定时器重复保护 |
| 行歌并肩仅实际party3m、范围即时更新、多个不叠加 | 待检 | party/距离状态定义 | 临时友善NPC不获partybuff；多个行歌11替换且离开移除；原型未桥接 |
| 问路零伤命中标、每party首次成功跟进奖励、重施重置唯一例外 | 纯资格规则已检 | 标记与tooltip | 实際武器/直接法术命中、source、多段一次、同舟奖励取较高者；原型未桥接 |
| 主动疗伤/保护/解控协作奖励只对实际party；自用不奖 | 自治疗不奖模拟已检，中立被治疗负契约已检（原型失败） | TargetConditions | actual恢复/实际解除时才奖励；被动并肩绝不奖；防止event+cast双奖励 |
| 同舟免费普通武器/单体戏法：无AP/bonus/reaction消耗，自身miss也引导 | 待检 | 可选攻击/戏法来源 | 合法范围/墙/原生passive/装备实际触发；原型无协同attack桥接 |
| 风雨转伤：队友减伤盾后40/45%、本人再防护、非递归、排除HP费用、多个取最大最近 | pure share/挑选规则已检 | 状态/图标 | 环境DoT也覆盖、实际party限定、两行歌不循环、治疗增益不增自愈；原型无转伤 |
| 仗剑每人每轮一次、多段合一次、零伤命中也触发、AOE仅原affectedtargets | 待检 | echo隐藏native攻击定义 | ownturn重置、重施不复位、同舟可触发、不自递归、多enemy只奖励一份；原型无echo |
| 前三支3级控制save优势+4，4级preapply反应once，5/8自救例外 | 控制清除函数待event契约 | Controlled下bonusUI可以操作、nativeinterrupt | StatusAttempt实有4参数；preapply阻止必须live证明，afterRemove不等价；原型after remove缺口 |
| 一线天30×2穿墙、无roll、忽略DR/抗性留免疫，免疫不占衰减位 | 纯line/falloff已检 | 路径/target/functor | 几何排序、first每后half向下取整、墙、immune/DR；原型native只有固定伤害 |

## Toolkit 放行清单

每条必须关联实际当前源版本、Pak SHA及日志/截图；出现失败先修再复测同版本。

| Gate | 所需实际证据 | 当前独立证据状态 |
|---|---|---|
| TK-01 | 选择正式ESC项目，source Mods/Public/Editor项目能加载，无fallback至旧Skeleton | 当前6DD第十四轮正式项目载入、封面和Basic_Level_A可见 |
| TK-02 | 原生StatsEditor刷新全部stats，日志无解析/引用/enum错误 | 当前6DD构建StatsParser 0；第十六轮新鲜原生日志无可归属ESC错误 |
| TK-03 | 新建ESC1→2，3级四支正确，4/8/12专长选择同时保留各级能力 | 当前6DD一级至三级接受、四支三级入口实测；更高级专长界面仅为旧成长表历史证据 |
| TK-04 | 四支分别升级3→12，无空级、入门御剑术替换、容量50 | 第六／七轮历史1–12界面；第十四轮连续性报告确认成长表同SHA，本包未重跑4–12 |
| TK-05 | 剑元及技能/状态图标、tooltip绑定，至少桌面与手柄资源 | 当前6DD小图、四支入口、热键栏和两类条件提示已显示；手柄交互未实测。正式游戏小图和封面X待用户复测 |
| TK-06 | Toolkit native保存/导出与最终正式pak对应，引用和版本一致 | 第九轮Publish Local是历史证据；当前6DD PAK SHA及回读、16轮509项capture实物哈希和14轮同SHA核心连续性已核验。16轮新日志41,563行无本模块诊断或崩溃；正式同SHA门禁JSON五项PASS |

## 正式游戏必须保留的测试case

客户端只有在当前版本Toolkit gates放行后开始；新测试角色/测试存档，原14模块包与原modsettings须恢复。

- G-01 1级创建、入侵鹦鹉螺开场进入地图、技能说明和图标。旧`6EE20F`包已完成角色与入图／本地化／徽章，一级法术和被动为空、Starter提示错误，故case未通过；旧`629ADB`包另观察到小图缺失；当前`6DD`包已通过上述Toolkit门禁并仅刷新安装PAK，正式客户端复测由用户进行。
- G-02 每支3/4/5/6/7/8/9/10/11/12级完整成长、4/8/12属性/专长。
- G-03 四支无装备基础、五类剑与特殊剑、双持、副手、盾/护甲禁用、失剑持续保留。
- G-04 AP完整机会与单次extraattack、bonus疗伤/副手、24m独立飞行门墙。
- G-05 聚焦实际日志验证伤害钩子的DamageList顺序、每段nativehit、盾/overkill/zero-hit、抗性免疫及最终四舍入。
- G-06 多人source标记与光环、太清/血海四次、余威敌回合、域倒地停、受控保留。
- G-07 XY15层全投入无生6段，伤前快照attack7，总乘数3.25；后续0层防护；6元或3层回潮。
- G-08 XG三名party、友善NPC中立，免费协同后仍保有AP/bonus/reaction，问路同次奖励一次；仗剑每人一次及不递归。
- G-09 两XG分担与盾后环境/DoT，比例最大最新，生命费用无转移、转移不再递归；self-heal不受增益。
- G-10 控制12种、preapply反应once、受控自救能够选择且正常支付资源；剩余持续源下一次重施可生效。
- G-11 兼职、重洗去职业、存档/读取、SessionLoaded重复、outcombat6秒一次、重进战停止。
- G-12 同版本重新封包SHA回读、ScriptExtender日志无Lua异常，测试环境恢复校验原modsettings/14pak哈希。

### 第十三轮UI与日志补充

`356E...`包在Toolkit实测一级至三级（HP12→20→28），四分支逐个选择，动作、戏法、被动小图与接受行歌后的快捷栏均可见，起始配剑按钮已移除。正常停止并退出，快照为`capture-20261001-012422-497745`。182,990行新日志无原生崩溃，但存在5次`CE_Status_ESC_MAIN_SWORD_False`错误对象映射缺失，`toolkit-thirteenth-log-analysis.json`为FAIL，因此不能部署该包。正式游戏后续测试由用户完成。

### 当前包交接

主agent在同SHA Toolkit门禁通过且游戏／Toolkit进程关闭、松散源码恢复后，仅刷新已安装的EasternSwordCultivator.pak，旧629包已备份。读回SHA与6DD构建一致，15个其他PAK／配置文件前后SHA相同；证据为 `build/sword-cultivator/game-package-refresh-evidence.json`。本动作没有启动正式游戏或修改存档。游戏封面、小图和SE机制仍待用户验证，GameTest保持pending。

### 2026-10-01 用户实机反馈及封面调研

用户确认游戏内技能图标正常显示；未逐一列出等级／分支，因此只记已反馈图标恢复，不将全部G-01／战斗契约判通过。用户提供的游戏内“已安装”页面截图显示本模块名称和中文描述正确、封面为X、右侧详情转圈。当前包SHA仍为6DD，封面显示问题尚未解决；反馈记录为 `build/sword-cultivator/game-user-icons-cover-feedback.json`。

[Larian官方发布指南](https://docs.baldursgate3.game/Getting_Started:_Publishing_a_Mod)要求项目Name、Description、Thumbnail，明确Publish Local仅生成PAK不上传mod.io，并说明发布后mod.io Media会展示在游戏内Mod Manager；文档没有承诺本地PAK的mod_publish_logo.png会成为已安装列表封面。[mod.io媒体API手册](https://docs.mod.io/restapiref/#add-mod-media)将logo作为线上Mod媒体上传，PNG/JPEG、最大8MB、至少512×288、推荐16:9；本项目640×360 PNG满足这个通用规格，但满足格式不等于游戏本地显示。

社区一手经验：[Reza head作者jerinski在2025-04-05的答复](https://www.nexusmods.com/baldursgate3/mods/1384?tab=posts)说明本地PAK可在游戏内管理器出现、可正常使用，但无thumbnail且标third party；其2025-04-29随后表示已发布mod.io。该经验支持线上条目关联解释，不是游戏全部读取路径的规范。本机其他已安装Mod都有非零PublishHandle，多数不含包内logo；本模块PublishHandle=0，包内封面与Toolkit原生发布封面均有效。综合证据最支持在线条目关联缺失，尚不能证明绝无本地fallback。

只读提取本机Game.pak的ModBrowser XAML：Lib_Keyboard.xaml第314行列表图绑定MainScreenshot.Screenshot，第697行安装详情绑定SelectedMod.MainScreenshot.Screenshot；这些控件没有直接引用本模块封面路径。MainScreenshot由原生视图模型提供，此次未证明其填充和fallback顺序，故不能把XAML等同“必须公开发布”的定论。此次未改包、删缓存、伪造PublishHandle或发布Mod。
