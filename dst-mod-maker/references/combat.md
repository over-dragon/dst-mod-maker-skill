# 战斗、受伤与增益

- 从实际目标 prefab 及 `components/combat.lua`、health.lua、weapon.lua、debuffable.lua、debuff.lua、aura.lua 查机制。攻击准备、结算、受击/拒绝事件、死亡是不同阶段；按 DoAttack/GetAttacked/DoDelta/Kill 等实际路径选 hook。
- 免伤、拒绝伤害与强制死亡有不同副作用；核对 SetInvincible、health.redirect、Kill/ForceKill 和 GetAttacked 的执行顺序及事件（attacked/blocked），不要按方法名假定 ForceKill 会绕过所有限制。
- 击退、击飞先查 `stategraphs/SGwilson.lua` 的 knockback 事件、`stategraphs/commonstates.lua:CommonHandlers.OnKnockback` 及原版发送事件的调用点，按目标状态图选择机制。
- 有增益或光环时查 OnTick、Enable、OnAttach/OnDetach 与实际 prefab。active、applying 或实际特效可能有不同生命周期；手动切换效果时同时检查原组件的启停与清理路径。
- 战斗状态依角色、形态和实际状态图变化。若改 Wendy/Abigail，参考 `prefabs/wendy.lua`、`prefabs/abigail.lua`、`stategraphs/SGabigail.lua` 和 `components/ghostlybond.lua`，重点查召回与死亡复用、对齐/形态、光环与攻击事件，不能将某个形态、tag 或 buff 当作所有角色的共同判据。轮盘见 `spellwheel.md`。

## 武器、投射物与范围效果

- 游戏内武器的普通攻击查 `components/weapon.lua` 的 SetDamage/SetRange/OnAttack/LaunchProjectile、`components/combat.lua:DoAttack`，以及同类原版 prefab；分清发射、命中、资源消耗和攻击动画的职责。
- 目标实体的直线/追踪投射物查 projectile.lua 的 Throw、Hit 与原版 `prefabs/blowdart.lua`；按世界点抛物或落地效果查 complexprojectile.lua 的 Launch/Hit 以及 `prefabs/bomb_lunarplant.lua`。按实际行动选择组件，核对碰撞、攻击者归属、命中/未命中、取消和实体移除路径。
- 范围效果查 combat.lua 的 DoAreaAttack 及原版同类效果调用；按需求明确目标筛选、距离与每个目标的结算次数，确保服务端只结算一次并协调投射物的动画、特效和生命周期。纯表现 FX 见 `anim_symbols.md`。

## 生存状态

饥饿、理智、温度、潮湿、食物、燃烧、冰冻、落水先查 components 下 hunger、sanity、temperature、moisture、edible、burnable、freezable、drownable 对应文件及 replica/实际 prefab；区分当前值、上限、持续变化率和多个状态来源，优先使用组件提供的接口，核对进入、退出、死亡及读档恢复。
