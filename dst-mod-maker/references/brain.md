# 生物、大脑与行为

## 修改现有大脑的选型

**判断按改动量与节点是否可定位，不按「哪个更优雅」：**

| 情况 | 做法 |
|---|---|
| 改动少，**且要改的节点有名字** | `AddBrainPostInit("<brain名>", fn)`，在回调里**按 `node.name` 定位**后改 |
| 改动多（大改节点组合、优先级结构、插入大量行为），或目标节点没有名字 | 新建 `scripts/brains/<新名>.lua`，把官方 brain **复制粘贴过来再改**；再 hook 该生物（`AddPrefabPostInit` 或自己的 prefab），用 `inst:SetBrain(require("brains/<新名>"))` **整体替换** |

官方查 `modutil.lua:AddBrainPostInit`、`brain.lua:_Start_Internal`、`behaviourtree.lua:BehaviourNode`、`entityscript.lua:SetBrain`。注意三点：

- 按节点名或可确认唯一的稳定特征定位，避免 children 固定索引；其它 mod 的插入/删除可能改变索引。不能可靠定位时才使用专用 Brain。
- Brain 可能重启，检查 OnStart 和 postinit 的执行次数，防止重复插入节点。
- 替换 Brain 要核对旧 Brain 停止、新 Brain 初始化、原有依赖及其它 mod 对旧类的 hook。自建脑参考同类官方 brains/ 与 behaviours/；按当前源码选择相关节点。

**自定义生物行为的分工**：Brain/behaviour 选择目标、优先级、追逐/逃跑（如 `brains/pigbrain.lua`、`behaviours/runaway.lua`）；locomotor 执行移动请求；SG 处理站立/走跑/攻击等具体状态、动画、动作生效帧、状态打断和退出清理（`stategraphs/SGpig.lua`、`stategraphs/commonstates.lua`）。行为节点在结束追逐时也可调用 `locomotor:Stop()`；SG 内停止移动、锁定动作及退出恢复按状态契约处理。不要写一组仅转发一次调用的函数或另建循环来竞争现有 Brain/SG。冷却可交给 timer 或相关行为/组件，追击过程中持续检查目标和路径，撤退找不到可达位置时结束或重新选择，不强行向不可通行点移动。

## 随从、骑乘与宠物

- 官方检索：`components/follower.lua` + `leader`、骑乘 `components/rideable.lua` / `rider.lua`、驯化 `components/domesticatable.lua`；pet brain 在 `brains/`；`entityscript.lua` 的 `SetLeader`。
- 所有权/跟随 AI/骑乘/忠诚度/跨洞穴迁移/清理是**一条关系生命周期**，要一致设计；注意 `inst.Follower`（引擎 AddFollower 的视觉句柄）≠ `inst.components.follower`（跟随领导者组件），别混；按实际依赖确认同步、读档和首次接线；跨分片关系需验证。

生物数值（血量、移速、伤害）放 prefab 或组件初始化；冷却、目标、关系归对应组件或行为。新建 Brain 用 `scripts/brains/<名>.lua` + `SetBrain`，自定义节点放 `scripts/behaviours/`；官方 `brains/`、`behaviours/`、`braincommon.lua` 是首选参考。
