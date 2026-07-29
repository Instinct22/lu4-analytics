# Game mechanics: Damage from shot range

- Source: https://masterwork.wiki/lu4/posts/post/144-game-mechanics-damage-from-shot-range
- Path: /lu4/posts/post/144-game-mechanics-damage-from-shot-range
- Type: None
- Key: page:lu4_posts_post_144_game_mechanics_damage_from_shot_range

## Content
Lu4
Lu4
Eternal
MasterWork
Classes
Skills
Items
NPC
Quests
Articles
Search
Ctrl+K
English
English
Русский
Українська
Start to Play
Classes
Skills
Items
NPC
Quests
Articles
English
English
Русский
Українська
Search
Lu4
Lu4
Eternal
MasterWork
Start to Play
Main
Articles
Basic mechanics
Game mechanics: Damage from shot range
Game mechanics: Damage from shot range
Basic mechanics
26.09.2025
Basics
This article is devoted to the shooting range damage dependency.
The way it was conceived and implemented by the Korean developers NCSoft.
You may encounter this mechanic on official and PTS servers, and it works the same way on the servers of the E-Global MasterWork project.
Formula for calculating damage from a bow/crossbow depending on the distance to the target:
DistRatio = Dist / AttackRange * 100
DistRatio — Variable that determines the damage to the target depending on the distance to it
Dist — Distance to target at the time of a specific shot
AttackRange — The shooter's maximum available firing range
Screenshot for estimating the distance from the character to the target "by eye"
Shooting range
For all bows the default attack_range = 500. However, this number can be increased due to bonuses from skills and items:
Long Shot
—
depending on skill level +200 / +400 to distance
Counter Snipe Shot
—
depending on skill level +35 / +50 / +75 to distance
Archery
—
depending on skill level +25 / +50 / +100 to distance
Snipe
—
depending on skill level +50 / +100 / +150 / +200 to distance
Archer's Will
—
depending on skill level +50 / +85 to distance
Symbol of the Sniper
—
depending on skill level +100 to distance
Hardened Weapons
—
+100 to distance
Rare bow/crossbow - Clairvoyance
—
bonus of rare weapon +100 to distance
Draconic Leather Armor
Bow master
s
—
bonus from armor set +50 to distance
Dynasty Leather Armor
Bow master
s
—
bonus from armor set +50 to distance
Moirai Leather Armor
Attack
s80
—
bonus from armor set +50 to distance
If you collect all possible enhancements, the maximum firing range can be 1710. However, this is an
absolute value that is almost impossible to achieve "in the field".
Damage calculation
Let's consider a more realistic situation - a
Hawkeye
with a
Draconic Bow
.
Passive Effects:
Draconic Bow
S
—
range +500
Long Shot
Lv. 2
—
range +400
Archery
Lv. 3
—
range +100
Archer's Will
Lv. 2
—
range +85
Active Effects:
Snipe
Lv. 2
—
range +200
Counter Snipe Shot
Lv. 3
—
range +75
Total AttackRange = 1 360.
Short distance
Let's take a distance to the target equal to 250. Calculate the shooting efficiency coefficient using the formula
DistRatio = Dist / AttackRange * 100:
Dist = 250
AttackRange = 1 360
DistRatio = 250 / 1 360 * 100 = 18,38
Find the DistRatio value on the X axis in the graph and see a reduction in damage by about 9%.
Long distance
Let's take a distance to the target equal to 950. Calculate the shooting efficiency coefficient using the formula
DistRatio = Dist / AttackRange * 100:
Dist = 950
AttackRange = 1 360
DistRatio = 950 / 1 360 * 100 = 69,85
Find the DistRatio value on the X axis in the graph and see an increase in damage by approximately 14%.
Interesting facts
In server settings Bow = Crossbow. Accordingly, the calculations are the same for a bow and a crossbow.
The damage is calculated at the moment the arrow or bolt reaches the target, which means that if the
distance to the target changes during the flight of the projectile (for example, the target is approaching),
then the final damage will also change.
Maximum damage can be achieved at 80% of shooting range. From 80% to 100%, the damage bonus decreases to 0.
Skill
Rapid Fire
reduces the firing range by 30-50%. The basic firing range is reduced - attack_range (bow) from 500 to 250,
and then all other effects from skills are applied to this value.
Can be interesting
New S-Grade Sets Bonuses
Masterwork Item Bonuses
Game mechanics: Damage from front, side, back
Game Mechanics: Physical Skills Damage
Game mechanics: Hidden weapon parameters
Categories
Basic mechanics
Gaining Experience and Penalties
Game mechanics: Damage from shot range
Game mechanics: Damage from front, side, back
Game Mechanics: Physical Skills Damage
Game mechanics: Hidden weapon parameters
Attribute System
Enchanting Skills
EXP and penalties in a party
MasterWork 2026
All rights reserved