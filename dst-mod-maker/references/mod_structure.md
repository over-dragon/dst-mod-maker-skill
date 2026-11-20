# 模组结构与文件组织

组织方式只写「该写哪些文件、按什么职责分、为什么」；**API 签名、行号一律现场查官方源码**。功能点到文件的完整映射见 `feature_map.md`，组件层判断见 `component_system.md`，写法契约见 `code_style.md`。

## 1 组织方式怎么选（按功能与依赖复杂度，不照搬某个模组的目录）

目录结构由功能决定，按实际需要的子集取用：

| 功能规模 | 组织方式 |
|---|---|
| 只改官方对象、不新增 prefab | 极简：`main/` 清单 + `postinit/` 打补丁，无需 `scripts/` |
| 新增少量 prefab／组件 | 加上 `scripts/prefabs/`、`scripts/components/`，仍以 `main/` 为装配层 |
| 多系统或自有 brain/widget/screen（依赖复杂时） | 按职责细分 `scripts/` 各目录，`main/` 只做清单、`postinit/` 按对象平铺；重构按 `workflow.md` §3.1 分阶段 |

目录按需求选择；复杂系统的可选扩展见 §6，状态图端别见 `stategraphs.md`。

## 2 modmain.lua 只是入口清单

`env.modimport` 定义在官方 `mods.lua`，路径相对模组根目录、不带 `.lua`。新建模组 `modmain.lua` 仅按依赖顺序导入 `main/` 文件；具体 postinit 由相应 `main/*.lua` 转发，本地化也放装配层。

### env 元表：放 `main/init.lua`，不是 modmain 第一行

`GLOBAL.setmetatable(env, {__index = function(t,k) return GLOBAL.rawget(GLOBAL,k) end})` 写在 **`main/init.lua` 第一行**（第一个被 modimport 的文件）。作用只是让后续用官方 API 时不用写 `GLOBAL.` 前缀。`modmain.lua` 应保持纯清单，别把它写在那里（`code_style.md` §1）。

【源码】`mods.lua:CreateEnvironment` 建立 mod env，`modutil.lua:InsertPostInitFunctions` 注入可用 API；modimport 让同一入口装配的文件共享 env。实际白名单与端别分支现场查。

- 不写这句 → 官方全局要写 `GLOBAL.X`；写了这句 → 读不到的键去 `_G` 查，可直接写 `X`。mod env API 本来就已注入，元表主要补的是其它官方全局。
- **补了元表就全程裸写**，`local G = GLOBAL` + `G.X` 是把元表白设，禁止两种混写（`code_style.md` §1）。
- 因此它是**风格选择，不是必需**；`__index` 只做读回退，赋值仍落在本 mod 的 env 内，不污染全局。
- **三个入口职责不同，env 的身份取决于加载路径**。【源码】`mods.lua` 的 `FrontendLoadMod` 分别创建普通与前端 env；`LoadMods` 则对同一个 mod env 先执行 `modworldgenmain.lua`、非 worldgen 进程再执行 `modmain.lua`。不能依赖另一入口已运行、已补元表或已写入运行期数据；各入口按需使用 `GLOBAL.X` 或初始化自己的装配文件。
- mod env API 直接裸写，只有取官方全局才要 GLOBAL 或元表；按 InsertPostInitFunctions 的生成/前端/运行期分支确认可用入口。

**顺序表达依赖**：`init` 最先；`language` 选择导入 `string_zh.lua` 或 `string_en.lua`，在动作、配方及使用文本的模块前加载。配置与组件注册早于其消费者；`AddAction` 用已加载的本地化值注册，早于动作收集和 SG handler。

按职责切分 `main/` 下的文件（按实际需要的子集取用，不硬凑）：

```
init / tuning / language / widgets / components / prefabs / actions /
stategraphs / stategraphs_client / rpc / patches / skins / recipe / containers / writeable
```

`main/` 是装配层：**`main/init.lua` 单独集中 `PrefabFiles` 和公共 `Assets`**（仅确实需全局加载又未由 prefab/原版负责的资源）；新 prefab 的局部 assets/deps 在 `Prefab` 定义处声明。其他 main 文件只放配置、语言、声明式注册（`AddAction`、配方）与 `modimport("postinit/...")` 转发；`AddPrefabPostInit` / `AddComponentPostInit` / `AddStategraphPostInit` / `AddClassPostConstruct` / `AddComponentAction` 等按对象归到 `postinit/<类型>/<对象名>.lua`。装配层可以只是一个纯转发文件；`main/prefabs.lua` 在有原版 prefab hook 时才建，不能承担 `PrefabFiles` 声明。修改现有模组时尊重原有结构，除非用户要求优化/重构。详见 `code_style.md` §6。

**两端职责分离是引擎要求；文件分开是推荐结构**：`stategraphs.lua` 与 `stategraphs_client.lua` 并列，`rpc` 单独成文件。依据见 `stategraphs.md`。

## 3 顶层目录按职责划分

| 目录 | 放什么 |
|---|---|
| `main/` | init 集中公共资源/PrefabFiles，其余为配置、语言、声明式注册和 postinit 转发；**不放 hook** |
| `postinit/` | **所有**对官方对象的 hook／包装：`prefab` / `component` / `stategraph` / `widget` / `screen` / `brain` / `map` / `actions` / `componentactions`，一文件一对象 |
| `scripts/` | 模组自有资源：`components/` `prefabs/` `brains/` `stategraphs/` `widgets/` `screens/` `map/` |
| `anim/ images/ sound/` | 美术资源，按 `anim_symbols.md` 处理 |

三个入口按执行职责选择：

| 入口 | 职责 |
|---|---|
| `modmain.lua` | 游戏运行期 prefab、组件、动作、SG、UI、存档及旧档改造 |
| `modworldgenmain.lua` | 新世界生成、地皮定义、布局、room/task/level 和相关世界自定义注册；也会在前端/游戏加载，只有实际依赖 WorldSim 的部分才门控 |
| `modservercreationmain.lua` | 建服前端界面及其资源、配置交互 |

后两个仅有相应需求时建立。兼顾新世界和已存世界的地图功能，见 `worldgen.md`；入口按执行时机选择。

小模组不要照搬大型模组的 `levels/` `languages/dlc_strings/` `tools/` 这类目录。

## 4 modinfo.lua

| 字段 | 说明 |
|---|---|
| `all_clients_require_mod = true` | 服务端／所有端模组，**默认**，不主动询问 |
| `client_only_mod = true` | 仅客户端模组；需要且验证可行时才用 |
| `client_only_mod = false` 且 `all_clients_require_mod = false` | 服务端运行、不强制客机安装；仅在客户端不依赖模组代码/资源/协议时采用 |
| `api_version` | 查当前 `mods.lua:MOD_API_VERSION` 及 modindex.lua 校验；不要把缺省值当作当前版本 |
| `name` / `description` / `author` / `version` / `version_compatible` | 常规元信息，字段读取点在 `mods.lua` |

字段与双语／配置写法以 `assets/modinfo.lua` 为准：modinfo 用注入的 `locale` 加 `LANGS` 表生成 `name` / `description`，末尾循环 `config` 组装 `configuration_options`；运行期文本分流用 `LOC.GetLocaleCode()`（见 `code_style.md` §7）。配置项默认不加，使用者要求再加。

### 模组配置怎么组织（使用者要求加配置项时）

模板 `assets/modinfo.lua` 已含完整生成循环，按它的形状扩展即可。

- **表驱动 + 双语**：`LANGS[cur].config` 是紧凑元组数组，每项 `{key, label, hover, default, {{描述, data}, ...}}`；`label` / `hover` / 选项描述随语言各一份。单元素 `{"分组标题"}` 生成一项不可选的假配置项，用来分组。
- **生成循环**：把 `{描述, data}` 转成 `{description=..., data=...}`，`default` 用 `or` 兜底，无选项时给 `{{description="", data=false}}`，最后赋给 `configuration_options`。共享的选项表（如键码表）提到 `LANGS` 外复用，别在两种语言里各写一遍。
- **读取侧**：key 用 `modid.."_xxx"` 前缀；在 `main/tuning.lua` 里用 `GetModConfigData(<同名>)` 统一读出并写进 `TUNING`，别在各处散着调。多系统模组可先收口为自己的命名空间配置表，再写入 `TUNING`，单一入口是 `overrides > GetModConfigData > default`。
- **⚠ 值别用 `false`**：读取常写成 `overrides or GetModConfigData(...) or default`，`false` 会被 `or` 吃掉并回退默认。要布尔语义就用 `"enabled"` / `"disabled"` 之类字符串再归一，或显式判 `nil`。同一配置项若同时出现在世界设置与模组设置，两处 `default` 必须同步（不同步是已经出现过的坑）。
- **端与作用域**：客户端本地配置与主机世界 overrides 是不同来源。查实际配置读取、TheWorld.topology.overrides 的初始化时机及前端语言 API；不直接跨入口假定 locale 或世界对象存在。
- **modinfo 沙箱**：用数值 `for` + `#`，必要时自带 `table_insert` / `my_ipairs` 局部实现，避开全局 `table.insert` / `ipairs`。是否因沙箱缺少标准库**未证实、不作定论**，但照这个写法最稳。
- 更大规模的做法：按全局、开发、客户端配置分组，只在开发版加载调试配置；如果需要识别发布版本，核对模组自己的目录和发布约定。
- 【源码】世界设置经 `worldsettings_overrides.lua:OverrideTuningVariables` 等函数修改 TUNING，官方模块可能在文件顶部缓存 TUNING 值，晚改不一定影响消费者。世界设置与配置项的区别及入口见 `worldgen.md`。

其它字段（图标、依赖、优先级、分类标签）按当前源码复核后再写，**不凭记忆列字段**。端型判定见 `workflow.md` 第 2 节。

## 5 写入规则

1. 新建模组默认在 `<game_root>/mods/` 下创建不重名目录；修改既有模组先定位实际副本并保持原有架构，优化/重构按需求采用本节约定。
2. 复制 `assets/modinfo.lua`、`assets/modmain.lua`、`assets/main/init.lua` 作骨架，按功能增删 `modimport("main/...")` 行，确保每个启用的 import 都有实际文件。
3. 对照对应功能专题确定文件与依赖，按 §2–3 装配。配方及本地化可按 `assets/main/recipe.lua`、`assets/main/language.lua` 与 `assets/main/string_zh.lua`、`assets/main/string_en.lua` 骨架填写。
4. 美术资源按 `anim_symbols.md` 第 6 节处理：可用工具时接受使用者提供的 png 打包图集、或解包改造官方动画；否则索取素材，不臆造资源文件。
5. 不建空目录、不建无内容的转发文件；目录按实际功能取子集。

## 6 多系统或大型模组的可选组织

按依赖复杂度而非文件数扩展。保持入口和装配清单为单一导入点，内容模块通过 require 复用纯模块；公共数据不散落在各处，整体重构按 `workflow.md` §3.1 分阶段。此节不要求小模组增加目录。

| 目录或职责 | 何时有价值 |
|---|---|
| `main/` | 按系统拆装配清单；配方、烹饪、皮肤、角色、RPC、用户命令等按依赖有序装配，共用 init 与本地化入口 |
| `postinit/<类型>/` | 单对象 patch，有清晰的原对象名；跨对象的系统级包装可在 postinit 平铺 |
| `scripts/datadefs/` | 复杂配置、地皮、物品、皮肤、配方及布局的数据与注册逻辑分离 |
| `scripts/behaviours/` + `scripts/brains/` | 复用 BehaviourNode 和组合行为；具体选型读 `brain.md` |
| `scripts/tools/` | 模组运行期共享模块，由实际需要者 require；开发期资源转换工具及发布文档不要进入运行链 |
| `languages/` | 大量台词与多类翻译的模块；Lua 字符串表与 .po 翻译映射分别管理，.pot 为生成模板；统一合并时点，兼容需求见 `compatibility.md` |
| `levels/` | 世界地皮的美术资源；布局数据在 `scripts/map/` |

世界生成与运行期地图的装配按 `worldgen.md`；前端建服资源按 modservercreationmain 的 FrontEndAssets/ReloadFrontEndAssets 机制核对。世界级系统可各自作为组件挂在实际 world prefab，见世界专题。阅读已有大型模组先追三个入口的实际加载链，再按功能下钻 postinit、scripts 及数据定义。
