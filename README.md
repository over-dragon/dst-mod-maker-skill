# DST Mod Maker Skill

面向 AI Agent 的《饥荒联机版》（Don't Starve Together，简称 DST）Lua 模组开发技能。

帮助 AI 从玩法描述出发，查阅当前游戏源码、选择合适的官方机制、编写和优化模组，并完成静态自检。既可以用于从零制作模组，也可以用于维护已有模组。

**这不是安装到游戏里的模组，而是提供给 AI 编码助手使用的 Skill。**

## 设计理念

- **源码优先**：以当前安装版本的游戏源码为行为依据，API 注解用于快速定位接口、类型及枚举，避免依赖过时的结论或凭空编造 API。
- **按需检索**：根据任务及功能读取相关专题，不要求 AI 一次性加载全部资料，也不追求收录所有游戏知识。
- **工程化开发**：提供模组目录组织、入口分工、Prefab 注册、Hook、配置及本地化等开发规范，兼顾小型模组与复杂模组的维护需求。
- **联机正确性**：重视服务端权威、客户端表现、数据同步、状态图以及实体生命周期等 DST 特有机制。
- **复用官方实现**：优先使用已有组件、动作、事件、动画和图标，避免不必要的重复实现与资源声明。

## 支持的开发场景

| 方向 | 内容 |
| --- | --- |
| 模组开发与重构 | 新建模组、局部修改、结构优化、代码审查、问题排查 |
| 实体与玩法 | Prefab、组件、物品、装备、容器、配方、生物 AI、战斗 |
| 角色 | 新角色、出生物品、技能树、角色专属机制 |
| 交互与联机 | 动作、状态图、轮盘施法、UI、netvar、RPC、跨分片通信 |
| 世界与资源 | 世界生成、旧档地图改造、动画、Symbol、贴图、皮肤与特效 |
| 维护 | 存档与生命周期、兼容性、资源检查、游戏版本更新 |

## 安装与使用

### 1. 安装 Skill

克隆或下载本仓库，将完整的 `dst-mod-maker/` 目录放入所使用 Agent 支持的 Skills 目录中，或通过其 Skill 管理功能导入。

应保留 `SKILL.md`、`references/`、`scripts/` 和 `assets/` 的相对目录结构，不要只复制 `SKILL.md`。

如果 Agent 不支持自动发现 Skill，也可以在对话中明确指定 `dst-mod-maker/SKILL.md` 的路径，要求它按该文件及相关专题开展工作。

### 2. 准备开发环境

- 已安装《饥荒联机版》，并允许 Agent 读取游戏目录和目标模组目录。
- Python 3：用于源码检索、环境定位、静态检查及动画解包工具。这些工具只依赖 Python 标准库。
- 可选：Lua 5.1 或 luac 5.1，用于真正的 Lua 语法解析；未安装时检查器会降级为词法扫描。

Skill 默认优先查询当前游戏安装中的 `data/databundles/scripts.zip`，无需事先手动解包官方脚本。无法自动定位时，可通过工具参数指定游戏目录或源码路径。

### 3. 向 AI 提出需求

推荐直接描述想实现的玩法或要解决的问题。首次使用或 Agent 未自动加载时，可以明确提到 Skill 名称。

**新建模组**

> 使用 dst-mod-maker Skill 为饥荒联机版制作一个模组：增加一种可制作的背包，拥有 16 个物品栏格子，使用官方背包动画和图标，支持联机及中英文本地化。

**优化已有模组**

> 使用 dst-mod-maker Skill 优化这个模组，整理目录与加载结构、改善代码维护性，保留原有玩法、配置和存档兼容性。

**排查游戏错误**

> 使用 dst-mod-maker Skill，根据下面的游戏日志和模组代码分析错误原因，查阅当前官方源码并修复问题。

不需要在提示词中重复 Skill 已包含的开发规范。

## 仓库结构

```text
dst-mod-maker/
├── SKILL.md           # 技能入口、任务路线与开发流程
├── assets/            # 模组基础骨架
├── references/        # 按功能组织的专题导航和工程实践
│   └── lsp-dst/       # 第三方 LuaCATS API 注解
└── scripts/           # 源码检索、资源分析与静态检查工具
```

## 辅助工具

工具会按需由 Agent 使用，也可以手动运行。进入 `dst-mod-maker/` 目录后执行：

```bash
# 定位游戏和当前官方源码
python scripts/locate_scripts.py --json

# 在官方源码中查找接口及调用点
python scripts/grep_source.py "AddPrefabPostInit" --file "modutil.lua" -C 3

# 静态检查新建或整体重构的模组
python scripts/check_mod.py "<模组目录>" --new-mod --json

# 解析官方动画包的 bank、build 和 symbol 信息
python scripts/unpack_anim.py "<game_root>/data/anim/backpack.zip" --summary
```

静态检查可以发现部分 Lua 语法、资源路径、图集纹理引用和工程结构问题，但它不能代替游戏运行验证。

## 使用说明与局限

- 本项目提供开发导航与工程实践，不是官方 API 文档，也不绑定特定模型或 Agent。生成质量与模型能力、工具权限及是否遵循 Skill 有关。
- 游戏版本更新后，应重新核对涉及的官方实现；内置 API 注解可能与当前版本存在差异。
- 最终功能、界面表现、联机行为及存档兼容性需要在游戏中实际验收。出现错误时，建议提供第一条相关 Lua 错误及完整堆栈。

欢迎通过 Issue 提供使用反馈、失败案例、源码依据或改进建议。尤其欢迎能复现的 AI 生成问题，它们有助于持续改善技能的导航与自检流程。

## 致谢

感谢 Klei Entertainment 开发《饥荒联机版》，以及 [LSP-dst](dst-mod-maker/references/lsp-dst/README.md) 项目作者及贡献者提供的 LuaCATS API 注解。

内置 LSP-dst 保留其 [原始许可证（MIT No Attribution）](dst-mod-maker/references/lsp-dst/LICENSE)。本项目为非官方社区工具。
