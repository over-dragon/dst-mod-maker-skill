# API 选型与组合范式

原则：**有合适事件时先监听；否则优先官方扩展 API，确实不足再改类或覆盖**。使用者未提出兼容要求时不主动加兼容层。

按需定位相关 API 与调用者，参数查注解及当前官方实现；组件选型见 `component_system.md`。

## 1 hook 清单（检索方向）

| API | 定义位置 | 用途 |
|---|---|---|
| `AddPrefabPostInit` | `modutil.lua`；执行时机在 `mainfunctions.lua` | 对指定 prefab 追加初始化，fn 在 `prefab.fn` 之后跑 |
| `AddPrefabPostInitAny` | `modutil.lua` | 对所有 prefab |
| `AddPlayerPostInit` | `modutil.lua` | 每个玩家生效 |
| `AddClassPostConstruct` / `AddGlobalClassPostConstruct` | `modutil.lua` | `require(package)` 拿类表、包装 `_ctor`，postfn 在原构造之后。**不只 UI**：`widgets/controls`、`components/health_replica.lua` 这类 `return` 类表的模块都可用；模块只是 `return` 一张普通表（无 `_ctor`）时直接 `require` 拿表改，别套这个 API（查 `DoAddClassPostConstruct`） |
| `AddStategraphPostInit` | `modutil.lua` | 图名作 key；装完后跑，可改 events / actionhandlers / states。按图实际构造端判断，不机械加 `ismastersim`（`code_style.md` §3） |
| `AddStategraphState` / `Event` / `ActionHandler` | `modutil.lua`、`stategraph.lua` | 同名后注册覆盖先注册 |
| `AddComponentPostInit` | `modutil.lua` | 改官方组件：加字段／方法、包装现有方法；见 `component_system.md` 第 2 节 |
| `AddReplicableComponent` | `modutil.lua` | 声明自定义组件有 replica |
| `AddBrainPostInit` | `modutil.lua` | 小改且目标节点**有名字**时按 `node.name` 定位；改动多就复制官方 brain 新建再 `SetBrain` 替换，见 `brain.md` |
| `AddTile` / `AddLevelPreInitAny` / `AddRoomPreInit` | `modutil.lua` | 世界生成侧 env 入口，见 `worldgen.md` |
| `AddSimPostInit` | `modutil.lua` | 游戏初始化后执行；用于确实依赖该时机的逻辑，现场核对调用者及世界对象是否已就绪 |
| `AddModRPCHandler` / `AddClientModRPCHandler` | `networkclientrpc.lua`（env 包装 `modutil.lua`） | 两个方向，见第 4 节 |
| `AddMinimapAtlas` / `RegisterInventoryItemAtlas` | `modutil.lua` | 注册小地图／物品栏图集，见 `anim_symbols.md` 第 5 节 |

覆盖前先查目标行为成功时是否已有事件、回调或对应注册 API；改组件实例优先 `AddComponentPostInit`，改动作/状态图优先专用 API。只有需要全局类影响、更早时序或没有合适扩展点才直接改类/模块。

**按生效范围选 hook**：

- 每个玩家都要生效 → `AddPlayerPostInit`；某个角色生效 → `AddPrefabPostInit` 加该角色 prefab 名（如 `wilson`）；`AddPrefabPostInitAny` 对所有预制体都跑，一般用不到。
- 实现背景：`AddPlayerPostInit` 是 `AddPrefabPostInitAny` 外套 `HasTag("player")`（`modutil.lua`）。知道即可，别因此回避 `AddPlayerPostInit`。
- **改单个角色不要用 `AddPlayerPostInit` 挂 `playeractivated` 再筛 `prefab`**：全体玩家都会被挂一遍，直接 `AddPrefabPostInit("<角色名>")`（`code_style.md` §5）。

包装官方方法时应保留原契约：直接 `return old(...)` 会转发全部返回值；后置处理时按当前源码接收并返回全部已知返回值。若需捕获可变数量的返回，Lua 5.1 用 `select("#", ...)` 保存数量及 `{...}`、`unpack(values, 1, n)` 保留中间的 nil，不假定存在新版 Lua 的 `table.pack`。调用参数仍按签名决定，签名可能变化的包装用 `...` 转发（`code_style.md` §4）。

## 2 netvar 选型与同步契约

按当前 `netvars.lua` 的定义、位数与调用者选择最小够用的类型。自定义 prefab 在 SetPristine 与 mastersim 分支前完成双端一致的声明；现有 prefab PostInit 按实际初始化路径处理。

- 具体类型、取值范围及数组上限查 `netvars.lua` 和 `GetIdealUnsignedNetVarForCount`，选能表达实际数据的最小类型；数组及高频变动的状态按实际开销取舍。
- 开关/持久状态用 net_bool 等状态类型，一次性通知用 net_event；按 `netvars.lua` 的 push/set/set_local 区分事件与状态，新客户端重建不能依靠历史一次性事件。
- 【源码】两端声明和顺序必须一致；dirty 通常由实际变化触发，set_local 不同步。根据 `netvars.lua:set/set_local` 查初始化和强制通知契约。
- 声明后按业务需要读写：服务端需要同步初值或状态变化时 `set(x)`，消费者需要当前值时 `value()` 或调用 replica getter。若后来创建的 UI 要立即呈现已有状态，可在绑定监听时读取当前值，例如 `widgets/statusdisplays.lua:OnSetPlayerMode` 用 `GetPercent()` 设置血量。

## 3 事件与同步

- 【源码】`PushEvent` 是本地事件派发，不自动跨网络（`entityscript.lua` 的 `PushEvent_Internal`）。
- 【源码】要双端同步可用网络变量：服务端 `netvar:set` 发生实际变化时双端触发 dirty 事件（`netvars.lua` 的 `netvar:set(x)` 注释）。
- UI 通过 netvar dirty → 本地 PushEvent → 相关 widget 事件监听读取；监听按实际实体或数据筛选。官方参考 `widgets/itemtile.lua`。
- 事件回调签名恒为 `fn(self, data)`，按符号名在 `entityscript.lua` 核对。

## 4 RPC 方向

| 方向 | 注册 | 发送 |
|---|---|---|
| 客户端 → 服务端 | `AddModRPCHandler` | `SendModRPCToServer` |
| 服务端 → 客户端 | `AddClientModRPCHandler` | `SendModRPCToClient` |
| 分片 → 分片 | `AddShardModRPCHandler` | `SendModRPCToShard` |

上述 API 均可在官方 `networkclientrpc.lua` 及 `modutil.lua` 的 env 包装检索；`GetModRPC` / `GetClientModRPC` / `GetShardModRPC` 是对应 ID 查询。

查 `networkclientrpc.lua:RPC_QUEUE_RATE_LIMIT` / RPC_QUEUE_RATE_LIMIT_PER_MOD、HandleRPCQueue、TickRPCQueue 的定义与调用。队列上限针对 sender 的待处理请求，不能当固定发送频率；超限可能丢弃请求。连续上报按需求限频，合并未变化值。

`rpc` 单独成 `main/rpc.lua`，命名空间用 modid；注册与发送按方向配对；各参与端注册名称和顺序一致，避免数字 ID 对不上。

**客户端持续上报**（鼠标坐标、朝向等）：由本地 ThePlayer 周期任务取 TheInput 数据并 SendModRPCToServer；按需用 AddClientModRPCHandler 开关。不要为每个远端玩家挂本机输入任务，停止时清理任务。地图右键优先走官方动作链（`actions.md`）。

**接收端的权威校验**：客户端只发送操作意图和必要参数，服务器用其自己的实体与组件状态判断目标是否存在、类型和数值是否有效、距离/拥有权/权限/冷却是否满足、请求是否仍合法；不可相信客户端的结算金额、伤害、目标状态或重复请求。业务结算集中在服务端入口，预测只做可恢复表现。身份查 handler 实际传入参数，不自行信任 payload 中的玩家标识。GUID 是本地实体表索引，不把一端的 GUID 传到另一端再用 `Ents[guid]` 当作跨端身份；带实体参数的 RPC 要按当前官方序列化契约核对。

**分片**：分片 RPC 是独立世界进程间通信，不是跨客户端调用。按符号查当前 `networkclientrpc.lua` 的 `AddShardModRPCHandler`、`GetShardModRPC`、`SendModRPCToShard` 与接收者。核对发送端/目标 shard、数据格式、世界状态；考虑玩家迁移、目标分片不存在、迟到或重复请求以及存档恢复。共享玩法数据须明确由哪一分片最终结算；没有跨分片需求不新增 RPC。

## 5 相关专题与自检

- 动作与地图右键见 `actions.md`，预测与相机控制见 `stategraphs.md`，轮盘见 `spellwheel.md`。
- 组件端别见 `component_system.md`，物品栏和 UI 见 `items_ui.md`，视觉跟随见 `anim_symbols.md`。
- 回调参数、同步及结构自检统一按 `workflow.md` §4。
