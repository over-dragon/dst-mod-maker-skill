# 功能点到专题的检索索引

按功能选择专题，读取相关内容后按其中的官方符号检索当前源码。实现细节以对应专题为准；签名与名称查 `api_signatures.md`。一个需求可能由多个子系统组合。

| 功能/关键词 | 主要资料 | 第一跳官方文件或符号 |
|---|---|---|
| 入口、配置、本地化、modinfo、PrefabFiles | [模组结构](mod_structure.md)、[代码风格](code_style.md) | mods.lua / modutil.lua / GetModConfigData / LOC / worldsettings_overrides.lua |
| 新建或修改 prefab、实体组件、replica、保存 | [组件体系](component_system.md)、[引擎生命周期](engine_invariants.md) | entityscript.lua / entityreplica.lua / prefabs/目标.lua / components/目标.lua |
| 事件、netvar、RPC、分片通信、输入 | [API 与联机](api_patterns.md) | netvars.lua / networkclientrpc.lua / playercontroller.lua |
| 动作类型、右键、地图动作 | [动作](actions.md) | actions.lua / componentactions.lua / playeractionpicker.lua / mapscreen.lua |
| 状态图、动画时序、移动预测 | [状态图](stategraphs.md) | stategraph.lua / stategraphs/commonstates.lua / SGwilson.lua / SGwilson_client.lua / locomotor.lua |
| AI、追逐、逃跑、随从、骑乘、宠物 | [生物行为](brain.md) | brain.lua / behaviourtree.lua / brains/ / behaviours/ / follower / rideable / rider |
| 新角色、角色属性、出生物品与资源 | [角色](characters.md) | modutil.lua:AddModCharacter / prefabs/player_common.lua / tuning.lua |
| 战斗、武器、投射物、范围效果、免伤、增益、生存状态 | [战斗](combat.md) | combat / health / weapon / projectile / complexprojectile / debuffable / hunger / sanity |
| 角色技能树 | [技能树](skilltree.md) | prefabs/skilltree_defs.lua / skilltreedata.lua / skilltreeupdater |
| 指令、轮盘、魔法、AOE | [轮盘与施法](spellwheel.md) | spellbook / aoespell / aoetargeting / spellbookcooldowns / widgets/wheel.lua |
| UI、库存、装备、容器 | [物品与 UI](items_ui.md) | inventory / inventoryitem / equippable / containers.lua / widgets/ |
| 配方、科技、食谱、烹饪 | [制作](crafting.md) | recipes.lua / recipes_filter.lua / builder / cooking.lua |
| 世界生成、地图、地皮、建筑、植物、海洋、旧档、世界管理器、跨分片迁移、场景 | [世界](worldgen.md) | map/ / worldtiledefs.lua / gamelogic.lua / world_network / worldmigrator / scenarios/ |
| 动画、图集、皮肤、shader、音效、相机 | [资源与效果](anim_symbols.md) | anim assets / AnimState / FollowSymbol / SoundEmitter / camera |
| 外部依赖、冲突、兼容 | [兼容](compatibility.md) | KnownModIndex / ModManager / 具体依赖 |
| 自检、日志、性能、更新 | [工作流](workflow.md)、[验证](verification.md) | scripts/check_mod.py / 游戏日志 |
