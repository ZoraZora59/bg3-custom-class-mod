"""Confirmed 2026-09-29 design, shared by generation and independent validation.

The GDD is the authority. This is an implementation mapping, not a new design.
"""
from uuid import UUID, uuid5

NAMESPACE = UUID('41c5219f-c813-48bb-bad0-842dd973eb65')
MOD = 'EasternSwordCultivator'


def guid(key):
    return str(uuid5(NAMESPACE, key))


MODULE_UUID = guid('module')
FOLDER = f'{MOD}_{MODULE_UUID}'
VERSION64 = (1 << 55) | 10
PUBLISH_HANDLE = 6417135
CAPACITIES = [0, 6, 10, 14, 18, 24, 26, 28, 30, 40, 44, 50]
BRANCHES = {
    'taixuan': dict(name='太玄', english='Taixuan', hp=1.8, attack=6, ac=6, reduction=20),
    'tianqing': dict(name='天倾', english='Tianqing', hp=2.5, attack=4, ac=2, reduction=35),
    'xueyan': dict(name='血魇', english='Xueyan', hp=1.6, attack=3, ac=2, reduction=20),
    'xingge': dict(name='行歌', english='Xingge', hp=1.1, attack=1, ac=1, reduction=0),
}
CLASS_DESCRIPTION = '承自异乡的剑道，以剑心御动天地之气。以剑心御剑破敌；修行者或一心求道，或弃道求力，或走火入魔，或与友同行。'
BRANCH_DESCRIPTIONS = {
    'taixuan': '心照万法，剑通天地。以剑气洞悉破绽，护身反击。持盾或穿着中甲、重甲时，剑术与剑气防护失效。',
    'tianqing': '舍道求力，逆锋不屈。以沉重剑势摧破敌阵，凭强健体魄承受攻势。',
    'xueyan': '剑心入魇，饮血成狂。在穿行与杀戮中夺取生命，越战越烈。',
    'xingge': '仗剑同行，扶危解困。以灵动剑术接应同伴，共同破敌。持盾或穿着中甲、重甲时，剑术与剑气防护失效。',
}

# key, level, kind, cost, distance, radius/width, dice, segments, base, action
# AUTO chooses exactly one basis: main sword, otherwise offhand sword, otherwise 2d6 + Wisdom.
ROWS = [
    ('yujian', 1, 'attack', 0, 18, 0, '', 1, 'WQ', 'sword'),
    ('sword_strike', 1, 'attack', 0, 3, 0, '', 1, 'WQ', 'sword'),
    ('tiaoxi', 2, 'recover', 0, 0, 0, '', 1, '', 'sword'),
    ('qi_guard', 2, 'guard', 2, 0, 0, '', 1, '', 'bonus'),
    ('sword_flight', 5, 'flight', 0, 24, 0, '', 1, '', 'bonus'),
    ('qi_sword', 3, 'mode', 0, 0, 0, '', 1, '', 'free'),
    ('control_release', 5, 'release', 4, 0, 0, '', 1, '', 'bonus'),
    ('focus_target', 9, 'focus', 0, 18, 0, '', 1, '', 'free'),
    ('taixuan_zhaoxi', 3, 'attack', 0, 18, 0, '2d8', 1, 'WQ', 'sword'),
    ('taixuan_qinghui', 4, 'guard', 4, 0, 0, '', 1, '', 'bonus'),
    ('taixuan_jiuxiao', 8, 'area_save', 4, 18, 6, '8d8', 1, 'Q', 'sword'),
    ('taixuan_liuguang', 6, 'attack', 10, 18, 0, '4d8', 4, 'Q', 'sword'),
    ('taixuan_xinghe', 7, 'self_area_save', 10, 0, 6, '10d8', 1, 'Q', 'sword'),
    ('taixuan_taiqing', 9, 'domain', 10, 0, 6, '2d8', 1, 'Q', 'sword'),
    ('taixuan_yixiantian', 12, 'piercing_line', 20, 30, 2, '36d8', 1, 'Q', 'sword'),
    ('taixuan_guiyuan', 4, 'heal', 6, 0, 0, '', 1, '', 'bonus'),
    ('tianqing_nifeng', 3, 'cone_attack', 0, 12, 2, '3d8', 1, 'W', 'sword'),
    ('tianqing_wanjun', 4, 'area_attack', 4, 18, 6, '6d8', 1, 'W', 'sword'),
    ('tianqing_lietian', 8, 'attack', 4, 18, 0, '12d8', 1, 'W', 'sword'),
    ('tianqing_tianbeng', 6, 'cone_attack', 10, 12, 0, '18d8', 1, 'W', 'sword'),
    ('tianqing_tianfeng', 7, 'dash_attack', 10, 18, 3, '22d8', 1, 'W', 'sword'),
    ('tianqing_tianjian', 9, 'leap_area_save', 10, 24, 9, '26d8', 1, 'W', 'sword'),
    ('tianqing_bafang', 12, 'self_area_save', 20, 0, 18, '44d8', 1, 'W', 'sword'),
    ('tianqing_tiandi', 12, 'area_attack', 20, 24, 9, '14d8', 3, 'W', 'sword'),
    ('tianqing_xushi', 3, 'recover', 0, 0, 0, '', 1, '', 'sword'),
    ('tianqing_nixi', 3, 'heal', 5, 0, 0, '', 1, '', 'bonus'),
    ('xueyan_luexue', 3, 'attack', 0, 18, 0, '2d6', 1, 'WQ', 'sword'),
    ('xueyan_chuanshen', 4, 'dash_attack', 4, 12, 2, '4d6', 1, 'WQ', 'sword'),
    ('xueyan_ranxue', 8, 'blood_cost', 0, 0, 0, '', 1, '', 'bonus'),
    ('xueyan_liancheng', 6, 'chain_attack', 10, 24, 0, '1d6', 4, 'Q', 'sword'),
    ('xueyan_nixue', 7, 'self_area_save', 10, 0, 6, '8d6', 1, 'Q', 'sword'),
    ('xueyan_xuehai', 9, 'domain', 10, 0, 6, '2d6', 1, 'Q', 'sword'),
    ('xueyan_wusheng', 12, 'attack', 20, 24, 0, '', 6, 'Q', 'sword'),
    ('xueyan_huichao', 4, 'heal', 6, 0, 0, '', 1, '', 'bonus'),
    ('xueyan_damage_mode', 3, 'mode', 0, 0, 0, '', 1, '', 'free'),
    ('xingge_wenlu', 3, 'attack', 0, 18, 0, '1d4', 1, 'W', 'sword'),
    ('xingge_huifeng', 4, 'protect', 4, 18, 3, '', 1, '', 'bonus'),
    ('xingge_fuchen', 8, 'release', 4, 18, 0, '', 1, '', 'bonus'),
    ('xingge_chengfeng', 6, 'rescue', 10, 18, 3, '8d6', 1, 'W', 'sword'),
    ('xingge_tongzhou', 7, 'cooperate', 10, 18, 6, '10d6', 1, 'W', 'sword'),
    ('xingge_fengyu', 9, 'share', 10, 0, 6, '', 1, '', 'sword'),
    ('xingge_zhangjian', 12, 'resonance', 20, 0, 6, '2d6', 1, 'Q', 'sword'),
    ('xingge_xiangfu', 3, 'heal', 4, 18, 0, '', 1, '', 'bonus'),
]
SPELLS = {}
for key, level, kind, cost, distance, radius, dice, segments, base, action in ROWS:
    branch = key.split('_')[0]
    SPELLS[key] = dict(key=key, level=level, kind=kind, cost=cost, range=distance,
                       radius=radius, dice=dice, segments=segments, base=base,
                       action=action, branch=branch if branch in BRANCHES else 'common')

# Legacy spell IDs remain deserializable but are never newly granted.
for key in ('focus_target', 'qi_sword', 'sword_strike'):
    SPELLS[key]['retired'] = True
for row in SPELLS.values():
    if row['base'] in ('W', 'WQ', 'Q'):
        row['legacy_base'] = row['base']
        row['base'] = 'AUTO'

# Directly selected sword strikes can also attack environmental items. Keep
# automatic domains, support, rushes and area victim selection character-only.
for key in ('yujian', 'taixuan_zhaoxi', 'taixuan_liuguang', 'tianqing_lietian',
            'xueyan_luexue', 'xueyan_liancheng', 'xueyan_wusheng', 'xingge_wenlu'):
    SPELLS[key]['targetItems'] = True


PASSIVES = {
    'sword_heart': (1, 'common'), 'basic_defense': (1, 'common'),
    'continuous_strikes': (5, 'common'), 'control_resist': (3, 'solo'),
    'auto_release': (4, 'solo'), 'taixuan_breath': (3, 'taixuan'),
    'tianqing_fortitude': (3, 'tianqing'), 'xueyan_siphon': (3, 'xueyan'),
    'xueyan_finish': (3, 'xueyan'), 'xueyan_unhindered': (3, 'xueyan'),
    'xingge_sidebyside': (3, 'xingge'), 'xingge_cooperation': (3, 'xingge'),
}


def spells_at(branch, level):
    result = []
    for key, spec in SPELLS.items():
        # Retain legacy Stats IDs for saved references, without granting duplicate buttons.
        if key in ('sword_strike', 'qi_guard', 'tianqing_xushi') or spec.get('retired'):
            continue
        if spec['level'] != level:
            continue
        if spec['branch'] == branch and key not in ('qi_sword', 'control_release', 'focus_target'):
            result.append(key)
        elif spec['branch'] == 'common':
            if key == 'qi_sword' and branch in ('taixuan', 'xueyan'):
                result.append(key)
            elif key == 'control_release' and branch in ('taixuan', 'tianqing', 'xueyan'):
                result.append(key)
            elif key == 'focus_target' and branch == 'taixuan':
                result.append(key)
            elif key not in ('qi_sword', 'control_release', 'focus_target') and branch == 'common':
                result.append(key)
    return result

# Secondary control rolls are native engine saves; Lua receives only failed-save markers.
HIT_CONTROLS = {
    'xingge_huifeng': dict(ability='Dexterity',slow=.5,attack=-2,duration=2),
    'taixuan_xinghe': dict(ability='Strength',push=3,duration=1),
    'tianqing_nifeng': dict(ability='Strength',push=2,duration=1),
    'tianqing_wanjun': dict(ability='Constitution',slow=.5,attack=-2,duration=2),
    'tianqing_lietian': dict(ability='Strength',ac=-3,duration=3),
    'tianqing_tianbeng': dict(ability='Strength',push=3,ac=-3,duration=3,mainOnly=True),
    'tianqing_tianfeng': dict(ability='Strength',push=3,prone=1,attack=-3,duration=2),
    'tianqing_tianjian': dict(ability='Strength',push=4,prone=1,slow=.5,ac=-4,duration=3),
    'tianqing_bafang': dict(ability='Strength',push=6,prone=1,ac=-5,duration=3),
    'tianqing_tiandi': dict(ability='Strength',prone=1,slow=.5,ac=-5,duration=3),
    'xingge_chengfeng': dict(ability='Strength',push=2,duration=1),
}
for _key,_control in HIT_CONTROLS.items(): SPELLS[_key]['hitControl']={**_control,'marker':'ESC_SAVEFAIL_'+_key.upper()}
