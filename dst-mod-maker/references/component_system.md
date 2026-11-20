# 组件体系：判断、落点与现场检索

这份只写**判断与导航**。组件方法签名、参数类型、字段按文件名查 `references/lsp-dst/`（指南 `references/api_signatures.md`）；实现行为、回调时机与行号按符号名 `scripts/grep_source.py` 查当前官方源码。不把 API 清单或行号囤进 skill。

## 1 组件在模组里的位置

- 组件是挂在实体上的 Lua 对象，不是全局系统：`EntityScript:AddComponent(name)` 加载并实例化 `components/<name>.lua`，构造用 `Class(...)`。官方检索点：`entityscript.lua` 的 `AddComponent` / `RemoveComponent`、`class.lua` 的 `Class`、`components/<name>.lua`。
- 权威组件主要在服务器构造；客户端读对应 `inst.replica.<name>` 或实体 netvar。按实际 prefab 构造路径确认 `inst.components.<name>` 是否在该端存在；例如 `spellbook`、`aoetargeting` 由官方 prefab 在 SetPristine 前挂到两端，用于界面、选点；不可把服务器权威组件当作双端组件。
- 复制链路查 `entityreplica.lua:ReplicateComponent/ReplicateEntity`；依赖 replica 的客户端接线注意 OnEntityReplicated 的就绪时机和后续 dirty 更新，动态容器见 `items_ui.md`，跟随特效见 `anim_symbols.md` §4。
- 一个组件要不要 replica，取决于其权威状态是否需要客户端读取、现有同步通道能否满足；纯服务端状态不强制 replica。

### 新建与修改网络 prefab

- 对照最接近的官方 prefab。常见构造顺序为 CreateEntity → Transform/AnimState/Physics/Network 等共享初始化 → 可见外观、共享组件与网络字段 → SetPristine → 非 mastersim 返回 inst → 服务端组件、Brain/SG、游戏逻辑 → 返回 inst；每个 prefab 按实际功能取子集。纯本地视觉实体不照搬联网构造。
- 自建 prefab 的 assets 与 prefab 依赖随 `Prefab(name, fn, assets, prefabs)` 声明并通过 `PrefabFiles` 加载；路径/结构见 `mod_structure.md`，共享资源和库存图标分别查 `anim_symbols.md`。
- 改已有网络 prefab 时走 AddPrefabPostInit；仅服务端代码在回调中可直接 `if not TheWorld.ismastersim then return end`，构造函数则需 `return inst`。共享声明和客户端表现按真实端别放置；已有 prefab PostInit 的时序见 `engine_invariants.md` §1。

## 2 三条路线，先选再写

| 路线 | 什么时候用 | 落在哪 |
|---|---|---|
| 挂官方组件 | 已有组件能表达这个状态／行为 | prefab 或 prefab postinit 里 `inst:AddComponent("官方名")`，参数现场查 `components/<名>.lua` |
| 改官方组件 | 给已有组件加字段／方法、包装现有方法、给一类实体统一加行为 | `postinit/components/<名>.lua`，用 `AddComponentPostInit(component, fn)`（`modutil.lua`） |
| 自定义组件 | 状态是模组专属、多个 prefab 共用、要独立存档或独立更新循环 | `scripts/components/<名>.lua`，prefab 内 `AddComponent` 挂载 |

判断顺序：仅需对成功行为作出附加响应时先找官方事件（并确认触发时机、事件源、data 与重复触发）；例如 `components/pickable.lua` 的 `SpawnProductLoot` 向 picker 推 `picksomething`，玩家侧可监听，不必改 `Pick`。能挂官方组件就不写组件；需要改组件实例时用 `AddComponentPostInit`，不直接改 `require` 返回的官方组件类；确实需要自己的状态与生命周期才自定义。轮盘与施法见 `spellwheel.md`。

`AddComponentPostInit` 的回调是 `fn(loadedcmp, self)`（`entityscript.lua` 的 `AddComponent`，组件实例、宿主实体），在构造后执行。**覆盖实例方法用 `function self:Method(args)` 直接定义**（`code_style.md` §4）；包装原方法要核对完整形参与返回值，不因已知签名省略后续返回。

复刻组件（`components/<名>_replica.lua`）若是 `return Class(...)` 的类表，可按实际时序选择 `AddClassPostConstruct` 做实例扩展；只有明确需类级方法或更早时序才直接 `require` 修改表。见 `api_patterns.md` §1。

## 3 自定义组件的落地清单

- 文件放 `scripts/components/<name>.lua`，`Class(function(self, inst) ...)` 定义、末尾 `return`。自定义组件在 prefab 内直接 `inst:AddComponent("<name>")` 挂载，不在 modmain 里逐个注册。
- 默认值放构造函数。OnSave/OnLoad 只负责持久状态；查 `entityscript.lua:GetPersistData/SetPersistData` 的空表省略规则，别依赖 OnLoad 总会执行。
- 存档迁移应幂等；实体引用需随存档 ID 恢复，在 OnLoadPostPass 等适当阶段接线。查 entityscript.lua 的读档与引用恢复调用。
- 生命周期按需要实现，符号名现场在 `entityscript.lua` 核对：`GetDebugString`、`LongUpdate`、`OnEntitySleep` / `OnEntityWake`（需要随休眠停更时按 `engine_invariants.md` §1 处理）、`OnRemoveEntity` 之类清理钩子。
- 客户端要读组件状态时，二选一：
  - 写 `<name>_replica.lua` + `AddReplicableComponent("<name>")`（`modutil.lua`），replica 内声明 `net_*` 与 dirty 事件，客户端 `ListenForEvent`；服务端写 `inst.replica.<name>._x:set(...)`。
  - 不写 replica，把状态直接挂到已有实体的 `net_*`（共享 prefab 的构造/PostInit 或 `player_classified`）；在官方组件 PostInit 注入 Get/Set 和事件桥即可。声明 netvar 的路径必须两端都运行，不能仅在服务器组件 PostInit 中声明。两端声明、初始同步与选型见 `api_patterns.md` §2。

## 4 模块边界

复杂的共享业务状态可用自定义组件 + replica + AddReplicableComponent；纯服务端自定义组件无需 replica。已有组件的扩展按 §2；视觉跟随特效见 `anim_symbols.md` §4。

## 5 三层分工

| 层 | 放什么 | 别放什么 |
|---|---|---|
| 服务端 | 权威状态、判定、写 `components`、存档、周期任务 | 依赖 `ThePlayer` / HUD / 本地输入 |
| 网络 | `net_*` 声明与 dirty 事件、RPC 注册与发送、replica | 无必要的高频 RPC、队列堆积与重复请求（超限会丢弃，见 `api_patterns.md` §4） |
| 客户端 | 读 `replica` / netvar、客户端或共享组件、widget、本地特效、预测态 | 写权威状态或访问仅服务端构造的组件 |

## 6 专题入口

轮盘与施法见 `spellwheel.md`；复用组件和自定义状态仍按 §2 选型。世界级玩法与管理组件见 `worldgen.md`。

## 7 现场检索导航（按符号名查，不记行号）

| 要确认什么 | 去哪查 |
|---|---|
| 组件构造、类机制 | `class.lua` 的 `Class`；官方 `components/timer.lua` 是最小范例 |
| 挂载／卸载／复制 | `entityscript.lua` 的 `AddComponent` / `RemoveComponent`；`entityreplica.lua` 的 `ReplicateComponent` / `OnEntityReplicated` |
| 生命周期与存档 | `entityscript.lua` 的 `GetPersistData` / `LongUpdate` / `GetDebugString` + 官方组件的 `OnSave` / `OnLoad` |
| mod 环境 API | `modutil.lua` 的 `AddComponentPostInit` / `AddReplicableComponent` / `AddClassPostConstruct` / `AddBrainPostInit` / `AddSimPostInit` |
| 某个组件的方法签名 | 官方 `components/<名>.lua`、`components/<名>_replica.lua`；注解库 `scripts/components/members/`、`scripts/replica_components/members/` |
| 施法相关 | `spellwheel.md` 中各类官方范例 |

## 8 常见误判

- 把施法当成要单独建一套系统 → 先按第 2 节判断能不能用官方组件 + PostInit。
- 给纯服务端的自定义组件硬配 replica → 只有客户端要读状态才需要。
- 在客户端 SG / widget / RPC handler 里读仅服务端构造的组件 → 用对应 replica 或 netvar；共享组件按自身契约使用。
- PostInit 里新增 netvar 却没补一次初始同步 → 客户端首帧拿到旧值。
- 包装官方**全局函数／事件回调**写死形参 → 用 `function(...)` 全量接参；覆盖组件实例方法则直接 `function self:Method(args)`，别把前者当成通用写法（`code_style.md` §4）。
