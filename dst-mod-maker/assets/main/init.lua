GLOBAL.setmetatable(env, { __index = function(t, k) return GLOBAL.rawget(GLOBAL, k) end })

-- 新增 prefab 统一在此列出；不在 main/prefabs.lua 声明。
-- PrefabFiles = { "my_prefab" }

-- 仅声明本模组需公共加载、且未由原版或 prefab 自身负责的资源。
-- Assets = { Asset("IMAGE", "images/my_ui.tex"), Asset("ATLAS", "images/my_ui.xml") }
-- 新 prefab 的动画/依赖仍在 scripts/prefabs/<名>.lua 的 local assets / prefabs 中声明。
