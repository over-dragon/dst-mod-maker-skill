# 状态图、动作表现与移动预测

需要新增或改动作时同时读 `actions.md`；SG 的网络端别按实际构造路径决定。按符号检索定义、调用方及相近的原版状态。

## 先选接入与组织方式

| 需求 | 落点与检索入口 |
|---|---|
| 修改原版已有状态/事件/动作路由 | `postinit/stategraphs/<对象>.lua`，用 AddStategraphPostInit 包装相应 onenter/onexit、timeline 或 handler.fn；保留原契约 |
| 给现有图增加新状态或图级事件 | AddStategraphState / AddStategraphEvent；需要新动作时对应 AddStategraphActionHandler（`modutil.lua`） |
| 新建生物/自有实体 SG | `scripts/stategraphs/SG<名称>.lua`，定义 states/events/actionhandlers，返回 StateGraph(实际图名, states, events, 默认状态, actionhandlers)，prefab 中 SetStateGraph("SG<名称>") |
| 大量相似技能、攻击或移动状态 | 从多个真实状态中提取共有生命周期和变体参数的构造函数，按系统集中管理；服务端与客户端各有对应的生成/装配方式 |

- 生物 SG 首先查官方同类 prefab、`stategraphs/SGpig.lua`、`SGspider.lua`，复用 `require("stategraphs/commonstates")` 所提供的 CommonStates 与 CommonHandlers。如 AddIdle、AddWalkStates、AddRunStates、AddSleepStates、OnAttacked、OnDeath。按实际动画、组件、标签、状态名及参数选择，不机械加整套状态；复用 handler 同时确认它跳转的状态存在。
- 如果默认状态、走跑、休眠、受击与死亡机制已有通用范式，优先调用官方构造函数。复杂同类状态可统一 onenter 的移动停止、攻击准备、目标和超时，timeline 保留每种动画的生效帧，onexit 统一释放锁、清除临时目标和取消未提交动作。只有多个状态实际共享契约时才提取公共函数，变体的特殊中断和清理仍需保留。
- Brain 决定意图，SG 消费移动/攻击指令和管理状态；locomotor 负责移动执行。主动 AI 的目标、追逐和逃跑详见 `brain.md`。

## 状态的组成与生效时机

按实际行为设计 State，而非先复制某个官方完整 SG：

| 字段 | 职责 |
|---|---|
| name / tags | 状态身份、busy/attack/moving 等标记及实际消费者 |
| onenter(inst, params) | 进入时初始化 statemem、处理移动或动画，并设置需要的超时 |
| timeline / onupdate | TimeEvent(n * FRAMES, fn) 对应动画时机；连续更新才用 onupdate |
| events / ontimeout | 动画结束、输入、受击或超时后的状态转换；同时应考虑异常中断 |
| onexit(inst, nextstate) | 离开旧状态时清理其音效、动画覆盖、移动/攻击锁、任务、临时标记等 |

- 【源码】`stategraph.lua:State` 将 tags、events 组装为映射，构造时对 timeline 按时间排序。追加或替换 timeline 项要保持时间顺序，尽量在图级 PostInit 中完成，避免修改正在执行的共享定义。
- 【源码】当前状态的事件优先：`State:HandleEvent` 调用该状态的 handler，若返回非真值，`StateGraphInstance:HandleEvent` 仍可调用图级 handler；仅需要拦住图级默认行为的回调才返回 true。包装原 handler 时保留其返回值。
- 玩家有 BufferedAction 的状态：服务端在实际生效帧调用 `inst:PerformBufferedAction()`，成功/失败后按需求推进；直接攻击等可能走 combat 或其它组件，不能一律靠 BufferedAction。客户端的预测态按官方 `SGwilson_client.lua` 同类状态调用 `inst:PerformPreviewBufferedAction()`，它触发对应的 RemoteBufferedAction 并标记预览（`entityscript.lua`），实际结算由服务端完成。若已选择能满足效果的官方态，复用其原有提交逻辑即可。
- 多阶段状态明确准备、结算与收尾的边界；取消、受击、死亡、正常完成等路径按实际需要清理，以免残留音效、目标、状态锁或重复扣除。状态消费过程中切态时核对下节 statemem 的身份契约。

## 状态图与生命周期

- 【源码】hook key 是图名而非文件名；查 `modutil.lua:AddStategraphPostInit` 与 `stategraph.lua:StateGraph` 的装配顺序。PostInit 在 mod actionhandlers、events、states 合并之后执行，同名注册可能覆盖旧定义；按现有对象包裹，不直接替换无关状态。
- `StateGraphInstance:GoToState` 不替调用者决定 busy 是否允许切态。有效切态先调用旧 onexit，再初始化新的 statemem；即使同名重入也重建 statemem。跨态数据用 sg.mem，持续性玩法数据放对应组件。
- **同步回调可能已经切态**：业务函数返回后仍要确认旧状态是否拥有继续执行的权利。需要时保存 inst.sg.statemem 的身份，回调返回确认实体有效且仍是该次 statemem；仅检查状态名或 sg.mem 不够。核对 `stategraph.lua:GoToState/HandleEvent/UpdateState` 和 `entityscript.lua:PushEvent`。
- 动作变速先分清 SG 的 dt、调度任务、绝对冷却和 AnimState 动画倍率；它们不必共用时钟。按 UpdateState、scheduler 及实际表现调用逐项核对。
- 提交前允许取消、提交后可按需求自然收尾；受击、死亡等硬中断仍应清理。按实际状态设计，不为等尾音阻塞必要中断。

## 玩家状态与移动预测

- 从 `prefabs/player_common.lua:SetStateGraph/EnableMovementPrediction` 确认图名和构建端；查 `stategraphs/SGwilson.lua` / SGwilson_client.lua 的同类 ActionHandler 与 State。服务端处理真实结算；客户端只补需要预测或本地播放的状态，调用 PerformPreviewBufferedAction 而非重复业务结算。
- `server_states`、ServerStateMatches、FlattenMovementPrediction 与超时按当前官方同类动作查（如 `SGwilson_client.lua` 中 chop_start）；客户端不是把服务端状态全部复制一遍，延迟补偿也不由模组自创二选一机制。
- 自定义移动接管或阻塞输入时查 `components/playercontroller.lua` 的 EnableMovementPrediction 调用者、DoPredictWalking/DoDirectWalking、RemotePredictOverrideLocomote；可参考官方 `SGwx78_common.lua` / SGwilson_client.lua 中设备操控状态，按实际 tags 与 onexit 恢复预测。不要套用某个角色专属状态的一组固定 tags。
- 移动速度、走跑和停止直接查 `components/locomotor.lua` 的 WalkForward、RunForward、Stop 及其调用者；状态自己的进入/退出与 Brain 的移动意图相协调（`brain.md`）。
- 预测位置可能早于服务器权威位置；预测和非预测路径应汇合到同一权威动作入口，避免重复结算。
