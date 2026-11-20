# API 签名检索指南

## 1 来源

`references/lsp-dst/` 是 b1inkie/lsp-dst 的 LuaCATS 类型定义库，许可见内附 LICENSE（MIT No Attribution）。内容为供 Lua Language Server 使用的注解，含名称、类型、参数、字段与中文说明，可快速定位对应官方文件。它没有运行时实现，可能与当前游戏版本不同。

## 2 从注解定位

| 路径（相对 lsp-dst/） | 内容 |
|---|---|
| `scripts/components/members/`、`scripts/components/def.lua` | 组件类、字段及组件索引 |
| `scripts/replica_components/members/` | replica 类 |
| `scripts/widgets/methods/` | UI 控件 |
| `scripts/global/`、`scripts/global/methods.lua`、`scripts/env/` | 全局类、函数与 mod env API、环境注解 |
| `scripts/lan/` | PrefabID、tag、component、event、recipe 等枚举 |
| `scripts/ent/`、`scripts/utils/` | 实体及工具类 |
| `scripts/sys_components/` | 引擎侧方法，如 `AnimState.lua`、`Transform.lua`、`Follower.lua` |
| `scripts/map/` | 地形、room、task、静态布局相关注解 |
| `scripts/constant/`、`scripts/types.lua`、`scripts/noparent.lua` | 常量、类型、全局变量 |

## 3 读注解

按文件名或符号搜索，只读取需要的类和方法块。组件类与 replica 可能继承基类，成员不一定都写在子类。idk 表示类型未知；遗留、弃用、不确定标记与当前版本行为须回源码核实。事件数据可在 scripts/lan/event_data.lua 定位。

上表路径均相对 Skill 的 `references/lsp-dst/`，与官方安装包的 scripts 目录不同。比如 AnimState 注解从 Skill 根目录打开 `references/lsp-dst/scripts/sys_components/AnimState.lua`。

```bash
rg -n 'DoDelta|SetAbsorptionAmount' references/lsp-dst/scripts/components/
rg -n 'wilson' references/lsp-dst/scripts/lan/
```

## 4 查官方实现

- 注解用于定位，实际调用、签名、字段、名称、枚举和行为按当前游戏源码确认。引擎侧没有 Lua 实现时核对当前原版调用、注解及资源结构；无法确认的行为如实说明，用户进游戏验收。
- mod env API 按 methods.lua 的文件提示和 modutil.lua 定位；组件及 replica 按 `components/<名>.lua`，网络变量查 netvars.lua，生命周期查 entityscript.lua、entityreplica.lua，专题入口查 `feature_map.md`。
- 使用 `scripts/locate_scripts.py` 定位当前安装，`scripts/grep_source.py` 查符号的定义、调用者与原版例子。源码包与注解不一致时优先当前源码；历史解包仅作备用并注明版本差异。
