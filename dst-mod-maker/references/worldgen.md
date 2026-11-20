# 世界生成、运行期地图与世界系统

- 新世界使用 `modworldgenmain.lua` 注册地皮、room/task/level、静态布局等；`mods.lua:FrontendLoadMod/LoadMods` 表明该入口也会在前端及游戏加载。检查 `modutil.lua` 的 API 可用范围；需要 WorldSim 的实际生成操作才判断其存在性（如 `rawget(GLOBAL, "WorldSim")`），世界自定义注册仍须按需要在前端执行。
- 【源码】已有世界不会重跑原世界生成。查 `gamelogic.lua` 对 savedata.map 的加载及 `map/retrofit_savedata.lua:DoRetrofitting(savedata, world_map)` 调用，参考 `map/ocean_retrofit_island.lua` 的官方补岛实现。旧档改造由游戏期 `modmain.lua` 转发对应 `postinit/map/`；不能把需要运行期 Map 的代码放进实际 WorldSim 生成过程。
- 同时支持新旧世界时，优先考虑新档生成注册 + 旧档 retrofit；也可确认新档首次加载经过相同权威 retrofit 链后共用一套，前提是符合所需生成效果。两路使用一致的持久化识别条件，避免重载/新档重复生成。
- 改存档地图要联合核对 tile 数据、坐标/边界、topology 与 nodeidtilemap、实体坐标/分片、导航数据及写回时机；按原版实际调用链确认参数。持久标记应随存档保存，已有建筑、船和关键实体须避让。无安全位置时缩小、改址或等待后续加载，不能因所有候选有实体就强行覆盖；写入之前完成全部选址和依赖校验。

## 世界相关功能的检索入口

| 功能 | 官方文件／符号 | 关键分界 |
|---|---|---|
| **世界／地形／事件** | `map/` 下 tasks.lua、rooms.lua、levels.lua、tasksets.lua、worldsettings_overrides.lua | 按生成/游戏期/旧档改造选入口；TUNING 查实际消费者和缓存时机 |
| **海洋／船／海钓** | boatphysics.lua、boat.lua、sailing 组件；oceanfishingrod.lua、oceanfishinghook.lua、oceanfishingtackle.lua、physics.lua | 船是移动平台，区分世界坐标和平台相对坐标；钓鱼按竿、钩、饵的调用链定位 |
| **农耕／植物／再生** | growable.lua、pickable.lua、farming_manager.lua、plantregrowth.lua 的 TimeMultipliers/SetRegrowthRate 等；entityscript.lua:LongUpdate | 区分生长、收获、枯萎、离线推进与世界再生，核对休眠和存档；数值放实际组件初始化或 prefab |
| **建筑／部署／物理** | prefabutil.lua:MakePlacer、deployable.lua、workable.lua、physics.lua | Placer 做预览，服务端最终验证放置与生成；按实际原版参数核对 |

- 地皮定义查 `modutil.lua:AddTile`、`worldtiledefs.lua`、`noisetilefunctions.lua`。世界生成的静态布局看 `map/layouts.lua`、`map/static_layout.lua` 和 `map/boons.lua`；任务和地形关系查 `map/rooms.lua`、`map/tasks.lua`、`map/tasksets.lua`、`map/levels.lua`。修改既有 level/room 优先官方 PreInit。世界自定义与 tile 定义是否需要在前端加载，按 API 实际消费者核对。
- 自定义地皮按 AddTile 的 tile_data（行为）、ground/minimap/turf 定义分别核对实际素材、地面声音、地皮物品及陆地/水面类型；需调整邻接渲染顺序时查 `modutil.lua:ChangeTileRenderOrder` 和其调用的 TileManager。地皮定义、地皮渲染顺序与地图中何时铺设它是不同机制。

## 世界自定义选项与配置

- 只有确需世界级选项时才使用 `modutil.lua:AddCustomizeGroup/AddCustomizeItem`；查 `map/customize.lua` 的 LEVELCATEGORY.WORLDGEN / SETTINGS 及相应选项处理，区分决定新世界生成的数据与读档时持续生效的世界设置。世界生成定义在前端也需可用，不能全部包进 WorldSim 判断。
- 较多的世界开关可采用纯定义表（选项、组、默认值、语言键）作为共同数据源，再分别注册前端展示及运行期消费。改动服务器设置要追 `worldsettings_overrides.lua`、实际配置读取及世界 topology.overrides 的加载时机；不要用读取不到早期世界状态的默认值悄悄替代配置。
- 世界选项与 modinfo 配置如果共用一项语义，确定优先级及 nil/false 的处理，保持默认值一致；精简模组无需额外注册两套界面。

## 世界级玩法、分片与区域生命周期

- 洞穴、分片传送与玩家迁移查 `components/worldmigrator.lua:Activate`、`components/playerspawner.lua` 的 ms_playerdespawnandmigrate 事件、`prefabs/migration_portal.lua`；区分同分片位置传送与跨分片移交，按实际归属、目标分片及读档流程保留玩家状态。分片消息另见 `api_patterns.md`。
- 场景事件、特殊布局和非交互过场按需求查 `scenarios/`、`components/scenariorunner.lua`、`nis/` 和 map/ 的相近原版范例，核对一次性触发和存档恢复。

- 世界级刷新器、季节事件、区域生态、全局计时等有独立状态时，优先挂在实际世界 prefab 的组件上：`forest`、`cave` 或适合各分片的共同构建入口；查 `prefabs/forest.lua`、`cave.lua`、`world.lua` 的构造与 PostInit，按分片和 `TheWorld.ismastersim` 判断。不把每个玩家都挂一份全局计时器。世界级组件仍遵守 OnSave/OnLoad、任务和监听清理（`component_system.md`）。
- 【源码】`prefabs/world_network.lua:MakeWorldNetwork` 构造 `TheWorld.net`，包含双端网络状态与 clock/seasons 等组件；`prefabs/shard_network.lua` 构造 `TheWorld.shard`，断言 mastersim 并 `AddShardNetwork`，承载分片间状态。两者皆 `persists=false`，不要把它们当持久化业务数据的唯一归属。新同步字段核对初始化时间、两端声明、dirty 初始同步及分片权威；普通世界状态用 `WatchWorldState`/已有事件，参照 `components/worldstate.lua`、`prefabs/world.lua` 的使用点。自定义跨分片逻辑仍按 `api_patterns.md` 的 RPC 契约设计，不因某个 mod 使用共享网络实体就推导任意字段能跨分片同步。
- 复杂地图（海洋、洞穴、室内区域）把生成时的数据注册、运行期区域判定、实体与玩家迁移、世界级刷新/事件管理拆开；运行期区域结构先看当前官方 `components/virtualroommanager.lua`。其构造断言 mastersim，世界先创建，区域实体随后通过注册/注销事件登记，实体引用由管理器重建，避免读档顺序问题。设计自己的区域关系时区分持久 ID 与运行期实体引用，核对恢复与移除路径。游戏更新时复核 map 内部函数及 tile 渲染顺序，不默认全量覆盖 worldgen。
