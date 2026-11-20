# 动作系统与地图交互

**非 `instant`** 的自定义动作不是「注册一个 Action 就完事」，是四段闭环，缺一段就点了没反应（`instant=true` 的动作跳过第 ③ 段，见下方分水岭）：

| 段 | 落点 | 现场查（官方／符号） |
|---|---|---|
| ① 定义 | `main/actions.lua` | `actions.lua:Action`、`modutil.lua:AddAction` 查字段与签名 |
| ② 文本 | `main/language.lua` 选择独立语言文件，早于 `main/actions.lua` 加载 | 用已本地化的 `STRINGS.ACTIONS.<ID>` 调 `AddAction(ID, str, fn)`，或赋给 Action 对象 `.str` 后注册（变体表用对象形式，`strfn` 返回对应子键）。见 `modutil.lua` 的赋值契约 |
| ③ 状态 | `postinit/stategraphs/SGwilson.lua`、`SGwilson_client.lua` | `AddStategraphActionHandler("wilson" \| "wilson_client", ActionHandler(ACTIONS.X, state或deststate函数))`；`deststate` 按实际端别读权威组件、replica 或已确认存在的共享组件 |
| ④ 收集 | `postinit/componentactions.lua`（由 `main/actions.lua` 转发） | `AddComponentAction` 的类型由实际交互决定，先查 `components/playeractionpicker.lua` 的点击路由及 `componentactions.lua` 各段回调形参，见下表 |

**instant 与普通动作的分界**：查 `actions.lua:Action`、`entityscript.lua:PushBufferedAction` 和 `stategraph.lua:StartAction`。instant 行为直接结算，可不写 SG handler；新建普通的双端非 instant 玩家动作，需要在 `wilson` 与 `wilson_client` 绑定相应状态。预测态可复用官方已有状态。官方 previewaction 兜底可能仍能发送请求，但不会自动提供自定义预测表现。核对实际 Action.instant 与单次 BufferedAction options 的区别。

**别漏两端**：普通需要客户端参与的非 instant 玩家动作按两端路径注册；AddComponentAction 的收集注册在参与的两端保持一致，避免 ID 映射不同。官方动作也能改：包装 `ACTIONS.<名>.strfn`，或在收集回调里 `table.remove(actions, i)` 剔除不想要的官方动作。

### 组件动作收集：先选交互入口，再定表结构

| 类型 | 玩家如何触发／收集对象 |
|---|---|
| `SCENE` | 直接点击场景目标；收集目标实体的组件 |
| `USEITEM` | 游标持有物品再点目标；收集 active item 的组件 |
| `EQUIPPED` | 装备物品对目标操作；常见鼠标入口收集手部装备组件 |
| `POINT` | 世界坐标，可能有场景 target |
| `INVENTORY` | 物品栏或装备格内的物品操作 |

回调参数和允许条件现场读 `componentactions.lua` 对应收集类型。

【源码】`components/playeractionpicker.lua` 的 `GetRightClickActions` 先判断 `GetActiveItem()`，走 `GetUseItemActions`（`CollectActions("USEITEM")`）；没有 active item 并持有手部装备时才走 `GetEquippedItemActions`（`CollectActions("EQUIPPED")`）。不能仅凭组件名选择类型。例：装备工具后右键建筑用 EQUIPPED，拖着材料点装备充能用 USEITEM；两者不能混。

收集阶段只决定是否展示候选动作，使用两端可读的状态；服务端 `Action.fn` 在实际结算时仍校验正确装备/使用物、目标、材料和有效状态，避免动作排队期间条件变化后继续结算。

用一张按动作类型分组的表统一注册，天然保证「同类型同组件只注册一次」：

```lua
local COMPONENT_ACTIONS = {
    SCENE = {
        inspectable = function(inst, doer, actions, right)
            table.insert(actions, ACTIONS.MY_ACTION)
        end,
    },
    USEITEM = {}, POINT = {}, EQUIPPED = {}, INVENTORY = {},
}
for atype, v in orderedPairs(COMPONENT_ACTIONS) do
    for component, fn in orderedPairs(v) do
        AddComponentAction(atype, component, fn)
    end
end
```

**同一 (actiontype, component) 只注册一个收集回调**，多个动作在其内部统一处理。`componentactions.lua:AddComponentAction/RemapComponentActions` 的回调存储与名称表 ID 分配并非同一操作，重复注册会导致覆盖、重复名称与映射问题。两端用确定顺序注册；`pairs` 顺序无保证，字符串 key 用官方 `util.lua:orderedPairs`（`stringidsorter`），不在遍历中修改表。

### 地图界面右键动作：走官方通道，不要自己发 RPC

按当前官方函数追踪完整链：
 
1. `screens/mapscreen.lua:UpdateMapActions` → `components/playercontroller.lua:UpdateActionsToMapActions/GetMapActions/RemapMapAction`。先读官方 map action（如 `actions.lua:BLINK_MAP`）的字段与对应 POINT 收集；地图关闭和输入由官方处理。
2. 自定义地图动作核对 `ACTIONS_MAP_REMAP` 的映射或 `map_only` 的匹配条件。普通收集成功仍可能无法在地图显示，不能只注册 AddAction。
3. 查 `PlayerController:OnMapAction`、`RPC.DoActionOnMap` 与 `networkclientrpc.lua`。优先复用官方主机/客机、预测和 mod action 的分流，无需另写地图右键 RPC 或劫持 MapScreen。
4. ActionHandler 按 instant 与实际预测路径选择，目标坐标、落点、玩家形态、技能与冷却由服务端实际结算入口重新校验。

动作多时按定义、官方包装、收集表和状态图分类组织；小功能复用相近的官方状态和动作链。
