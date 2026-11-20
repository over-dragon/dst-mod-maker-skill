# 技能树：注册、表现和生命周期

- 新建或扩展技能树查 `prefabs/skilltree_defs.lua:BuildAllData/CreateSkillTreeFor` 和相近角色定义。注册前协调节点、布局、连接及元数据（含 RPC_LOOKUP）；保留原树节点和公共行为，不只修改一个孤立字段。
- `CreateSkillTreeFor` 按 orderedPairs 分配 RPC ID 并生成连接和元数据；两端必须使用一致的节点 ID 与定义。确认技能数量的网络限制、既有树 ID 的兼容性、根节点/locks/connects、defaultfocus、分组布局及实际图标。UI 查 `widgets/redux/skilltreebuilder.lua`、`skilltreewidget.lua`；复用官方 icon 或用 `RegisterSkilltreeIconsAtlas`，按真实资源核对。
- 新增定义可在 `main/skilltree.lua` 声明注册；对原对象的 hook 由 main 转发 postinit。定义创建时的文本来自何处、前端/游戏 UI 何时读表、语言何时可用需现场查，不能笼统认为 AddSimPostInit 一定适合注册所有技能树。
- 技能激活与恢复查 `components/skilltreeupdater.lua:ActivateSkill/DeactivateSkill/GetActivatedSkills/OnLoad/SendFromSkillTreeBlob`，区分节点回调、客户端事件与读档握手；运行期用 updater 的 IsActivated 等接口查询技能，不直接修改 skilltreedata 内部集合。
- 属性、倍率、配方和动作等效果按实际激活状态协调，保证重复激活/取消/读档不叠加、不误清理其它来源；属性变化核对组件 setter、当前值、replica 和 HUD。优先节点回调/已有事件，只有确认存在遗漏的变化路径才补定时核对。
