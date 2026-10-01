"""Author the BG3 static-art inventory and individual ImageGen prompts (UTF-8)."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art' / 'static-v1'
OUT.mkdir(parents=True, exist_ok=True)
PALETTES = {
    'common': 'muted jade teal with pale ivory luminous strokes and a tiny antique-gold accent',
    'taixuan': 'cool pale jade, turquoise and moon-white luminous strokes, calm restrained aura',
    'tianqing': 'ochre gold, pale amber-white luminous strokes and charcoal contrast, force energy not fire',
    'xueyan': 'deep crimson, pale rose luminous strokes and dark plum contrast, dangerous blood-energy aura',
    'xingge': 'deep teal-green, pale warm ivory luminous strokes and a small old-gold accent',
}
rows = []
def add(id, name, group, kind, subject, source='20-eastern-sword-cultivator-gdd.md', **extra):
    rows.append(dict(id=id, name=name, group=group, kind=kind, subject=subject, source=source, **extra))

# Class emblems: one lineage, four paths, no invented faction/religion.
add('badge_sword_cultivator','东方剑修','common','badge','One dignified upward silver Chinese jian sword, a compact antique-gold circular sword-energy frame with four understated open arcs, pale jade inset; one lineage with four paths.')
add('badge_taixuan','太玄','taixuan','badge','An upward slender silver Chinese jian sword with a pale jade jewel, sparse antique-gold closed circular cloud filigree, serene symmetrical negative space, fine restrained ray accents.')
add('badge_tianqing','天倾','tianqing','badge','An upward broad powerful steel Chinese sword, antique-gold cracked radial frame split outward by the sword, heavy angular wedges and a small amber jewel; lucid defiant overwhelming strength, no fire.')
add('badge_xueyan','血魇','xueyan','badge','An upward sharp dark-steel Chinese sword, antique-gold angular broken ring with restrained inward hooks, three deep crimson jewel insets and sparse crimson vapor; ominous corrupted sword lineage, no Bhaal skull or religious symbol.')
add('badge_xingge','行歌','xingge','badge','An upward elegant silver Chinese jian sword, two antique-gold open curved supporting arms forming a protective heraldic ring, small teal gemstone, paired graceful routes suggesting companionship; no musical instrument.')

# Shared activatable skills, selectors and sustained features.
for id,name,subject in [
 ('skill_yujian','御剑术','One diagonal Chinese jian blade with a single sweeping outbound trail and a shorter returning arc; remotely flying sword returns to the hand; no hand needed.'),
 ('skill_sword_strike','近身剑术','One diagonal Chinese jian sword with one short sharp curved slash; unmistakably close sword attack, simpler than remote sword control.'),
 ('skill_tiaoxi','调息','A minimal seated meditating human silhouette, one small sword upright at the torso and two inward flowing breath arcs gathering into the chest; no face details.'),
 ('skill_qi_guard','剑气护体','A simple upright human torso enclosed by one clean luminous sword-energy protective circle, a small diagonal incoming blade deflected off its edge.'),
 ('skill_sword_flight','御剑飞行','A simple standing human silhouette balanced with both feet on one horizontally flying Chinese jian sword, two clean airflow strokes beneath; sword supports person, not winged flight.'),
 ('skill_recall_sword','召剑','One sword flying hilt-first toward a clearly simplified open hand, with a single curved returning trail.'),
 ('skill_qi_sword','凝气成剑','Several fine energy threads coalescing into one slender upright Chinese jian sword outline, unformed wisps at its base and a sharply defined tip.'),
 ('skill_control_release','主动解控','One small upright sword cutting across a broken chain loop around a minimal torso; two separated chain ends open outward, unmistakable release from restraint.'),
 ('skill_focus_target','改换重点目标','A single small faceless enemy silhouette selected by four open inward pointing sword tips, one simple targeting diamond; no numeral or crosshair UI border.'),
]: add(id,name,'common','skill',subject)

skills = {
 'taixuan': [
 ('zhaoxi','照隙','One fine diagonal spectral sword tip entering a narrow bright gap between two dark armor plate shapes; a single pinpoint opening, precision rather than explosion.'),
 ('qinghui','清辉返照','One closed protective crescent ring around a slender upright sword; one small incoming arrow bounces off the ring and turns into one returning sword ray.'),
 ('jiuxiao','九霄剑雨','Five slender spectral swords descending together in a compact fan onto one shallow ground arc; instantaneous sword rain, no enclosing sustained domain circle.'),
 ('liuguang','流光追星','Exactly four slender spectral sword trajectories curve and converge on one small star-like impact point; clear four paths and a single concentrated target.'),
 ('xinghe','星河倒悬','One tall upright central spectral sword within a stronger protective closed arc and three small outward repelling sword rays; defense with reversal, distinct from a rain of swords.'),
 ('taiqing','太清剑域','A low elliptical domain boundary surrounding one tiny upright sword-bearing figure, three narrow swords descending inside the boundary; sustained mobile sword domain, clean center.'),
 ('yixiantian','玄极·一线天','Several fine curved spectral sword threads converge into ONE long perfectly straight piercing sword beam cutting across two offset dark armor fragments, one very bright first impact; no broad explosion.'),
 ('guiyuan','归元','A minimal torso with two returning pale jade energy arcs gathering into a bright small center at the chest, one small upright sword below, restorative rejoining energy.'),
 ],
 'tianqing': [
 ('nifeng','逆锋','One substantial diagonal sword with a single wide open sweeping arc and two small outward displaced silhouettes; forceful sweeping sword attack.'),
 ('wanjun','万钧剑势','One broad vertical sword presses down over three tiny angular enemy silhouettes beneath a low heavy horizontal energy arc, visual compression and suppression, no rain of blades.'),
 ('lietian','裂天一剑','One enormous diagonal blade cleaves one clearly split armored plate in two, narrow separation and sharp pale impact line, single-target armor breaking.'),
 ('tianbeng','天崩剑啸','One broad forward-facing sword tip releases a powerful ninety-degree fan of three thick force arcs, a single central impact accent, wide frontal destruction.'),
 ('tianfeng','天锋破阵','One thick horizontal giant sword rushes forward along a clear straight path, two angular enemy forms pushed sideways, heavy forward thrust rather than falling.'),
 ('tianjian','天剑坠世','One enormous sword points vertically downward into one broad circular impact wave with a few broken ground shards; sword falling from above, decisive ground impact.'),
 ('bafang','八方灭阵','Exactly eight strong sword blades arranged radially outward from one central point, readable eight-direction starburst, no downward falling swords.'),
 ('tiandi','天地剑劫','Exactly three enormous parallel sword blades descending toward one shared low elliptical impact area, compact grouping with clear three blade silhouettes.'),
 ('xushi','蓄势','One broad upright sword gathers two heavy inward spiraling energy arcs into the blade, compact held-back strength, no impact explosion.'),
 ('nixi','逆息回生','One bold split heart-like life core rejoins around an upright sword under two rising restorative arcs; vigorous self-healing, no cross medical sign.'),
 ],
 'xueyan': [
 ('luexue','掠血','One thin crimson sword pierces one simplified target mark and draws a returning curved blood-energy thread toward the hilt; single-target life siphon, no gore.'),
 ('chuanshen','血影穿身','One diagonal crimson sword with one long straight penetrating trail cutting through two small faceless silhouettes, a clear single continuous dash route.'),
 ('ranxue','燃血入狂','One small heart core feeds three sharp upward crimson energy spikes around an upright dark sword, deliberate self-sacrifice and rising frenzy; symbolic, no exposed organs.'),
 ('liancheng','血影连城','Exactly four short sharp sword strokes connected by a clear zigzag path between three small target points; successive pursuit route, no arena circle.'),
 ('nixue','逆血狂澜','Six sharp crimson sword rays burst outward around one central dark upright blade, followed by two small inward returning wisps; explosive backlash.'),
 ('xuehai','血海噬灵','One elliptical crimson domain around a tiny upright sword-bearing figure, three inward hooked energy streams siphoning strength toward the center, sparse dark plum core.'),
 ('wusheng','血魇·无生','Exactly three simple translucent sword-bearing shadow silhouettes close inward around one central target dot, two short slash accents for each shadow, iconic not detailed figures.'),
 ('huichao','回潮','Two curved crimson energy tides fold inward and rejoin one small split life core around an upright sword tip; restorative inward tide, no attack target.'),
 ('damage_mode','剑气伤害切换','One upright sword divided into a crimson half and a pale neutral-ivory half, two small opposite curved arrows; choose necrotic or force energy, no extra resource or elemental fire.'),
 ],
 'xingge': [
 ('wenlu','问路','One diagonal sword opens a small target diamond, a second thinner following sword route approaches the same point; creating a follow-up opportunity.'),
 ('huifeng','回风解围','Two opposing curved sword-wind arcs open space around one small ally silhouette, a short protective arc shields the ally, no teleport portal.'),
 ('fuchen','拂尘','One fine sword-guided airflow sweeps two broken chain links away from a simple ally torso, clear release from restraint with light feathered strokes, no broom.'),
 ('chengfeng','乘风破围','One small ally silhouette steps through a large open protective sword arc, a horizontal airflow path leads outward through the gap; rescue and escape movement.'),
 ('tongzhou','同舟破浪','Three complementary sword paths from distinct directions converge on one enemy point at the same time, one leading sword slightly stronger; immediate coordinated attack, no literal boat.'),
 ('fengyu','风雨同归','One central upright protective sword-bearing figure receives two curved incoming lines from two smaller ally silhouettes, a broad sheltering arc overhead; sharing allies damage, no healing cross.'),
 ('zhangjian','仗剑行歌','Four small glowing companion nodes linked by graceful sword-energy arcs, one flying sword follows a second leading sword stroke; sustained team offensive resonance, no music notes.'),
 ('xiangfu','相扶','Two simple open hands facing one another support a small restored life core, one understated sword shape below, cooperative emergency healing.'),
 ],
}
for group,items in skills.items():
    for slug,name,subject in items: add('skill_'+group+'_'+slug,name,group,'skill',subject)

# Distinct states/passives/resources are visual assets, not newly invented mechanics.
features = [
 ('passive_sword_heart','剑心／感知御剑','common','passive','One upright sword piercing a small open eye-shaped perception motif, intuitive sword awareness, no realistic eyeball.'),
 ('passive_basic_defense','入门防护','common','passive','One small sword over a modest shield outline, exactly one clean protecting arc, understated foundation defense.'),
 ('passive_continuous_strikes','连贯出剑','common','passive','Three clean offset short sword strokes connected by one uninterrupted flowing arc, consecutive attacks, no numbers.'),
 ('passive_control_resist','抗控基础','common','passive','One calm open eye above a stable sword, broken knot outside an intact small protective circle, bodily and mental control resistance.'),
 ('passive_auto_release','反应脱困','common','passive','A chain loop splits at a bright sword tip with one short recoil ray, immediate prevention of disabling control.'),
 ('passive_taixuan_breath','沟通天地／自愈','taixuan','passive','A small calm torso and upright sword receive two thin downward flowing strands from a wide sky arc, stable breathing and natural recovery.'),
 ('passive_tianqing_fortitude','深厚体魄','tianqing','passive','A broad upright sword supports one heavy intact shield-shaped torso, thick sturdy silhouette, grounded endurance.'),
 ('passive_xueyan_siphon','饮血','xueyan','passive','One small crimson droplet-like energy core follows a hook-shaped returning sword trail into a pale life point; symbolic life siphon without gore.'),
 ('passive_xueyan_finish','斩杀回元','xueyan','passive','One downward sword stroke severs a small dark target diamond and releases three small energy motes returning upward to the blade.'),
 ('passive_xueyan_unhindered','无视借机攻击','xueyan','passive','One diagonal sword glides through an open gap between two interrupted attack arcs, fast evasive passing, not teleportation.'),
 ('passive_xingge_sidebyside','并肩','xingge','passive','Exactly two simple standing silhouettes shoulder to shoulder under one broad protective sword arc, mutual protection.'),
 ('passive_xingge_cooperation','协作回气','xingge','passive','Two distinct sword strokes meet and release a small returning breath spiral toward one central life-energy point, teamwork restores energy.'),
 ('status_weakpoint','破绽','taixuan','status','Two angular armor plates with one small bright exposed gap marked by a fine sword-tip ray, target weakness debuff.'),
 ('status_followup','跟进机会','xingge','status','One target point surrounded by two open arcs with a second slim sword approaching, ally follow-up marker.'),
 ('status_control_resistance','解控后抵抗','common','status','A small stable upright sword surrounded by an intact pale circle and two separated chain fragments outside, short resistance after release.'),
 ('status_blood_robe','血衣','xueyan','status','A simple armored torso wrapped in a thin crimson protective coat-shaped outline, three small siphoned energy motes seal its edge, blood-energy shield.'),
 ('status_frenzy','癫狂','xueyan','status','One sharply tilted sword with a jagged split halo and three rising crimson spikes, building violent frenzy; no face or numerical layers.'),
 ('status_armor_break','破甲','tianqing','status','One thick sword tip breaks a clearly cracked shield into two separated angular halves, debuffed armor.'),
 ('status_suppression','剑势镇压','tianqing','status','Three descending heavy pressure bars above a small bent enemy silhouette, short sword tip above, pressure slows and weakens attacks.'),
 ('status_counter_ready','护体反击','taixuan','status','One compact closed sword guard arc turns one incoming narrow ray back outward into a small sword arrow, readiness to counter.'),
 ('status_sword_domain','太清剑域增益','taixuan','status','A small upright sword inside a clear elliptical field with three upward pale enhancing rays, domain aid for allies.'),
 ('status_sword_domain_debuff','太清剑域压制','taixuan','status','A small dark target within an elliptical sword boundary pressed by three thin inward sword tips, domain suppression for enemies.'),
 ('status_tianqing_might','天倾攻势强化','tianqing','status','A broad upright sword with two expanding strong upward arcs and a small white edge flare, temporary increased offense.'),
 ('status_tianqing_aftershock','坠剑余威','tianqing','status','One grounded downward sword stands inside two concentric low shockwave arcs, sustained nearby force aftermath.'),
 ('status_dash_defense','穿行保护','xueyan','status','One moving diagonal sword wrapped in a short slanted protective arc with two trailing strokes, defense after actual movement.'),
 ('status_xingge_protection','回风保护','xingge','status','One ally torso supported by two graceful curved sword-wind brackets, short protective effect.'),
 ('status_escape','破围脱险','xingge','status','A small running silhouette exits a clean gap in a sword arc, two interrupted attack trails behind, safe movement.'),
 ('status_damage_share','分担伤害','xingge','status','Two small ally points send curved streams to one larger guarded central point, clear incoming shared injury, no offensive arrow.'),
 ('status_team_resonance','御剑呼应','xingge','status','A small leading sword trail followed by one distinct flying sword, two linked luminous nodes, triggered follow-up.'),
 ('resource_sword_yuan','剑元','common','resource','One simple slender vertical sword-energy crystal inside a small open breath ring, iconic reusable energy token, no numeral.'),
 ('resource_frenzy','癫狂资源','xueyan','resource','One compact jagged crimson three-point energy shard pierced by a short blade, accumulating frenzy token, no numeral.'),
]
for id,name,group,kind,subject in features:add(id,name,group,kind,subject)

# Static illustrations are promotional/background art, never required gameplay gates.
add('cover_lineage','一脉四途·Mod封面','common','illustration','A lone faceless Eastern sword cultivator seen from behind, robes and a real straight sword, stands on a weathered Faerun stone ruin overlooking a misty landscape. Four subtly different sword-energy routes arc from one source: fine jade-white precision, broad ochre-gold force, crimson shadow, and paired teal-gold companion paths. A mysterious small distant unidentifiable doorway suggests crossing worlds, no literal key design, no gods, no logos. Square editorial fantasy cover, solitary dignity, grounded stone metal cloth textures, warm dusk and cool mist, clear central silhouette, no text.')
add('background_founder','异乡传承·背景插画','common','illustration','A solitary Eastern sword immortal viewed from behind, gender and age not visually specified, simple layered robes, one straight sword held lowered, standing before a weathered unfamiliar fantasy stone arch with a narrow luminous interworld opening. An alien but grounded Faerun landscape beyond, lonely cool atmosphere, one quiet lineage left in a foreign world, no followers crowd, no dragon, no invented key close-up, no text. Cinematic landscape wide illustration, restrained painterly realism.')

ICON_BASE = ('Create exactly ONE original Baldur\'s Gate 3 compatible fantasy RPG ability icon. '
 'Square composition, transparent background with a restrained semitransparent pigment aura fading smoothly to alpha at the edges. '
 'Visual language of vanilla BG3 spell icons: bold softly luminous hand-painted linework, slightly worn brush edges, variable stroke thickness, pale contrasting contours, '
 'simple symbolic shapes, generous negative space and only a few small decorative motes. Main silhouette occupies roughly 72% of square, comfortably inset. '
 'EVERY sword, hand and person is a SIMPLIFIED TWO-TONE LUMINOUS CONTOUR DRAWING, with hollow or flat pigment interiors. '
 'Sword hilts are plain short crossbars; do NOT draw ornate guards, gemstones, jewelry, decorative tassels, realistic steel shading or material bevels. '
 'Think glowing chalk rune drawn on a faded pigment wash, not a collectible weapon illustration. '
 'This is an iconic luminous pictogram, NOT a cinematic illustration, NOT a realistic product rendering, NOT a metallic class badge. '
 'No ornate border, no letter, no number, no readable text, no watermark, no checkerboard, no montage, no grid. '
 'Do not render detailed faces, full battle scenes, background landscapes or excessive smoke. Major symbol and action must read clearly at 64 pixels. ')
BADGE_BASE = ('Create exactly ONE original Baldur\'s Gate 3 compatible in-game class heraldic emblem. '
 'Centered square transparent composition, compact silhouette occupying 78% of the image with ample transparent margin. '
 'Hand-painted antique-gold metal rim, recessed dark details, steel bevel highlights, selective colored jewel accents, '
 'inspired by vanilla BG3 fighter/wizard class badge material treatment. Central Chinese jian sword stays unmistakable. '
 'No text, number, watermark, square UI frame, photoreal product photography, checkerboard, dragon, yin-yang, deity sigil or invented faction. ')
for row in rows:
    if row['kind']=='badge':
        row['prompt']=BADGE_BASE+'Subject: '+row['subject']+' Palette accents: '+PALETTES[row['group']]+'.'
        row['transparent']=True
        row['exports']=['class_300','class_hotbar_64']
    elif row['kind']=='illustration':
        row['prompt']='Create ONE original BG3-compatible painted fantasy background/promotional illustration. '+row['subject']
        row['transparent']=False
        row['exports']=['illustration_master']
    else:
        row['prompt']=ICON_BASE+'Palette: '+PALETTES[row['group']]+'. Subject: '+row['subject']
        row['transparent']=True
        row['exports']=['hotbar_64','controller_144','tooltip_380']
    row['status']='pending'
    row['master']=f"masters/{row['kind']}/{row['id']}.png"
    row['attempts']=0
sources={}
for name in ['17-bg3-art-style-guide.md','19-skill-specifications-draft.md','20-eastern-sword-cultivator-gdd.md','21-player-facing-skill-text-draft.md']:
    sources[name]=hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest()
manifest={'version':1,'created':'2026-09-29','generation_route':'built-in image_gen','sources_sha256':sources,'palette_status':'First art direction following docs/17; adjustable after visual review','assets':rows}
target=OUT/'manifest.json'
if target.exists():
    old=json.loads(target.read_text('utf-8'))
    old_by_id={r['id']:r for r in old['assets']}
    for row in rows:
        previous=old_by_id.get(row['id'],{})
        for key in ['status','attempts','source_generated_path','width','height','alpha_extrema','review_notes','master','basename','revision_history','references']:
            if key in previous:row[key]=previous[key]
        if previous.get('status')=='complete' or previous.get('revision_history'):row['prompt']=previous['prompt']
target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'prompts.jsonl').write_text(''.join(json.dumps({k:r[k] for k in ['id','name','kind','group','prompt','transparent']},ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
print(json.dumps({'count':len(rows),'kinds':{k:sum(r['kind']==k for r in rows) for k in sorted({r['kind'] for r in rows})},'manifest':str(target)},ensure_ascii=False))
