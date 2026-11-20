---
name: dst-mod-maker
description: 制作、修改、优化、审查、调试《饥荒联机版》（Don't Starve Together / DST）Lua 模组及解释 Mod API。适用于玩法、Prefab、组件、动作、状态图、UI、动画资源、存档、联机同步和崩溃排查，按需查当前官方源码与 API 注解。不用于普通游戏攻略。
---

# 饥荒联机版模组制作

把描述中的每个功能点变成完整、可运行、便于维护的模组。负责需求拆解、方案、源码检索、开发和静态自检；游戏内验收由使用者完成，遇到错误按实际日志继续定位。

## 阅读与执行

**匹配任务和功能后必须实际读取对应资料，再确认官方实现与调用方；具体实现由需求决定。** 只收到技能名称或描述时先打开本文件。复杂任务进入新子系统、改变方案、收到新的纠正或上下文被压缩时，重新读取相关约定；同一阶段已读且仍在上下文中的资料不必反复打开。多阶段工作开始或切换阶段时简短说明实际读取的参考内容、关键官方符号和本阶段重点。资料不可用时说明证据限制。

### 任务路线

下列文件相对 `references/`。按任务性质选择，不必全部阅读。

| 任务 | 必须阅读 |
|---|---|
| 新建模组 | `mod_structure.md` §1–5、`code_style.md`、`workflow.md` §1–2；用 `assets/` 适用骨架，默认建在 `<game_root>/mods/` 不重名目录 |
| 局部修改/优化 | `code_style.md` 相关章节、`workflow.md` §1/§3/§4；保留无关结构和功能 |
| 整体优化/重构（含「优化这个模组」） | `mod_structure.md`、`code_style.md`、`workflow.md` §3.1/§4；分阶段，采用本 skill 结构，无需再次点名 skill |
| 审查/解释 | 按范围读技术专题；结构审查读 `mod_structure.md`、`code_style.md`；签名查 `api_signatures.md`；审查本身不修改文件 |
| 调试/性能排查 | `verification.md` §3、`workflow.md` §5；从第一条相关日志及堆栈追调用链 |
| 发布/游戏更新 | `verification.md` §4、`workflow.md` §6，按影响范围复核机制 |

### 功能路线

多个功能可以组合。读对应专题中涉及的部分及列出的官方入口；未列功能先看 `feature_map.md` 查近似机制。

| 功能 | 必读入口 |
|---|---|
| 配置、数值、语言、入口、modinfo | `mod_structure.md` §2/§4、`code_style.md` §1/§7 |
| 新改 prefab、实体、组件、replica | `component_system.md`、`api_patterns.md` §1；构造、休眠或存档涉及 `engine_invariants.md` |
| 事件、任务、休眠、生命周期、保存/恢复 | `component_system.md`、`engine_invariants.md`、`api_patterns.md` §3 |
| 动作及地图右键 | `actions.md`；状态或预测涉及 `stategraphs.md` |
| 状态图、移动预测 | `stategraphs.md` |
| 联机、netvar、RPC、跨分片、客户端输入 | `api_patterns.md` §2–4；预测另读 `stategraphs.md` |
| 物品、装备、物品栏、容器、UI/HUD | `items_ui.md`；物品图标读 `anim_symbols.md` §5 |
| 配方、科技、制作、食物/烹饪 | `crafting.md`；图标读 `anim_symbols.md` §5 |
| 生物、AI、brain、随从、宠物、坐骑 | `brain.md`；行为状态涉及 `stategraphs.md` |
| 新角色、已有角色属性、出生物品、角色资源 | `characters.md`；技能树或资源组合对应专题 |
| 战斗、游戏内武器、投射物、范围效果、buff、生存状态 | `combat.md`；按实际组件查源码 |
| 角色技能树 | `skilltree.md` |
| 轮盘、施法、选点、角色或物品指令 | `spellwheel.md` |
| 世界、地图、地皮、旧档改造、世界级事件、建筑、部署、农耕、海洋/船/钓鱼、洞穴/迁移、场景 | `worldgen.md`；涉及入口读 `mod_structure.md` §2–3 |
| 动画、symbol、皮肤、特效、贴图、shader、音频/相机 | `anim_symbols.md` 对应章节（含动画解包、图集） |
| 兼容层（用户要求或实际冲突）、多系统组织 | `compatibility.md`、`mod_structure.md` §6 按涉及内容选择 |
| 签名、拼写、枚举、未知 API | `api_signatures.md` → 检索 `lsp-dst/`；行为和时序回官方源码 |

## 事实与源码

- 先用 `scripts/locate_scripts.py` 识别游戏根目录、版本、官方源码和注解路径。
- 签名、名称、字段、类型、枚举：先用 `references/lsp-dst/`（LuaCATS 注解）快速定位，具体导航见 `api_signatures.md`；实际用于实现时核对当前源码或引擎侧调用范例。
- 行为、时序、端别、初始化、网络、兼容：查当前安装的 `data/databundles/scripts.zip` 的定义、调用者和相关原版实例。注解冲突或关键 hook/RPC/netvar/SG 回源码。优先当前游戏源码包，解包目录仅作备用或明确选定的历史快照。
- 不编造 API、资源、bank/build/symbol；交付依据应来自本次查询的源码（文件、符号，按需注明实际行号）或明确证据。【经验】/【引擎侧经验】说明适用范围。无源码时注明行为尚未核实。
- 不主动检索订阅模组库；点名的参考 mod 用于提取组织经验与机制线索，回官方实现核实，避免搬运第三方实现。
- 自撰资料保留检索入口、非显而易见的引擎契约和通用工程范式；具体数值、字段、签名、状态和角色数据从当前源码与实际资源获取，参考文档以文件和符号定位，不维护固定源码行号、版本统计或重复的 API 手册。补充第三方经验时先确认它能改变通用开发决策，再核对官方实现。

## 开发与交付

1. **澄清与规划**：拆解全部功能，明确目标、触发、装备槽、允许/拒绝条件、材料/消耗、共享状态、存档、端别和资源；只问会实质改变方案的问题。默认 `all_clients_require_mod = true`，不主动新增配置、兼容层或美术，优先复用官方资源。局部修改保留无关结构；整体重构保留原玩法、配置、旧档和公开接口（用户明确要求的变更优先）。
2. **选机制**：先查成功行为后的官方事件；需要改行为优先扩展/注册 API，再考虑包装或改类。明确服务端权威、共享声明、客户端表现，按实际 prefab/组件/SG 构造路径判断守卫，校验 RPC 与动作的权威结算，保持注册顺序一致。
3. **编写**：新建或整体重构遵守工程结构。modmain 只导入 main，先 init；PrefabFiles/公共 Assets 集中 init，自建 prefab 正常从 scripts/prefabs 注册并声明自己的 assets；main 转发 postinit。官方已注册可用资源无需公共重复声明。独立中英文文件与 modinfo 的覆盖一致；三个入口按实际职责选择。具体写法见 `mod_structure.md` 与 `code_style.md`。
4. **自检**：以最终代码逐项核对需求、实际加载与官方调用链。每个已实现或改动的功能回查对应专题和关键官方调用点，尤其区分主机与远端路径、状态与资源消费者；不要沿用规划阶段未经核实的结论。按 `workflow.md` §4 使用 `check_mod.py`（新建及整体重构加 `--new-mod`），明确未核实项。Lua 词法扫描和静态解析均不证明游戏运行正确。
5. **交付**：提供可用模组、功能说明、已做的源码与静态检查及针对实际功能的游戏验收提示。游戏测试由使用者完成；出错回传第一条相关堆栈，按日志改根因。技术交流按用户表达和需要展开，不做能力问卷；默认值不替代明确需求。

## 辅助工具

```bash
python scripts/locate_scripts.py --json
python scripts/grep_source.py "符号名" --file "components/*.lua" -C 3
python scripts/check_mod.py "<模组目录>" --new-mod --json
python scripts/unpack_anim.py "<game_root>/data/anim/<名字>.zip" --summary
```

工具仅依赖 Python 标准库。检索可显式传 `--game-root`、`--scripts-zip`、`--scripts-dir`（备用，历史研究用 `--snapshot`），解包器 `-o` 输出 JSON。无 Lua 5.1 解析器时检查器降级为词法扫描并明确未解析，方法与退出码见 `verification.md`。工具按需使用，不安装无关依赖。
