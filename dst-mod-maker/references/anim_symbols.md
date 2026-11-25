# 动画、符号与贴图体系

资源名称、实际图层和帧编号按当前安装包解包核实；Lua 侧调用查相近官方 prefab。以下区分可解析的资源结构与需游戏验证的引擎侧经验。

## 1 build / bank / symbol / number

- build 是贴图及符号定义，bank 是动画集合；zip 可以只含一侧，包名不一定等于实际 bank/build。详见 §7，使用解包器确定真实名称。
- `OverrideSymbol` 是覆盖原动画的目标 symbol，第二、三参数选择来源 build 和 symbol。查 Skill 根目录下的 `references/lsp-dst/scripts/sys_components/AnimState.lua`（引擎侧注解）和官方 prefab 的装备动画调用；有皮肤时查 OverrideItemSkinSymbol，状态退出应恢复临时覆盖。
- 网络 AnimState 修改与纯本地特效是不同机制。网络实体通过 AddNetwork/SetPristine 构造，具体 AnimState 方法何时同步查官方调用并由用户进游戏确认；非网络视觉子实体由本地生成，见 §4。不要把 Entity:AddNetwork 当作 Lua gameplay component 挂载。
- 官方检索：`prefabutil.lua`、`entityscript.lua`、相近的 `prefabs/` 与 `stategraphs/`。按具体资源核对 SetBank/SetBuild、OverrideSymbol 及清理路径。

## 2 layer：三种用途

| 类型 | 对应机制 |
|---|---|
| 动画 layer 名 | AnimState:Hide/Show，解包确认 layer 名 |
| symbol 显隐 | HideSymbol/ShowSymbol，解包确认 symbol 名 |
| 实体整体渲染顺序 | SetLayer/SetFinalOffset，查 `constants.lua` 的 LAYER_* / FINALOFFSET_* 与实际 prefab |

【引擎侧经验】名称图层与 symbol 可以不同；数字偏移影响相对绘制顺序，具体显示在游戏内确认。

## 3 FollowSymbol 参数（引擎侧经验）

查注解及当前官方 `FollowSymbol` 调用，完整引擎语义要按目标效果实测。常见形态：`Follower:FollowSymbol(owner.GUID, symbol, x, y, z, followlayer, followvisible, symbol_begin, symbol_end)`。

- 第 6 位为 true 跟随 symbol 图层；面数相同的特效也可跟随对应面动画。
- 第 7 位跟随显隐。
- 第 8 位为 symbol 的 number；只填该位时匹配指定编号。
- 第 8、9 位同时设置，经验为左闭右开区间 [begin, end)。

bank element 的引用 number 与 build frame 的起始 number 可不同（§7）。一张贴图可覆盖多个编号，涉及 FollowSymbol 究竟过滤哪个编号时须实测。

## 4 跟随玩家特效的可复制范式

- 如果只需本地视觉，网络父实体承载同步状态，子实体用 CreateEntity 加 Transform/AnimState/Follower，不加 Network、标记 FX、persists=false。
- 通过 SetParent、FollowSymbol 挂载并选择合适的渲染顺序；专服不创建纯本地 fx，客户端 OnEntityReplicated 补建。
- 四面或多面效果按需要参照 GetCurrentFacing、动画时间与 updatelooper 的官方用法；颜色同步查 colouraddersync。
- OnRemoveEntity、换装或状态结束清理子实体和更新监听；同步与显示根据实际生命周期接线。按符号在官方 prefab 中找相近范例。

## 5 物品栏贴图注册

- 单图可声明 IMAGE 与 ATLAS；公共图集声明 ATLAS。画版、动态符号等用途可能要求 ATLAS_BUILD，查官方 `decor_pictureframe.lua`、`minisign.lua`、`skin_assets.lua` 的 Asset 声明选择适用参数，具体行为由引擎决定。
- 新图注册于 `main/init.lua`；已有原版或 prefab 局部已加载资源不重复放公共 Assets。库存、配方、小地图、技能树、百科等资源由不同消费者读取；查 `modutil.lua` 的 RegisterInventoryItemAtlas、AddMinimapAtlas、RegisterSkilltreeIconsAtlas、RegisterScrapbookIconAtlas。
- 区分直接复用已注册的原版 atlas/image 与自建模组图集。自建图集必须随模组提供 XML 和对应的实际 TEX；`Texture filename` 相对于 XML 所在目录指向该 TEX，`Element name` 只是图集中的区域名（多个 Element 可以共用一张 TEX）。仅修改 Element 或引用原版同名 TEX 不算有效资源。先查消费者能否直接选用原版图集和图名；确需自建图集再核对实际纹理、路径和 UV。静态核查用 `check_mod.py`，实际加载看客户端日志。

### 公共图集注册示例

```lua
local inventory_images = {
    "my_item",
    "my_item_charged",
}

local atlas = resolvefilepath("images/inventoryimages/my_mod_images.xml")
for _, v in ipairs(inventory_images) do
    local image = v..".tex"
    RegisterInventoryItemAtlas(atlas, image)
    RegisterInventoryItemAtlas(atlas, hash(image))
end
```

公共 Assets 中声明实际图集。图名对应 XML Element，多个物品或形态可从数据表生成清单，双方在首次使用前注册。

- 【源码】`simutil.lua:RegisterInventoryItemAtlas/GetInventoryItemAtlas` 的缓存按键查找；`prefabs/inventoryitem_classified.lua` 的 image 为 net_hash，`inventoryitem_replica.lua:GetImage/GetAtlas` 也可能使用字符串名，所以共享图集注册两种键。先查找后注册、与原版或其它 mod 重名，都需留意首次缓存和冲突行为；有返回 atlas 也需确认图集包含实际 image。
- 复用原版图标时用已注册名称，必要时 `inventoryitem:ChangeImageName("backpack")` 等方式指定；新 prefab 默认按 prefab 名查图，与所用动画无关。图标名与 prefab 名一致时可直接供物品/配方查找。查 `components/inventoryitem.lua`、`inventoryitem_replica.lua`、`recipe.lua:GetAtlas` 与 `widgets/recipetile.lua`。

## 6 边界与可用工具

以实际存在的素材和官方资源为准，不凭空起资源、bank/build/symbol/number 名。未指定素材时优先复用；需要新增或转换素材时按用户需求与可用工具处理，确有缺失时索取素材。

## 7 解包官方动画（skill 自带能力）

```bash
python scripts/unpack_anim.py "<game_root>/data/anim/<名字>.zip" --summary
python scripts/unpack_anim.py "<game_root>/data/anim/<名字>.zip" -o out.json
```

`data/anim/` 是常见官方动画路径，实际数据包由游戏安装决定；可用 locate_scripts.py 定位。一个 zip 内可以只有 anim.bin 或 build.bin；只解一个包不能推断另一侧的名称。解包器读取资源结构，不写回或产出动画。

**解包结果的匹配规则**（不是 Lua API）：

- build.bin：build.name → symbol → frame（贴图记录）。frame 的 number 是起始编号，duration 即 length，为覆盖的连续编号数量，不是时间；x/y/w/h 与 atlas_pages 供定位，实际纹理坐标还需顶点数据。
- anim.bin：bank → animation → frame（动画时间轴，由 fps 推进）→ element。element 的 symbol 与 number 是贴图引用，layer 是图层，矩阵与 zIndex 描述变换和相对层级。
- 先匹配 symbol，再找满足 `build_frame.number <= element.number < build_frame.number + build_frame.duration` 的贴图 frame。例如 number=0、length=2 的 frame 同时覆盖引用 0 和 1。不能把 animation frame 序号当作 symbol 的 number。
- 同包 build 找不到符号时检查其它 build 或运行时动态绑定的 symbol（如部分 *_follow 符号），不要直接判资源损坏。hash 表缺漏时解包器可能输出 null，需结合其它实际资源核对。
- 格式支持及字段以 `scripts/unpack_anim.py` 为准；游戏更新后解析失败按版本和数据结构重查，解包成功也不证明客户端显示正常。

## 8 音频、相机、皮肤与 shader

- 音频查 `modutil.lua:RemapSoundEvent/RemoveRemapSoundEvent`、SoundEmitter 的实际 prefab 用法；相机查 `camerashake.lua`、`cameras/followcamera.lua`。镜头和本地播放按实际端别驱动，需要时用 dirty 事件同步。检查播放、停止、重复和清理路径；引擎实际表现由用户进游戏确认。
- 皮肤查原版 skin assets 和角色/物品 skin prefab。

### 着色器与粒子特效

- 动画材质查 `AnimState:SetEffect`、`SetShaderFloat` 的原版调用。粒子查 `VFXEffect:SetRenderResources(发射器索引, 贴图, shader)`：Lua 控制发射位置、速度和寿命，shader 绘制每颗粒子。先查相近 prefab 搭配的贴图、shader 和混合模式，例如 `prefabs/torchfire_shadow.lua` 的烟雾。
- 自定义粒子 shader 可用 GLSL 顶点文件 `.vs` 和片元文件 `.ps`。以下是 Klei Mod Tools 编译命令示例。将产物放入模组的 `shaders/`，在 prefab 的 assets 中声明 `Asset("SHADER", "shaders/my_fx.ksh")`，绑定时传 `resolvefilepath("shaders/my_fx.ksh")`。

  ```text
  ShaderCompiler.exe -little my_fx my_fx.vs my_fx.ps my_fx.ksh -oglsl
  ```

- 联网粒子参考 `prefabs/thurible_smoke.lua` 的 `InitParticles`：用 `not TheNet:IsDedicated()` 在有画面的实例创建 VFX，再用 `not TheWorld.ismastersim` 让客机提前返回。这样非专用主机也能看到粒子。
