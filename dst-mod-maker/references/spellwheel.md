# 轮盘指令与施法

适用于物品轮盘、角色/随从命令、魔法书和选点施法。优先复用官方组件与动作链；只有需求超出其表达范围时才新增组件。纯界面轮盘不必套用权威施法链。

## 1 选官方范例

| 需求 | 官方 prefab |
|---|---|
| 物品轮盘、直接指令加选点 | `prefabs/abigail_flower.lua` + `ghostcommand_defs.lua` |
| 魔法书、目标位置与效果 | `prefabs/waxwelljournal.lua` |
| 技能解锁轮盘与不同冷却 | `prefabs/willow_ember.lua` |
| 遥控器、多种 AOE 选点 | `prefabs/winona_remote.lua` |
| 玩家实体上的指令、直接复用原版 Action | `prefabs/walter.lua` |
| 随从命令及动态轮盘 | `prefabs/wobycommon.lua` |

按当前版本读相关 prefab 构造、指令表和消费者；不假定这些对象都有相同的组件或状态图。

## 2 组件与两端分工

- 轮盘组件和选择查 `components/spellbook.lua:SetItems/OpenSpellBook/SelectSpell`；UI 查 `screens/playerhud.lua:OpenSpellWheel` 与 `widgets/wheel.lua`，按实际选中、执行、显示字段实现。
- 【源码】`spellbook` 和 `aoetargeting` 是共享组件的实际例子。薇诺娜遥控器、薇洛火焰及阿比盖尔之花在 SetPristine 前挂载这两者，客户端也需要组件来展示和选择指令；`aoespell` 在 mastersim 分支后挂载，执行权威结果。按照实际 prefab 端别判断，不机械用 replica 替代。
- 指令表元素含 label/onselect/execute；轮盘图形可用 bank/build/anims、图标和背景数据，按当前 wheel.lua 实际字段查。SetItems 接收有序数组；两端同一选择 ID 对应相同指令。动态解锁、替换或增删指令时保持一致排列并处理打开轮盘或旧选中项；避免直接修改共用指令定义表造成实例互相污染。
- `onselect(inst)` 收到轮盘归属实体，可能是物品也可能是玩家自己（Walter）。物品的持有人用 `inventoryitem:GetGrandOwner()` 等真实所有权链查，不能把 inst 直接当 doer。选择时设置本次 spellname、spellaction、targeting 等；切换指令后清除不再适用的旧选项，服务端才设置 SpellFn。

## 3 根据交互选择执行链

| 类型 | 官方入口 |
|---|---|
| 展开轮盘 | `ACTIONS.USESPELLBOOK`，`componentactions.lua` → spellbook/OpenSpellBook → HUD |
| 选中后立即请求结算（无选点） | execute → `ThePlayer.replica.inventory:CastSpellBookFromInv(inst)` → 库存、预测及官方 RPC → 服务端 `ACTIONS.CAST_SPELLBOOK` → spellbook:CastSpell(user) |
| 选中后复用已有动作 | onselect 中 `SetSpellAction(ACTIONS.<名>)`；同一库存请求构建 BufferedAction 时优先选这个 action，例如 Walter 的 DISMOUNT/RUMMAGE |
| 选中后在地图场景中选坐标 | execute → playercontroller:StartAOETargetingUsing(inst) → POINT/CASTAOE → 服务端 `aoespell:CastSpell` |

【源码】`components/inventory.lua:CastSpellBookFromInv` 依据选中 ID 调用 SelectSpell、读取 GetSpellAction，再 PushAction；nil action 退回 CAST_SPELLBOOK；`actions.lua:ACTIONS.CAST_SPELLBOOK.fn` 校验物品归属及 CanBeUsedBy，并回调 CastSpell。客机入口见 inventory_replica、inventory_classified、playercontroller:RemoteCastSpellBookFromInv 和 networkclientrpc.lua；选点链见组件动作 POINT、CASTAOE 与 aoetargeting。

立即施法的 UI execute 优先使用上表 inventory replica 入口：它根据是否有权威 inventory 选择本地结算或远端请求。直接调用 RemoteCastSpellBookFromInv 会跳过主机分支（其实现受 not self.ismastersim 限制），不能作为两端通用入口。

优先用现有 action/handler/state，满足需要就无需额外 hook。要新增或改施法动作状态时，查 SGwilson 与 SGwilson_client 中 CASTAOE/CAST_SPELLBOOK 的 ActionHandler、deststate、具体状态；需要预测的自定义表现按 `stategraphs.md`，动作注册规则按 `actions.md`。

## 4 冷却、限制和恢复

- 轮盘的开放资格、可选状态和实际结算是不同阶段。客户端展示/选点只读可用状态，服务端执行时重新核对使用者、物品所有权、选中指令合法性、技能、目标/距离、资源与冷却，避免取到已失效的指令或重复结算。直接复用的官方动作也要确认其条件适用于本功能。
- 动态增删指令要核查 `spellbook:SelectSpell` 失败时的旧状态，以及 inventory:CastSpellBookFromInv 是否检查选择结果；避免使用失效 ID 沿用旧 spellaction/SpellFn。
- `components/spellbookcooldowns.lua` 管理冷却；查 `prefabs/player_common.lua` 与 `prefabs/willow_ember.lua` 的 RestartSpellCooldown/IsInCooldown/GetSpellCooldownPercent。按 `widgets/wheel.lua` 的 checkcooldown、anims.cooldown/disabled 配套字段提供真实轮盘状态，不能把轮盘禁用态当作服务端冷却校验。
- 检查指令切换、关闭轮盘、物品转移/卸下、目标变化、受击/死亡等路径；有瞄准、音效、动作锁定时按实际生命周期清理。复用官方已有 UI、动作和 RPC 优先。

## 5 扩展已有轮盘

先查指令表是否共享、函数是否在加载时被局部缓存及动态刷新时机（官方范例 abigail_flower.lua / ghostcommand_defs.lua）。选择真实消费者处的 hook，避免修改共享定义而影响其它实例。
