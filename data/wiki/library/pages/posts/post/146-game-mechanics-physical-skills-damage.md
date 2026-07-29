# Game Mechanics: Physical Skills Damage

- Source: https://masterwork.wiki/lu4/posts/post/146-game-mechanics-physical-skills-damage
- Path: /lu4/posts/post/146-game-mechanics-physical-skills-damage
- Type: None
- Key: page:lu4_posts_post_146_game_mechanics_physical_skills_damage

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
Game Mechanics: Physical Skills Damage
Game Mechanics: Physical Skills Damage
Basic mechanics
28.03.2025
Базовая информация
This article is about the original game calculations of the damage done by physical skills, as it is being conceived
and implemented by the Korean game developer NCSoft. You have encountered these mechanics on official and PTS
servers, which also work on E-Global MasterWork.
Physical skills damage
Physical Skill Damage Calculation Formula:
Damage = 77 * (P.AtkSkill + P.AtkChar) * MultiplicativeBonus / P.DefChar
The number 77 is a constant for physical melee attacks laid by Korean
developers. On Interlude chronicles this value was "70", from where it inherited many builds of free servers.
On the chronicles after, up to High Five, the constant value for MELEE_DAMAGE (close combat) is 77, for RANGE
(distant combat) = 70. MasterWork uses constant values for MELEE_DAMAGE = 77 and RANGE = 70 at the seasonal
and primary servers.
Damage - damage that the character will inflict on the target
P.AtkSkill — the power of a physical skill
P.AtkChar — physical attack of character or monster
MultiplicativeBonus — multipliers that change damage
Attribute
PvP damage
PvE damage
Enhancement Effects
Weapon damage spread
Soulshots
Weapon enchantment level
P.DefChar — P. Def. of target
Based on the formula, we can conclude that the main parameters that affect damage are
the skill power and the P. Atk. of the character. This knowledge will allow you to effectively
develop and strengthen your character.
Gladiators with low skill power can increase their strength by modifying (enchanting) weapons.
For daggers with high skill power enchanting weapons is not so effective. The character's power
can be increased by other parameters.
Damage calculation example
For example, take a
Gladiator level 56 who use
Fatal Strike
Lv. 18
against monster
Ancient Gargoyle
Lv. 56
.
Calculations do not include weapon-specific damage spread.
P.AtkSkill — 1831
P.AtkChar — 767
P.DefChar - 411
Let’s consider multipliers separately
Skill Damage = 77 * (1831+767) / 411 = 454 average damage
Multiplier from soulshots- 77 * (1831+767) *
2
/ 411 = 907 average damage
Weapon modification +6 - 77 * (1831+767) * 2 *
1,042
/ 411 = 945 average damage
Attribute (difference between attacker and target +150...299 attribute) —
77 * (1831+767) * 2 * 1.042 *
1.4
/ 411 = 1 323 average damage
+10% of equipment PvP damage —
77 * (1831+767) * 2 * 1.042 * 1.4 *
1
/ 411 = 1,456 average damage
Enchanted skill bonus. Modifiers from effects that increase the power of the skills are multiplied.
So our gladiator is powered by
Final Secret
Lv. 1
(+30% to skill power)
and
Physical Pose
Lv. 1
(+20% to skill power)
will make — 77 * (1831+767) * 2 * 1,042 * 1,4 * 1,1 *
1,3 * 1,2
/ 411 = 2 271 average damage
Critical Chance by skill
For physical skills, the chance of a critical attack (double damage) consists of the basic value multiplied by the modifier
parameter (STR). The modifier (STR) values can be seen at the end of this article.
On the MasterWork project, the chance of a critical attack in PvP and PvE is divided - at the lower levels,
some skills
has a lower crit chance during PvE than PvP, but the values are aligned closer to the
maximum basic skill level. Then the PvE chance is increased by modifying (enchanting) the skill.
For all skills without modification, the basic critical rate is 15%. Then it is
multiplied by the Strength (STR).
For example, the character with 43 STR has a Skill Critical Rate
= 0.15 * 1.33 = 0.1995 = 20% chance to do critical damage by skill.
By enchanting the skill, the Critical Rate during PvE increases up to 25%.
Let's take a character with STR 43 and a skill modified to level 85 (+28...+30)
and count skill critical rate:
In PvP = 0,15 * 1,33 = 0,1995 = 20%
In PVE = 0,25 * 1,33 = 0,3325 = 33%
Skills with charges
Skills that consume or use charges always deal average damage. They are not affected by damage spread,
which depends on the weapon type.
On the MasterWork project, the charges of gladiators and tyrants are not cancelling after death and are saving
on the character longer, than in the original game. These changes are making the charge mechanics more comfortable to use.
Skills that consume charges
Double Sonic Slash
Lv. 1
Sonic Blaster
Lv. 1
Sonic Storm
Lv. 1
Sonic Focus
Lv. 1
Sonic Buster
Lv. 1
Force Burst
Lv. 1
Force Storm
Lv. 1
Force Blaster
Lv. 1
Punch of Doom
Lv. 1
Triple Sonic Slash
Lv. 1
Hurricane Assault
Lv. 1
Force Meditation
Lv. 1
Sonic Barrier
Lv. 1
Force Barrier
Lv. 1
Sonic Move
Lv. 1
Break Duress
Lv. 1
Attack Buster
Lv. 1
Attack Storm
Lv. 1
Weapon Blockade
Lv. 1
Force of Destruction
Lv. 1
Physical Skill with Charges Damage Calculation Formula:
Damage = 77 * ((P.AtkSkill + P.AtkChar) + (P.AtkSkill + P.AtkChar) * (0,2*(ChargeLv - 1)) *
MultiplicativeBonus / P.DefChar
The number 77 is a constant for physical melee attacks laid by Korean
developers. On Interlude chronicles this value was "70", from where it inherited many builds of free servers.
On the chronicles after, up to High Five, the constant value for MELEE_DAMAGE (close combat) is 77, for RANGE
(distant combat) = 70. MasterWork uses constant values for MELEE_DAMAGE = 77 and RANGE = 70 at the seasonal
and primary servers.
The number 0.2 is the basic value of critical rate increase when using charges. Calculations necessarily
count the number of active charges.
Damage — damage the character will inflict on the target
P.AtkSkill — physical skill power
P.AtkChar — physical attack of character or monster
ChargeLv — charge level
MultiplicativeBonus — multipliers that change damage
P.DefChar — P. Def. of the target
Based on the formula, charges increase damage by 20% * (charge level - 1)
For example, take a
Gladiator level 56 who use the skill
Double Sonic Slash
Lv. 12
against monster
Ancient Gargoyle
Lv. 56
.
P.AtkSkill — 1603
P.AtkChar — 767
P.DefChar — 411
ChargeLv — from 1 to 8
MultiplicativeBonus — do not use
Charge 1 level — 77 * ((1603+767) + (1603+767) * 0,2 * (1 - 1)) / 411 = 444 damage
Charge 2 level — 77 * ((1603+767) + (1603+767) * 0,2 * (2 - 1)) / 411 = 533 damage (+20%)
Charge 3 level — 77 * ((1603+767) + (1603+767) * 0,2 * (3 - 1)) / 411 = 622 damage (+40%)
Charge 4 level — 77 * ((1603+767) + (1603+767) * 0,2 * (4 - 1)) / 411 = 710 damage (+60%)
Charge 5 level — 77 * ((1603+767) + (1603+767) * 0,2 * (5 - 1)) / 411 = 799 damage (+80%)
Charge 6 level — 77 * ((1603+767) + (1603+767) * 0,2 * (6 - 1)) / 411 = 888 damage (+100%)
Charge 7 level — 77 * ((1603+767) + (1603+767) * 0,2 * (7 - 1)) / 411 = 977 damage (+120%)
Charge 8 level — 77 * ((1603+767) + (1603+767) * 0,2 * (8 - 1)) / 411 = 1 066 damage (+140%)
Skills with souls
Kamael’s skills, like all others, have a basic critical rate - 15% * STR modifier.
Kamael’s skills can use Souls - an effect similar to Charges of Gladiators and Tyrants. But, unlike
from Charges, if there are active Souls, the skill consumes up to 5 Souls (if there are 2 Souls - use 2,
if 5 - use 5).
Physical Skills with Souls Damage Calculation Formula:
Damage = 77 * ((P.AtkSkill + P.AtkChar) + (P.AtkSkill + P.AtkChar) * 0,05 * SoulCount) *
MultiplicativeBonus / P.DefChar
The number 77 is a constant for physical melee attacks laid by Korean
developers. On Interlude chronicles this value was "70", from where it inherited many builds of free servers.
On the chronicles after, up to High Five, the constant value for MELEE_DAMAGE (close combat) is 77, for RANGE
(distant combat) = 70. MasterWork uses constant values for MELEE_DAMAGE = 77 and RANGE = 70 at the seasonal
and primary servers.
0.05 is the basic value of damage increase when using Souls. When calculating, you must count the number
of active Souls.
Damage — damage the character will inflict on the target
P.AtkSkill — physical skill power
P.AtkChar — physical attack of character and monster
SoulCount — amount of Souls
MultiplicativeBonus — multipliers that change damage
P.DefChar — P. Def. of the target
Based on the formula, each Soul adds 5% to damage,
up to +25% damage.
For example, take a
Soul Breaker level 56 who use the skill
Shining Edge
Lv. 9
against monster
Ancient Gargoyle
Lv. 56
.
P.AtkSkill — 2748
P.AtkChar — 511
P.DefChar — 411
SoulCount — from 0 to 5
MultiplicativeBonus — not used
0 Soul — 77 * ((2748+511) + (1603+511) * 0,05 * 0 / 411 = 610 damage.
1 Soul — 77 * ((2748+511) + (1603+511) * 0,05 * 1 / 411 = 641 damage (+5%).
2 Souls — 77 * ((2748+511) + (1603+511) * 0,05 * 2 / 411 = 672 damage (+10%).
3 Souls — 77 * ((2748+511) + (1603+511) * 0,05 * 3 / 411 = 702 damage (+15%).
4 Souls — 77 * ((2748+511) + (1603+511) * 0,05 * 4 / 411 = 732 damage (+20%).
5 Souls — 77 * ((2748+511) + (1603+511) * 0,05 * 5 / 411 = 763 damage (+25%).
Backstab and Blow skills
Backstab and Blow is a critical attack itself, so the chance of a critical attack (double damage)
depends on the DEX rather than the STR. The values of the DEX modifier can be seen at the end
of the article.
Unlike regular skills, Blow skills have a chance to hit, which can be increased by the equipment and
skills enchanting up to 80%.
These skills are affected by the effects modifiers that increase P. Critical Damage
Skills and items
Skills that affect P. Critical Damage
Skill
Type
Learning
Critical Damage
Lv. 1
Active
Treasure Hunter, Abyss Walker
Focus Death
Lv. 1
Active
Plains Walker, Abyss Walker
Focus Power
Lv. 1
Active
Treasure Hunter, Abyss Walker
Dead Eye
Lv. 1
Active
Phantom Ranger
Vicious Stance
Lv. 1
Active
Warriors, only affects the skills of Rogue
Bear Spirit Totem
Lv. 1
Active
Tyrant
Ogre Spirit Totem
Lv. 1
Active
Tyrant
Hawk Spirit Totem
Lv. 1
Active
Tyrant
Zealot
Lv. 1
Active
Tyrant, Destroyer
Focus Attack
Lv. 1
Active
Warlord
Angelic Icon
Lv. 1
Active
Paladin
Boost Morale
Lv. 1
Active
Paladin, Temple Knight (Vanguard Transformation)
Flame Icon
Lv. 1
Active
Phoenix Knight
Battle Flame Icon
Lv. 1
Active
Phoenix Knight
Seed of Revenge
Lv. 1
Active
Hell Knight, trigger from the skill of the same name
Spirit of Shilen
Lv. 1
Active
Shillien Templar
Battle Spirit of Shillien
Lv. 1
Active
Shillien Templar
Pain of Shillien
Lv. 1
Active
Shillien Templar, trigger from the skill of the same name
Final Servitor
Lv. 1
Active
Summoners
Excessive Royalty
Lv. 1
Active
Summoners, trigger from the skill of the same name
Spirit Power
Lv. 1
Active
Summoners (Spirit of Assasin Transformation)
Dead Eye of Spirit
Lv. 1
Active
Summoners (Spirit of Saggitarius Transformation)
Party Blessing of Queen
Lv. 1
Active
Warlock
Single Blessing of Queen
Lv. 1
Active
Warlock
Blessing of Queen
Lv. 1
Active
Warlock, Feline Queen summon ability
Nightshade - Death Whisper
Lv. 1
Active
Phantom Summoner, Nightshade summon ability
Assassin Servitor
Lv. 1
Active
Spectral Master
Rhythm of Critical
Lv. 1
Active
Swordsinger, Bladedancer
Battle Whisper
Lv. 1
Active
Swordsinger
Death Whisper
Lv. 1
Active
Prophet, Elven Elder, Shillien Elder
Improved Critical Attack
Lv. 1
Active
Prophet, Elven Elder, Shillien Elder
Prophecy of Fire
Lv. 1
Active
Prophet
Revelation of Fire
Lv. 1
Active
Prophet
Counter Critical
Lv. 1
Active
Prophet, trigger from the skill of the same name
Chant of Rage
Lv. 1
Active
Warcryer
Chant of Critical Attack
Lv. 1
Active
Warcryer
Critical of Pa'agrio
Lv. 1
Active
Overlord
Chant of Victory
Lv. 1
Active
Warcryer
Motive of Victory
Lv. 1
Active
Warcryer
Critical Sense
Lv. 1
Active
Kamael
Appetite for Destruction
Lv. 1
Active
Inspector
Lesser Appetite for Destruction
Lv. 1
Active
Inspector
Divine Enchanter Fire Spirit
Lv. 1
Active
Subclass Transformation Level 80
Divine Enchanter Hero Spirit
Lv. 1
Active
Subclass Transformation Level 80
Sacrifice Enchanter
Lv. 1
Active
Subclass Transformation Level 80
Sacrifice Summoner
Lv. 1
Active
Subclass Transformation Level 80
Divine Summoner Final Servitor
Lv. 1
Active
Subclass Transformation Level 80
Pet Death Whisper
Lv. 1
Active
Pets that evolved at level 55
Feral Death Whisper
Lv. 1
Active
A Farm-tamed monster with the title Sharp
Maguen Plasma - Critical
Lv. 1
Active
Collecting Magven's Blue Plasma Level 3
Sword/Blunt Weapon Mastery
Lv. 1
Passive
Dwarf warrior, enchant Option Critical Damage
Dagger Mastery
Lv. 1
Passive
Treasure Hunter, Swordsinger, Plains Walker, Bladedancer, Abyss Walker, Bounty Hunter, enchant Option Critical Damage
Potential Ability
Lv. 1
Passive
Rogue, Elven Scout, Assassin, Scavenger
Collector's Experience
Lv. 1
Passive
Bounty Hunter
Coup De Grace
Lv. 1
Passive
Fortune Seeker
Forge Guardian
Lv. 1
Passive
Maestro
Incredible Endurance
Lv. 1
Passive
Dark Avenger
Furious Soul
Lv. 1
Passive
Kamael
Fire Squad
Lv. 3
Passive
Clan Squad Skill
Seal of Despair
Lv. 1
Attack
Overlord
Tribunal
Lv. 1
Attack
Paladin, Temple Knight, enchant Option "Modify Critical"
Judgment
Lv. 1
Attack
Dark Avenger, Shillien Knight
Judgment of Spirit
Lv. 1
Attack
Summoners (Spirit of Knight Transformation)
Items that affect P. Critical Damage
Weapons with SA Crit. Damage
Olympiad Ring
A
Physical Ring of Queen Ant
C
Enchanted Physical Ring of Queen Ant
S80
Cursed Ring of Queen Ant
1 day
A
Cursed Ring of Queen Ant
7 days
A
Ring of Baium
A
Enchanted Ring of Baium
S84
Infinity Sword
S
(Hero's weapon)
Infinity Cleaver
S
(Hero's weapon)
Infinity Stinger
S
(Hero's weapon)
Passive Talisman - Attack
300 minutes
NG
Foundation
Infinity Passive Talisman - Attack
NG
Foundation
Autoloot Vitality Agathion - Feline Queen
3 Days
NG
(any duration)
Autoloot Vitality Agathion - Seraphim & Queen
for 3 days
NG
Foundation
(any duration)
Clan Oath Brigandine
D
Draconic Leather Armor
Dagger Master
S
Dynasty Platinum Plate
Weapon Master
S
Dynasty Jewel Leather Armor
Dagger Master
S
Dynasty Jeweled Leather Armor
Weapon Master
S
Moirai Leather Breastplate
Attack
S80
Vesper Leather Breastplate
S84
Vesper Noble Leather Breastplate
S84
Vesper Noble Leather Breastplate
Attack
S84
Vesper Noble Leather Breastplate
Defence
S84
Vorpal Leather Breastplate
S84
Vorpal Leather Breastplate
Attack
S84
Vorpal Leather Breastplate {PvP}
Attack
S84
Eternal Leather Breastplate
S84
Eternal Leather Breastplate
Attack
S84
Eternal Leather Breastplate
Defense
S84
Dark Legion's Edge - Thunder
A
Foundation
(MasterWork Item)
Lacerator - Thunder
A
Foundation
(MasterWork Item)
Damascus*Damascus - Thunder
A
Foundation
(MasterWork Item)
Deadman's Glory*Deadman's Glory - Thunder
A
Foundation
(MasterWork Item)
Heaven's Divider - Thunder
S
Foundation
(MasterWork Item)
Gram - Thunder
S
Foundation
(MasterWork Item)
Great Axe - Thunder
B
Foundation
(MasterWork Item)
Demon Splinter - Thunder
S
Foundation
(MasterWork Item)
Doom Crusher - Thunder
A
Foundation
(MasterWork Item)
Dragon Hunter Axe - Thunder
S
Foundation
(MasterWork Item)
Vesper Leather Helmet
S84
Foundation
(MasterWork Item)
Vesper Noble Leather Helmet
S84
Foundation
(MasterWork Item)
Vesper Leather Breastplate
S84
Foundation
(MasterWork Item)
Vesper Noble Houberk
Attack
S84
Foundation
(MasterWork Item)
Vesper Noble Houberk
Defence
S84
Foundation
(MasterWork Item)
Vesper Leather Legging
S84
Foundation
(MasterWork Item)
Vesper Noble Leather Legging
S84
Foundation
(MasterWork Item)
Vesper Leather Gloves
S84
Foundation
(MasterWork Item)
Vesper Noble Leather Gloves
S84
Foundation
(MasterWork Item)
Vesper Leather Boots
S84
Foundation
(MasterWork Item)
Vesper Noble Leather Boots
S84
Foundation
(MasterWork Item)
Vorpal Leather Helmet
S84
Foundation
(MasterWork Item)
Vorpal Leather Breastplate
S84
Foundation
(MasterWork Item)
Vorpal Leather Breastplate
Attack
S84
Foundation
(MasterWork Item)
Vorpal Leather Breastplate
Defense
S84
Foundation
(MasterWork Item)
Vorpal Leather Legging
S84
Foundation
(MasterWork Item)
Vorpal Leather Gloves
S84
Foundation
(MasterWork Item)
Vorpal Leather Boots
S84
Foundation
(MasterWork Item)
Eternal Helmet
Attack Lv. 1
S84
(all levels)
Eternal Leather Helmet
Attack Lv. 1
S84
(all levels)
Adamantite Ring
B
Foundation
(MasterWork Item)
Ring of Black Ore
B
Foundation
(MasterWork Item)
Phoenix Ring
A
Foundation
(MasterWork Item)
Majestic Ring
A
Foundation
(MasterWork Item)
Tateossian Ring
S
Foundation
(MasterWork Item)
Dynasty Ring
S
Foundation
(MasterWork Item)
Moirai Ring
S80
Foundation
(MasterWork Item)
Vesper Ring
S84
Foundation
(MasterWork Item)
Vorpal Ring
S84
Foundation
(MasterWork Item)
Elegia Ring
S84
Foundation
(MasterWork Item)
Effects of items and zones that affect P. Critical Damage
Enchant Light Armor (+8)
Lv. 5
(D-grade)
Enchant Light Armor (+9)
Lv. 6
(D-grade)
Enchant Light Armor (+10)
Lv. 7
(D-grade)
Enchant Light Armor (+8)
Lv. 5
(C-grade)
Enchant Light Armor (+9)
Lv. 6
(C-grade)
Enchant Light Armor (+10)
Lv. 7
(C-grade)
Enchant Light Armor (+8)
Lv. 5
(B-grade)
Enchant Light Armor (+9)
Lv. 6
(B-grade)
Enchant Light Armor (+10)
Lv. 7
(B-grade)
Dryad's Wrath Shirt
S80
(effect of enchant +7 and more)
Hermuncus' Schiavoni
S84
(effect of enchant +10 and more)
Keucereus' Zulfiqar
S84
(effect of enchant +10 and more)
Katenar's Haudegen
S84
(effect of enchant +10 and more)
Lionel's Combat Bow
S84
(effect of enchant +11 and more)
Sayune's Gastraphetes
S84
(effect of enchant +11 and more)
Bludika's Dentaire
Focus
S84
(increases P. Critical Damage for critical attacks only)
Bludika's Dentaire
Mana Up
S84
(increases P. Critical Damage for critical attacks only)
Bludika's Dentaire
Critical Damage
S84
(increases P. Critical Damage for critical attacks only)
Sieghardt's Justice
Soul of Mistwalker
S84
(increases P. Critical Damage for critical attacks only)
Sieghardt's Justice
Soul of Heartseeker
S84
(increases P. Critical Damage for critical attacks only)
Sieghardt's Justice
Soul of Slaughterer
S84
(increases P. Critical Damage for critical attacks only)
Heartseeker's Fury
Spirit of Secutor
S84
(increases P. Critical Damage for critical attacks only)
Heartseeker's Fury
Spirit of Scissor
S84
(increases P. Critical Damage for critical attacks only)
Heartseeker's Fury
Spirit of Dimachaeri
S84
(increases P. Critical Damage for critical attacks only)
Curse of Kiruna’s Quarterstaff
Lv. 1
(counter skill for weapon
Kiruna's Quarterstaff
S84
enchant +13 and more)
Curse of Bludika’s Dentaire
Lv. 1
(counter skill for weapon
Bludika's Dentaire
S84
enchant +13 and more)
Curse of Sieghardt’s Justice
Lv. 1
(counter skill for weapon
Sieghardt's Justice
S84
enchant +13 and more)
Curse of the Plains
Lv. 1
(effect of the combat zone in
Plants of Lizardmen
High Five)
Morale Boost
Lv. 1
(special effect for a group of players in a
Dragon Valley
High Five)
Values for calculation
Weapon damage bonus from modification (enchanting)
Modification level
Bonus value
Modification Level
Bonus value
0
1
10
1,07
+1
1,007
+11
1,077
+2
1,014
+12
1,084
+3
1,021
+13
1,091
+4
1,028
+14
1,098
+5
1,035
+15
1,105
+6
1,042
+16
1,112
+7
1,049
+8
1,056
+9
1,063
Modification parameter STR
STR
Value
STR
Value
STR
Value
STR
Value
STR
Value
10
0.42
20
0.59
30
0.84
40
1.20
50
1.71
11
0.43
21
0.61
31
0.87
41
1.24
51
1.77
12
0.45
22
0.63
32
0.90
42
1.29
52
1.83
13
0.46
23
0.66
33
0.94
43
1.33
53
1.90
14
0.48
24
0.68
34
0.94
44
1.38
54
1.97
15
0.50
25
0.71
35
1.01
45
1.43
55
2.04
16
0.51
26
0.73
36
1.04
46
1.48
56
2.11
17
0.53
27
0.76
37
1.08
47
1.54
57
2.19
18
0.55
28
0.78
38
1.12
48
1.59
58
2.27
19
0.57
29
0.81
39
1.16
49
1.65
59
2.35
Modification parameter DEX
DEX
Value
DEX
Value
DEX
Value
DEX
Value
10
0.92
20
1.01
30
1.10
40
1.20
11
0.93
21
1.01
31
1.11
41
1.21
12
0.94
22
1.02
32
1.12
42
1.22
13
0.94
23
1.03
33
1.13
43
1.24
14
0.95
24
1.04
34
1.14
44
1.25
15
0.96
25
1.05
35
1.15
45
1.26
16
0.97
26
1.06
36
1.16
46
1.27
17
0.98
27
1.07
37
1.17
47
1.28
18
0.99
28
1.08
38
1.18
48
1.29
19
1.00
29
1.09
39
1.19
49
1.30
Can be interesting
Game mechanics: Damage from front, side, back
Game mechanics: Damage from shot range
Game mechanics: Hidden weapon parameters
Dual daggers and blunts
Enchantment bonuses for sets D/C/B/A/S Grade
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