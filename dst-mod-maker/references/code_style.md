# 代码风格与结构契约

新建或重构时对照用，不是引擎契约；修改现有模组时优先保留其结构和风格。**功能跑通不等于交付合格**：模组代码是给人读、给人改的，写法与落点本身就是交付质量。这里只放判断与组织，API 签名与行号一律现场查。

下列是推荐写法与组织约定；引擎机制以相应源码为依据，风格选择说明目的与适用条件。

## 1 入口与全局名

- `modmain.lua` **只放按序 `modimport("main/...")` 清单**，先 init；不得直接导入 postinit 或在入口写具体实现。对应 `main/*.lua` 可以只有一行转发。
- `GLOBAL.setmetatable(env, {...})` 放在 **`main/init.lua` 第一个有效语句**（第一个被 modimport 的文件）。`mods.lua` 的 `env.modimport` 用 `setfenv(result, env.env)` 让所有子文件共享同一个 env，入口补一次即可。
- **`main/init.lua` 是公共声明入口**：集中 `PrefabFiles`、需要全局加载的 `Assets`，以及本模组确实需要新增的物品栏/小地图图集注册。新 prefab 的局部 assets/deps 保留在 prefab 文件末尾的 `Prefab(...)` 中；已经由 prefab 声明或原版注册且可直接用的资源不再进公共 Assets。
- 补了元表后，所有文件**直接裸写**官方全局名（`Action()`、`ACTIONS`、`STRINGS`、`TheWorld`、`TheInput`、`ThePlayer`、`SpawnPrefab`……）。推荐不用 `local G = GLOBAL` 再 `G.X`：那等于把元表白设。`AddAction` 这类 mod env API 本来就在 env 里，不需要元表，见下一条。
- 三个入口按执行职责区分；env 是否共享取决于加载路径（`mod_structure.md` §2）。后两个入口写得少可直接用 `GLOBAL.X`，不依赖另一个入口已经补过元表。
- mod env API 直接裸写；取官方全局才需要 GLOBAL 或 env 元表。每个入口的可用 API 查 `mods.lua:CreateEnvironment` 和 `modutil.lua:InsertPostInitFunctions` 的实际分支。
- 元表本身仍是风格选择不是必需；不写就全程 `GLOBAL.X`，但**不要两种混着写**。

## 2 不要过度防御

写错了就让它报错——报错比静默回退好定位，也更早暴露。

- **配置**：`GetModConfigData` 直接读，不要 `type(v) == "number" and v or fallback`。配置项是自己写的，类型校验只会把写错吞成默认值。
- **官方文件**：直接 `require`，不要 `pcall(require, ...)`。加载的是官方模块，不存在「可能加载失败」。
- **引擎保证的东西**：在已经确认的执行端和生命周期，直接使用可达且必然存在的对象；不要机械探测 `TheWorld` / `TheNet` / `TheInput`。对象在前端、初始化、退出、专服或可选组件中确实可能不存在时，在真实边界判断。
- **避免无依据的幂等标记与双路径兜底**：已确认只执行一次的实例 PostInit 可直接保存原方法再包装，不用额外 `patched` 标记。相同字段赋值不等于重复包装无害；同一对象可能重复安装时，包装会层层嵌套，监听/任务/倍率也可能重复。先核对注册时机，只在实际有重复进入、取消或恢复路径时做幂等与清理。
- **客户端文件头不要堆防御**：确认客户端入口和生命周期后直接写逻辑，不堆 `TheNet == nil` / `IsDedicated()` / `rawget(GLOBAL, "TheInput") == nil`。一般不必按端分流装配层；若模块加载本身触及仅客户端/仅服务端资源，则按真实端别选择入口或守卫。
- 改控件、屏幕及 replica 等 Class 实例可用 AddClassPostConstruct；它在原构造之后执行，选择 hook 与纯表包装时看 `api_patterns.md` §1 和实际调用时机。
- 模块**直接 `return` 一张表**时，也可以 `require("...")` 拿表直接改字段／方法（改的是类本身、所有实例共享、时机更早）；类表没有 `_ctor` 时更不能套 `AddClassPostConstruct`（`DoAddClassPostConstruct` 假定 `_ctor` 存在）。按「要按实例注入」还是「要改类」选，见 `items_ui.md` 与 `api_patterns.md` §1。
- **边界**：`pcall` / 存在性探测用于真实可选依赖与可恢复失败，不用于掩盖自身错误；兼容层默认不加，实际执行边界仍应处理。

## 3 守卫只加在该加的地方

- 守卫按**实际执行端与时机**决定，不按 hook 名称机械添加。两端共享的 prefab PostInit 中仅服务端执行的逻辑用 `TheWorld.ismastersim`；共享声明留在分支外。已保证只在服务器实例上调用的组件与 SG 回调通常不需要重复判断。
- 常规游戏实体的 `AddPrefabPostInit`：服务端/客户端都可能构造网络 prefab；只改权威组件时在回调入口直接 `if not TheWorld.ismastersim then return end`，或将服务端段落集中在 `if TheWorld.ismastersim then ... end`；不以组件非 nil、`TheWorld ~= nil` 或通用 `IsServer()` 包装代替。只在确实可能早于世界创建的 prefab（如前端对象）或入口装配处按真实时序判断。
- 官方玩家主图 `wilson` 在服务端构造，预测图 `wilson_client` / `wilsonghost_client` 客端按需构造，SG hook 以图名匹配（`player_common.lua`、`stategraph.lua`）。确定图端别后无需重复守卫；自定义/共享图按实际构造路径判断。
- 前端、世界生成、客户端 UI 与运行期初始化不能混作同一环境；只在确有本地对象缺失或跨端共享的地方分流。
## 4 方法怎么写

- 覆盖组件／实体的**实例方法**（签名已知）用 `function self:Method(args)` 直接定义，不写 `self.Method = function(_self, args)`。后者只是语法糖的展开，可读性更差。
- `function(...)` 全量接参只用于**包装签名可能变化的官方全局函数／事件回调**（Klei 常在尾部加参数），并把返回值原样传回；不要拿它当所有覆盖的默认写法（`api_patterns.md` §1）。
- **选型**：成功行为后的附加效果先找官方事件；组件需要改字段/包装实例方法时用 `AddComponentPostInit`，不为了省一层 hook 就直接 `require("components/...")` 修改整个类。仅在对应官方扩展点不足、确实需要类级行为或更早时序时才改类。
- **包装官方方法、只在特定条件拦截**时，用「保存 old → 覆盖 → 条件不满足就回退 old」的套路：在 `AddComponentPostInit` 或类表改写里 `local old = self.Method` 或 `local old = Class.Method`，新实现里 `if 我的条件 then 做自己的事（或拦掉） else return old(self, ...) end`。这样只改目标场景，不影响官方其它实体；签名按源码确认。无论已知还是可变签名，只要保留原语义，就必须保留原返回值契约：例如原函数返回 `success, loot`，不能只接收并返回 `loot = old(...)`。不需要后置处理时直接 `return old(self, ...)`；需要后置处理时按已知返回值分别接收并返回。别整个替换掉官方实现再自己重造一遍。

## 5 按生效范围选 hook

- 单个角色 → `AddPrefabPostInit("<prefab>")`。`AddPlayerPostInit` 是 `AddPrefabPostInitAny` + `HasTag("player")`，对**全体玩家**生效；改单角色不要用它，更不要用它挂 `playeractivated` 再在回调里筛 `prefab`。
- 客户端输入／鼠标坐标上报走 `main/rpc.lua` 里的客户端范式：`AddClientModRPCHandler` 开关 → `ThePlayer` 上 `DoPeriodicTask` → `TheInput:GetWorldPosition()` → `SendModRPCToServer`。全程用 `ThePlayer`，不遍历全体玩家。详见 `api_patterns.md` §4。

## 6 改动集中放，默认落 `postinit/`

- `main/*.lua` 是**装配层**：公共 `Assets`/`PrefabFiles` 仅放 `main/init.lua`，其余按职责放配置、语言、配方、`AddAction` 定义与 `modimport("postinit/...")` 转发。`main/prefabs.lua` 不是 `PrefabFiles` 声明处，只在有 prefab hook 时转发。
- 对官方对象的 hook 与包装——`AddPrefabPostInit` / `AddComponentPostInit` / `AddStategraphPostInit` / `AddStategraphActionHandler` / `AddClassPostConstruct` / `AddComponentAction`／包装官方 `ACTIONS.*.strfn`——**默认**放 `postinit/<类型>/<对象名>.lua`，一文件一对象；跨系统改动按系统平铺命名。
- 典型落法：`main/prefabs.lua` 或 `main/components.lua` 可只转发对应 postinit 文件；`main/actions.lua` 放 `AddAction` 定义并转发 `postinit/actions`、`postinit/componentactions`；`main/stategraphs.lua` 转发两端 SG，`main/widgets.lua` 转发控件 hook。只建实际需要的文件，不把这些 postinit 路径直接塞进 modmain。
- **这是新建/整体重构的组织方式**：引擎全局类和共享模块表的包装也集中在 `postinit/`，例如 `postinit/map/retrofit_savedata.lua`；对应 main 文件负责转发。自定义 prefab 的构造放 `scripts/prefabs/`，由 init 的 PrefabFiles 注册。已有手工 RegisterSinglePrefab 及重注册补救层应检查能否迁移到标准加载链（保留 prefab 名、资源、依赖与旧档契约）。

## 7 注释与本地化

- `modinfo.lua` 有中英双语时，游戏内新增文本也要对应覆盖。modinfo 用注入的 locale，运行期用 LOC.GetLocaleCode（语言码查 `languages/loc.lua`）。main/language.lua 选择独立 string_zh 或 string_en 文件，保持文本键一致且不覆盖原版整表。先加载本地化，再将其值交给 AddAction 或 Action.str；动作文字为空及 strfn 的机制查 `modutil.lua:AddAction`、`stringutil.lua:GetActionString`。

- 交付代码里只留「为什么这么写」的一行结论；不要把源码加载链、行号推演、失败假设写成长篇注释，更不要为一段**臆想的**副作用搭整套兜底。
- 时机判断写一句结论即可。技能树定义与翻译要核对实际创建顺序、UI 读取时机和语言覆盖（`skilltree.md`）。别把加载链推演写进交付代码。
- 交付依据、假设与测试深度按用户需要调整（`SKILL.md`）。

## 8 动作注册

新建或重构采用 `actions.md` 的表结构、确定注册顺序与两端闭环；定义、收集与状态处理各归相应模块。
