# 物品、装备、容器、物品栏与 UI

## 接入与导航

| 目标 | 官方检索 |
|---|---|
| 物品、装备、所有权与库存范围 | `components/inventory.lua`、inventoryitem.lua、equippable.lua 及 replica |
| 容器容量、UI | `containers.lua:params/widgetsetup`、container.lua、container_replica.lua、`widgets/containerwidget.lua` |
| 控件与 HUD | `widgets/`、`screens/` 中目标类，modutil.lua:AddClassPostConstruct |
| 图标或贴图 | `anim_symbols.md` §5 |
| 配方与扣料 | `crafting.md`、builder.lua |

## 容器与库存

- 扩展共享 params 在 `postinit/containers.lua`，WidgetSetup 按配置设槽位；服务端组件与客户端 replica 一致。动态切换容器用实际同步状态 + dirty 与 OnEntityReplicated 处理变化及首次接线。
- 新增背包类装备的装备/卸下与开关容器流程查 `prefabs/backpack.lua` 的 onequip、onunequip、WidgetSetup 及回调注册。
- 容器配置可能共用表，改一类容器先查引用关系（例如 params.icepack 和 params.backpack），复制目标配置再修改。实际容量取 widget.numslots 或 slotpos；超过原版容量限制时核对 `containers.MAXITEMSLOTS` 与 `prefabs/container_classified.lua` 的槽位池，构造前在两端一致调整。
- 查物品归属和位置时区分 CanAccessItem、GetGrandOwner、FindItem/FindItems、IsHolding 及 replica；是否含装备栏、打开或溢出容器按当前 inventory 实现核对。制作检查与扣料使用同一输入范围，查询的实际副作用也要核实。
- 对进出物品栏的逻辑，查 inventoryitem.lua 的 OnPutInInventory、OnRemoved/OnDropped、ClearOwner，以及 inventoryitem_replica.lua:SetOwner；属性 setter 可能同步副作用，不能只看赋值一行。按真实所有权及 limbo 变化顺序安装 hook。

## UI 与动态显示

- AddClassPostConstruct 在 _ctor 后执行。需改构造期首次调用的行为时要检查实际调用点；可参考 `widgets/itemtile.lua:HandleBuffFX`。真正的类/纯表修改按 `api_patterns.md` §1 选型。
- UI 从 replica、netvar 或已确认存在的客户端组件读取；dirty → 本地事件 → widget 刷新。一次性事件不能替代可恢复的持久开关状态。
- 区分联网图标修改（ChangeImageName）与客户端局部覆盖（SetClientSideInventoryImageOverride），查对应官方调用；图集注册见 `anim_symbols.md`。
- 物品栏附加动态效果查 itemtile.lua 的 ToggleShadowFX/HandleBuffFX；制作栏相近链查 recipe.lua/recipetile.lua 的 fxover；检查文本查 inspectable.lua 的 GetStatus 与 stringutil.lua。
