-- modinfo.lua 骨架
-- 字段以当前 mods.lua / modindex.lua 为准；配置项组织见 references/mod_structure.md §4。
-- api_version 必须等于当前 MOD_API_VERSION（mods.lua:6 = 10）；
-- modindex.lua:627-630 会校验：小于报 Old API，大于报版本超前。

local modid = "my_mod"
local cur = (locale == "zh" or locale == "zht" or locale == "zhr") and "zh" or "en"

version = "0.1"
author = ""
forumthread = ""
api_version = 10

-- priority = 0 -- 加载优先级，越低加载越晚，默认 0
dst_compatible = true
dont_starve_compatible = false
reign_of_giants_compatible = false

-- 端型默认服务器/所有端模组，不主动询问；仅使用者明确要求客户端模组且验证可行时才改用下面那行
-- 判定见 references/workflow.md
all_clients_require_mod = true
-- client_only_mod = true -- 纯客户端时改用此字段，同时关闭 all_clients_require_mod
-- 服务端不强制客户端安装时，两者均为 false；须先验证无客户端代码/资源依赖。

server_filter_tags = {}
-- icon_atlas = "modicon.xml" -- 需要图标资源时才启用，不臆造资源文件
-- icon = "modicon.tex"

-- 中英双语，按 locale 选；description 前缀带版本号。游戏内文字使用 main/language.lua 对应双语。
local LANGS = {
    ["zh"] = {
        name = "模组名",
        description = "一句话说明这个模组做什么",
        config = {},
    },
    ["en"] = {
        name = "My Mod",
        description = "One-line description of what this mod does",
        config = {},
    },
}
name = LANGS[cur].name
description = version .. "\n" .. LANGS[cur].description

-- 配置项默认不加。使用者要求时再往对应语言的 config 里填
-- { name, label, hover, default, options }，由下面生成 configuration_options。
-- 单元素 {"分组标题"} 可作不可选的分组行；共享选项表提到 LANGS 外复用。
-- 注意：读取侧别用 false 作值（overrides or GetModConfigData(...) or default 会把它吃掉）。
-- key 用 modid.."_xxx" 前缀，在 main/tuning.lua 统一读出并写进 TUNING。
local config = LANGS[cur].config or {}
local _configuration_options = {}
for i = 1, #config do
    local options = {}
    if config[i][5] then
        for k = 1, #config[i][5] do
            options[k] = { description = config[i][5][k][1], data = config[i][5][k][2] }
        end
    end
    _configuration_options[i] = {
        name = config[i][1],
        label = config[i][2],
        hover = config[i][3] or "",
        default = config[i][4] or false,
        options = #options > 0 and options or { { description = "", data = false } },
    }
end
configuration_options = _configuration_options
