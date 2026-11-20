# 实体生命周期与 Lua 契约

这些是容易误读的机制。具体回调时机和参数回当前源码核对。

## 1 实体、休眠、查找

- 休眠会停用 Brain/SG 等更新，但不要假定周期任务也会自动暂停。读 `mainfunctions.lua:OnEntitySleep/OnEntityWake`、`entityscript.lua:DoPeriodicTask/DoTaskInTime` 与官方 `components/health.lua:StartRegen`。需休眠停更时按实际逻辑处理 IsAsleep 或暂停任务，唤醒时恢复。
- 调度任务把所属实体插为回调的第一个参数，例如 `self.inst:DoPeriodicTask(1, Tick, 1, self)` 对应 `Tick(inst, self)`。重构时核对传参，见 entityscript.lua 与 scheduler.lua。
- 查找目标用 `simutil.lua:FindEntity` 与 TheSim:FindEntities 的实际调用；优先用 tags/canttags 筛选，核对距离排序、可见性及过滤回调参数（如 FindEntity 的 fn(目标, 自身)）。不要遗漏 INLIMBO/FX 等真实排除条件。Lua 无法确定的边界由真实游戏验证。
- 朝向、世界与平台坐标查 entityscript.lua 的 GetRotation/方向向量调用；传送查 `components/blinkstaff.lua` 的 Physics:Teleport 及前后处理。
- 需要逐帧推进的组件查 EntityScript:StartUpdatingComponent/StopUpdatingComponent 与 OnUpdate；能由事件或有限任务触发的逻辑按需选择。
- RemoveFromScene 进入 limbo，Remove 销毁实体并触发移除路径；对玩家或持久实体不要将 RemoveFromScene 当普通视觉隐藏。查 entityscript.lua 的两个方法及 ReturnToScene。
- PushEvent 是本地事件。回调按实际注册实体、事件源、参数和派发顺序判断；查 EntityScript:ListenForEvent/PushEvent_Internal，不能假定跨实体回调顺序稳定。
- AddPrefabPostInit 的执行在 prefab 构造之后，实际下钻 `mainfunctions.lua:SpawnPrefabFromSim` 与 modutil.lua；两端构造的普通网络实体按 `code_style.md` §3 分权威逻辑和共享逻辑。

## 2 Lua 陷阱

- 多返回值在参数列表中间只展开一个，最后一个表达式或直接 return 才可完整传递；配合 select/unpack 保留 nil。
- `inst.F = LocalF` 只是复制函数引用；改 inst.F 影响运行时表查找，不影响文件内直接调用 LocalF 的位置。改函数前同时查定义与调用者。
