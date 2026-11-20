-- modmain.lua 骨架
-- 入口只放按序 modimport("main/...") 清单，不直接导入 postinit/。
-- GLOBAL.setmetatable(env, {...}) 放 main/init.lua 第一行；补了元表后所有文件直接裸写全局名。
-- env.modimport 路径相对模组根目录、不带 .lua。
-- 文件划分见 references/mod_structure.md 与 references/feature_map.md；写法见 references/code_style.md。

modimport("main/init")

-- 按实际功能取舍，不硬凑：
-- modimport("main/tuning")
-- modimport("main/language")   -- 先选择并导入中文/英文文字文件
-- modimport("main/components")
-- modimport("main/actions")    -- AddAction 使用已加载的 STRINGS.ACTIONS + 转发
-- modimport("main/recipe")
-- modimport("main/prefabs")    -- 仅有 prefab hook 时建，由此转发 postinit/prefabs；PrefabFiles 在 init
-- modimport("main/stategraphs") -- 转发本次需要的两端 SG hook
-- modimport("main/widgets")    -- 转发 postinit/widgets
-- modimport("main/rpc")                -- RPC 单独成文件
-- modimport("main/patches")
-- modimport("main/skins")

-- 新建/重构推荐 hook（AddPrefabPostInit 等）集中到 postinit/<类型>/<对象名>.lua，main/ 做装配与转发。
-- 注意：按实际执行端和阶段选择 ismastersim 守卫；已知仅服务端执行的回调不用重复套。
