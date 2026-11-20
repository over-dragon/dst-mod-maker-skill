# 角色、初始属性与出生物品

## 新角色与修改已有角色

- 新角色由 `main/characters.lua` 装配 `modutil.lua:AddModCharacter`，角色 prefab 放 scripts/prefabs，并通过 PrefabFiles 注册。查 `prefabs/player_common.lua:MakePlayerCharacter` 及最接近的原版角色，区分 common_postinit 的共享声明与 master_postinit 的权威组件初始化。
- 修改已有角色优先 AddPrefabPostInit；需要改变全角色共同逻辑才选择全体玩家 hook。数值查 `tuning.lua` 的实际读取点及 health/hunger/sanity 等组件 setter，注意改变上限时当前值、百分比、replica 和 HUD 的契约。
- 角色选择与查看界面查 `characterutil.lua`、`widgets/redux/characterselect.lua`、characterbio.lua、loadoutselect.lua。运行期角色名、语音和装备符号有各自消费者，查官方角色 prefab、STRINGS 与 `anim_symbols.md`。

## 角色本体、默认皮肤与前端资源

自建可选角色常见的两份 prefab 为 `<角色>.lua`（MakePlayerCharacter）和 `<角色>_none.lua`（默认皮肤）。在 main/init.lua 登记实际 PrefabFiles 和公共界面资源。皮肤使用 `prefabskin.lua:CreatePrefabSkin`，按需配置 base_prefab、type 为 base、skins（normal_skin、ghost_skin 等）、skin_tags、build_name_override 和 assets；`modutil.lua:AddModCharacter` 的 modes 供选择界面预览使用，查 `skinsutils.lua:GetSkinModes` 及 `widgets/redux/loadoutselect.lua` 对 MODCHARACTERMODES 的读取，避免重复添加默认预览模式。

| 用途 | 资源或源码定位 |
|---|---|
| 初始本地化文字及台词 | STRINGS.CHARACTER_NAMES、CHARACTER_TITLES、CHARACTER_DESCRIPTIONS、CHARACTER_QUOTES、CHARACTER_SURVIVABILITY 等按角色标识填写；STRINGS.NAMES、CHARACTERS、SKIN_NAMES 按实际消费者使用对应大小写。自定义 speech 表参考官方 speech_<角色>.lua 与 stringutil.lua |
| 角色大画像与选择/存档头像 | bigportraits/、images/saveslot_portraits/、images/selectscreen_portraits/；查 characterutil.lua 的 SetSkinnedOvalPortraitTexture / SetOvalPortraitTexture 和实际界面；旧选择图等按当前消费者确认是否需声明 |
| 玩家头像与自检按钮 | images/avatars/（avatar_、avatar_ghost_、self_inspect_）；查 widgets/playerbadge.lua、targetindicator.lua、inventorybar.lua |
| 地图图标 | images/map_icons/；AddMinimapAtlas 配合共享初始化中的 MiniMapEntity:SetIcon |
| 角色名称贴图 | images/names_<角色>.xml、images/names_gold_<角色>.xml；查 characterutil.lua 的 SetHeroNameTexture_Grey/Gold 与语言后缀选择 |

【资源结构】名称图集的 Texture filename 与 XML Element name 可不同。名称贴图的消费者按角色 ID 加 .tex 读取 Element，不能只按输出文件名自动生成名字；根据实际 UI 查当前需要的图名并核对 atlas。真实角色资源随用户素材提供，exported/ 下的 SCML/源图是制作素材，游戏加载的是编译后的资源及声明。

复用原版角色外观时分别核对玩家实例初始 build（`player_common.lua:MakePlayerCharacter`）、皮肤系统的人形/鬼魂 build 选择、角色选择及 HUD 等界面的 atlas/image。仅配置默认皮肤不保证构造阶段按角色名查找的 build 存在；仅复制 XML 区域也不保证纹理可加载。图集路径核查见 `anim_symbols.md` §5。

## 人形、鬼魂与角色专属状态

- 人形/鬼魂转换参考官方 `prefabs/woodie.lua`、wolfgang.lua 的 ms_becameghost、ms_respawnedfromghost 监听，以及 player_common.lua 的 OnLoad、OnNewSpawn 包装链。角色自己的 master_postinit 可设置相应回调，恢复时按实际 playerghost 状态重新协调生效效果；对已有角色追加行为需保留原回调。
- 角色专属速度等持续效果按来源和状态设置、撤销对应 modifier（如 locomotor 的 ExternalSpeedMultiplier），避免复活后叠加或鬼魂保留不应有的效果；不重复覆盖其它系统的倍率。声音按原版角色 soundsname、talker 配置与资源实际选择。

## 出生物品：全局默认与单实体决定

- 给一种已有角色或所有角色调整默认出生物品，先查 `tuning.lua:GAMEMODE_STARTING_ITEMS` 及官方角色 prefab（如 `prefabs/wilson.lua`）的 start_inv 读取时机、游戏模式、回退和 prefab 依赖。属于全局的配置可在数据被消费前调整对应角色/模式列表；不要无意改变其它模式或共用表。
- 例如在明确要给 DEFAULT 模式中已登记的所有角色追加同一种有效物品时，可遍历 `TUNING.GAMEMODE_STARTING_ITEMS.DEFAULT` 的角色列表并 table.insert；单个角色则只改其对应项。按实际加载顺序保证新增角色、物品依赖及前端显示正确。
- 自建角色在 master_postinit 为 inst.starting_inventory 指定该实例的列表；当前 `MakePlayerCharacter` 已标记末尾 starting_inventory 参数弃用。按 `player_common.lua:OnNewSpawn`、`prefabs/player_common_extensions.lua:GivePlayerStartingItems` 和 `networking.lua:SpawnNewPlayerOnServerFromSim` 核对真正发放时机。不要把 prefab 构造或每次 playeractivated 当作新生发放。
- 需按配置或玩家状态随机选择时，在权威出生路径决定该玩家的结果，按需复制列表，避免污染其它实例或依赖两端独立随机。核对角色选择界面所显示的默认物品与实际发放，相关入口 `characterutil.lua:GetUniquePotentialCharacterStartingInventoryItems`、TUNING.STARTING_ITEM_IMAGE_OVERRIDE、widgets/redux/templates.lua 与 screens/redux/defaultskinselection.lua；图标映射、预览列表和实际发放是不同职责。
- 涉及重连、复活、角色切换或洞穴迁移时明确哪些属于新生；保留原版出生与存档流程。

技能树另见 `skilltree.md`，通用组件与持久状态见 `component_system.md`。
