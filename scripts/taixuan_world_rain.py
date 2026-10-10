"""Editable world-falling columns and native-receipt-gated registration.

This author returns XML only. generate_resources is for the root build after
actual AllSpark compilation, never a fake binary or authoring acceptance.
"""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import taixuan_visual_polish as tx
from sword_cultivator_spec import FOLDER, guid
from sword_vfx_resources import _attribute, _convert, _document, _metadata, _write_xml

SUBDIR='TaixuanWorldRain'
EDITOR=Path('Editor/Mods')/FOLDER/'Assets/Effects/Sword'/SUBDIR
COMPILED=Path('Public')/FOLDER/'Assets/Effects/Effects_Banks/Sword'/SUBDIR
RECEIPT=COMPILED/'native-compile.json'
BANK=Path('Public')/FOLDER/'Content/Assets/Effects/Effects/Sword/[PAK]_ESC_TaixuanWorldRain/_merged.lsx'
VARIANTS=('spiritual','steel')
ROLES=('jiuxiao','taiqing','jiuxiao_background')
# Native Visual.Objects MaterialID, checked from extracted official resource banks.
NATIVE_MATERIALS={'spiritual':'897a51e0-39fb-7d08-0437-03ec27637571',
                  'steel':'4146ad12-b6ec-3601-5a9b-6a62a01b54c3'}
HEIGHT=7.0
CONTACT=.08
DURATION=.80
SIZE=(.32,2.1,.15)

def effect_name(role,variant):
    return f'VFX_ESC_Taixuan_{role.title()}_WorldRain_{variant.title()}_01'

def effect_guid(role,variant):
    return guid('vfx/taixuan/world-rain/'+role+'/'+variant)

def paths(role,variant):
    name=effect_name(role,variant)
    return EDITOR/(name+'.lsefx'),COMPILED/(name+'.lsfx')

def transformed_bounds(low,high,scale,spiritual,position=(0,0,0)):
    points=[]
    for x,y,z in itertools.product(*zip(low,high)):
        p=(x*scale[0],-y*scale[1],-z*scale[2]) if spiritual else (x*scale[0],z*scale[2],-y*scale[1])
        points.append(tuple(p[i]+position[i] for i in range(3)))
    return tuple(min(p[i] for p in points) for i in range(3)),tuple(max(p[i] for p in points) for i in range(3))

def _column(data,role,variant,dictionary):
    assert role in ROLES and variant in VARIANTS
    root,origin=tx.fx.projectile(Path(data))
    root=copy.deepcopy(root)
    root.set('id',guid('vfx/taixuan/world-rain/editor/'+role+'/'+variant))
    root.find('phases').clear()
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            if track.find('component').get('class')!='BoundingSphere':group.remove(track)
        if not group.findall('track'):root.find('trackgroups').remove(group)
    template,sword_origin=tx._native_sword_template(Path(data),dictionary)
    model=tx._native_added_model(root,'Fixed world vertical rain sword',role+'/'+variant,template,DURATION)
    tx._native_prop(model,tx.fx.MESH).find('data/datum').set('value',
        f"SPRW_Greatsword <{tx.NATIVE_SWORD['guid']}>" if variant=='spiritual' else f"WPN_HUM_Longsword_A_0 <{tx.LONGSWORD}>")
    spiritual=variant=='spiritual'
    low,high=(tx.NATIVE_SWORD['minimum'],tx.NATIVE_SWORD['maximum']) if spiritual else tx.STEEL_SWORD_BOUNDS
    widths=tuple(high[i]-low[i] for i in range(3))
    scale=tuple(SIZE[i]/widths[i] for i in range(3)) if spiritual else (SIZE[0]/widths[0],SIZE[2]/widths[1],SIZE[1]/widths[2])
    zero_low,zero_high=transformed_bounds(low,high,scale,spiritual)
    pivot=(-(zero_low[0]+zero_high[0])/2,-zero_low[1],-(zero_low[2]+zero_high[2])/2)
    tx._native_replace_constants(model,tx.fx.MODEL_SCALE,scale)
    tx._native_replace_constants(model,tx.MODEL_ROTATION,(180,0,0) if spiritual else (-90,0,0))
    tx._native_replace_constants(model,tx.MODEL_ROTATION_RPM,(0,0,0))
    tx._native_replace_constants(model,tx.MODEL_ROTATION_LIFE,(0,0,0))
    tx._native_prop(model,tx.fx.POSITION).find('data/datum').set('value',','.join(format(v,'.17g') for v in pivot))
    tx.fx.replace_ramp(dictionary,model,tx.MODEL_OFFSET,(
        [(0,0),(1,0)],[(0,HEIGHT),(.010/DURATION,HEIGHT),(.045/DURATION,HEIGHT*.55),(CONTACT/DURATION,0),(1,0)],[(0,0),(1,0)]))
    tx.fx.replace_ramp(dictionary,model,tx.MODEL_ALPHA,(
        [(0,0),(.005/DURATION,1),(.17/DURATION,1),(.38/DURATION,0),(1,0)],))
    tx.fx.bounds(dictionary,root,10,DURATION)
    for index,track in enumerate(root.findall('./trackgroups/trackgroup/track')):
        c=track.find('component')
        c.set('instancename',guid(f'vfx/taixuan/world-rain/component/{role}/{variant}/{index}'))
    footprint=transformed_bounds(low,high,scale,spiritual,pivot)
    return root,[origin,sword_origin],dict(role=role,variant=variant,world_ground_anchor=True,
        model_count=1,tip_bound_start_y=HEIGHT,tip_bound_contact_y=0,contact_seconds=CONTACT,
        duration_seconds=DURATION,world_footprint_at_contact=footprint,size_xyz=SIZE,
        model_scale=scale,pivot=pivot,bodyfx=False,produces_damage=False,
        actual_rendered_sword_visibility='pending; spiritual sphere mask needs renderer WorldExtents',
        orientation_basis='official Visual resource bounds; vertex-level blade-tip proof pending')

SOUND_ORIGIN='Editor/Mods/Shared/Assets/Effects/Projectiles/VFX_Projectiles_Force_MagicMissile_Impact_01.lsefx'
SOUND_INSTANCE='650d142e-20e4-45e6-a87b-67c1cb227888'
SOUND_ID='e11a1c71-5181-7a7d-5abc-4ed596ff09a3'
SOUND_ENTER='d9c8f8f4-03ef-4a81-afcc-9979213be536'

def author(data,role,variant,dictionary):
    root,origins,detail=_column(data,role,variant,dictionary)
    if role=='jiuxiao_background':
        detail.update(contact_particles=0,contact_sounds=0)
        from sword_glow import apply as apply_glow
        detail.update(apply_glow(root,dictionary,'taixuan'))
        return root,origins,detail
    # A ground contact glint is environmental, not a successful-hit signal.
    # Actual native HitEffect particles remain attached to their real hit result.
    impact,impact_origins,_=tx._impact(Path(data),'taixuan_taiqing_hit',tx.PROFILES['taixuan_taiqing_hit'],dictionary)
    track=copy.deepcopy(impact.find('./trackgroups/trackgroup[@name="One actual-stage impact core"]/track'))
    particle=track.find('component')
    tx.fx.timing(particle,CONTACT,CONTACT+.45)
    tx.fx.multiply(dictionary,particle,tx.fx.PARTICLE_SCALE,.50)
    dictionary.property(particle,tx.PARTICLE_OFFSET)
    tx.fx.set_value(particle,tx.PARTICLE_OFFSET,'0,0,0')
    particle.set('instancename',guid('vfx/taixuan/world-rain/ground-contact/'+role+'/'+variant))
    tx._group(root,'Environmental ground contact at sword arrival',1010).append(track)
    source=ET.parse(Path(data)/SOUND_ORIGIN).getroot()
    tracks=[t for t in source.findall('./trackgroups/trackgroup/track') if t.find('component').get('instancename')==SOUND_INSTANCE]
    if len(tracks)!=1:raise ValueError('Native MagicMissile impact sound donor changed')
    sound_track=copy.deepcopy(tracks[0]);sound=sound_track.find('component')
    if sound.get('class')!='Sound' or (float(sound.get('start')),float(sound.get('end')))!=(0,3.01):raise ValueError('Native sound timeline changed')
    if SOUND_ID not in sound.find(f'./properties/property[@id="{SOUND_ENTER}"]/data/datum').get('value',''):raise ValueError('Native non-healing Force impact sound changed')
    dictionary.property(sound,SOUND_ENTER)
    tx.fx.timing(sound,CONTACT,CONTACT+3.01)
    sound.set('instancename',guid('vfx/taixuan/world-rain/ground-sound/'+role+'/'+variant))
    tx._group(root,'Force contact sound at sword arrival',1011).append(sound_track)
    # Keep native Sound component lifetime intact. Only the invisible bounding
    # track extends past visual fade, preventing a guessed audio-tail cutoff.
    tx.fx.bounds(dictionary,root,10,CONTACT+3.01)
    detail.update(contact_particles=1,contact_sounds=1,contact_fx_start=CONTACT,
                  contact_sound_start=CONTACT,visual_model_end=DURATION,
                  native_sound_component_duration=3.01,total_resource_duration=CONTACT+3.01,
                  ground_glint_is_environmental=True,audio_and_rendered_alignment='pending native listening/capture')
    from sword_visible_blade import improve_world_rain
    blade_origins, blade_detail=improve_world_rain(Path(data),role,variant,root,dictionary)
    detail.update(blade_detail)
    from sword_glow import apply as apply_glow
    detail.update(apply_glow(root,dictionary,'taixuan'))
    return root,list(dict.fromkeys([*origins,*impact_origins,Path(data)/SOUND_ORIGIN,*blade_origins])),detail

def generate_resources(source):
    source=Path(source).resolve()
    if not (source/RECEIPT).is_file():return {'enabled':False,'records':{},'remaining':'native compilation receipt missing'}
    proof=json.loads((source/RECEIPT).read_text(encoding='utf-8'))
    variant=proof.get('variant')
    if proof.get('compiler')!='AllSpark.EffectCompiler.Compiler.Compile' or variant not in VARIANTS:
        raise ValueError('Taixuan world rain requires native compiler receipt and explicit sword variant')
    rows={row['effect_name']:row for row in proof['records']}
    if set(rows)!={effect_name(role,variant) for role in ROLES}:raise ValueError('Receipt must contain exactly three selected world banks')
    prepared={}
    for role in ROLES:
        editable,binary=paths(role,variant);row=rows[effect_name(role,variant)]
        if not row.get('semantic_roundtrip_verified') or row.get('binary_version')!=7:
            raise ValueError('Native world-rain semantic roundtrip not verified')
        for file,key in [(editable,'source_sha256'),(binary,'compiled_sha256')]:
            if not (source/file).is_file() or hashlib.sha256((source/file).read_bytes()).hexdigest()!=row[key].lower():
                raise ValueError('Stale native world-rain receipt')
        meta=_metadata(source/editable,'impact')
        if meta['looping']:raise ValueError('World rain must be one-shot')
        prepared[role]=(meta,row,binary)
    root,parent=_document('EffectBank');children=ET.SubElement(parent,'children');records={}
    for role,(meta,row,binary) in prepared.items():
        node=ET.SubElement(children,'node',id='Resource')
        for key,field in [('bounds_min','BoundsMin'),('bounds_max','BoundsMax'),('center','Center')]:
            _attribute(node,field,'fvec3',' '.join(f'{v:g}' for v in meta[key]))
        for field,typ,value in [('CullingDistance','float',0),('Duration','float',meta['duration']),
            ('EffectName','FixedString',effect_name(role,variant)),('ID','FixedString',effect_guid(role,variant)),
            ('Initialized','bool',True),('InterruptionMode','uint32',0),('Localized','bool',False),('Looping','bool',False),
            ('Name','LSString',effect_name(role,variant)),('Radius','float',meta['radius']),('SourceFile','LSString',binary.as_posix())]:
            _attribute(node,field,typ,value)
        deps=ET.SubElement(ET.SubElement(ET.SubElement(node,'children'),'node',id='Dependencies'),'children')
        for dependency in sorted(set(meta['dependencies'])|{NATIVE_MATERIALS[variant]}):
            _attribute(ET.SubElement(deps,'node',id='DependentResource'),'Object','FixedString',dependency)
        records[role]=dict(effect=effect_guid(role,variant),effectName=effect_name(role,variant),duration=meta['duration'],
            sourceSHA256=row['source_sha256'].lower(),compiledSHA256=row['compiled_sha256'].lower())
    _write_xml(source/BANK,root);_convert(source/BANK)
    return dict(enabled=True,records=records,variant=variant,visualAcceptance='pending',radiusReference=6)
