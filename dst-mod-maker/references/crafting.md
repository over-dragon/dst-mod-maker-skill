# 配方、制作、烹饪与科技

| 功能 | 文件 | 官方检索 | 注意事项 |
|---|---|---|---|
| 配方／制作栏／科技 | `main/recipe.lua` | `modutil.lua` 的 `AddRecipe2` / `AddRecipeToFilter`，`recipes_filter.lua` 的 `CRAFTING_FILTERS`，`recipes.lua` 原版配方 | 配方产物和每个 `Ingredient` 必须核对真实 prefab ID；普通新增配方明确传第五参数 `filters`，按用途从当前分类选。原版默认 MODS 不等于用途分类。配方贴图需已注册；新增科技查 AllRecipes.level、TUNING.PROTOTYPER_TREES 的消费者 |

## 烹饪与食物

- 官方检索：`cooking.lua`（`AddCookerRecipe`、`AddIngredientValues`、`recipes`）、配方表 `preparedfoods.lua` / `spicedfoods.lua`、`cookbookdata.lua`、成品 prefab 的 `edible` / `cookable` 组件；锅具组件 `components/cooker.lua`（`cookpot.lua` 是 prefab 不是组件）。
- 先定食材标签（`AddIngredientValues` 给 `fruit/meat/veggie/…` 权重）再定配方（recipe 的属性是标签阈值，`priority` 决定竞争胜出）；配方名与成品 prefab 名分开，别混。**扩展现有食谱**优先保留原 test 及字段语义，按需求包装匹配条件；查 recipe.name 的资源和 UI 消费者，避免仅靠改名绕重名。签名/权重细节现场查源码，不臆造配方数值

制作查询范围和组件扣料顺序见 `items_ui.md`。
