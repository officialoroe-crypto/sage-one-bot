# SAGE ONE — 13-Stage Evolution Design Lab

Status: **independent design specification / not production integration**

## Purpose

This lab translates the locked Evolution architecture into an implementation-ready visual specification. It does **not** modify Flutter screens, backend APIs, progression logic, or production assets.

## Canonical rules

- One permanent SAGE identity: black + deep blue + electric blue + white + subtle blue glow.
- Evolution material is an accent/material layer, never a full UI recolor.
- The Nepal/SAGE environment remains recognizable: Mount Everest, dark sky, stars, moon, blue/white moonlight, and golden Buddha.
- The UI structure remains stable across Evolutions.
- There are 13 major Evolutions and three intensity states per Evolution: Low / Mid / High.
- 13 × 3 = 39 visual states.
- Transition is High of the current Evolution → Evolution Transition → Low of the next.
- Skill Upgrade and Money Upgrade are separate progression paths.
- Evolution is lifetime achievement; Spark is separate platform economy.
- Do not invent final palette hex values where the locked reference calls them conceptual.

## Canonical order

1. Bronze
2. Silver
3. Gold
4. Platinum
5. Jade
6. Ruby
7. Sapphire
8. Emerald
9. Diamond Sovereign
10. Black Opal Realm
11. Painite Core
12. Void Matter
13. Californium Overlord

## Design-system boundary

This lab defines visual behavior and review criteria. Production implementation must consume the specification through shared configuration/engine primitives rather than duplicating thirteen screens.
