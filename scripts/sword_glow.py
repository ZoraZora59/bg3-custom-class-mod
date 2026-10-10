"""Native luminous swords with owned materials and preserved flight transforms.

The original Spiritual Weapon mesh and precompiled shader work together in the
client. Disabling the shader's gold gradient makes the model's Color ramp usable.
References: https://docs.baldursgate3.game/Reusing_Base_Game_Shaders
H9 rendered cyan/red controls and H10 flat model ring are the visual references.
"""
from pathlib import Path
import copy
import math
import xml.etree.ElementTree as ET
from sword_cultivator_spec import FOLDER, guid

PALETTES = {'common': (10,140,255), 'taixuan': (10,140,255),
            'tianqing': (255,183,35), 'xueyan': (255,5,10), 'xingge': (45,255,150)}
SWORD = '3727a57a-e4be-44da-02b4-5061028fed5f'
CIRCLE = 'fd5982fe-30fd-6f3a-f531-ea7a68f86c34'
EXTERIOR = '27169e30-e769-5199-2378-1cb3f2ad4f38'
RING = '36c6fe7b-25b9-19fe-a285-d750d070b6ff'
TEMPLATES = Path(__file__).parent/'resources/native-sword-glow.lsx'


def visual_id(style, shape='sword'):
    return guid(f'vfx/glow/visual/{style}/{shape}')


def material_id(style, shape='sword'):
    # Keep existing sword IDs stable. Ground boundaries need substantially
    # softer opacity than a visible blade, so they own a separate material.
    suffix = '/circle' if shape == 'circle' else ''
    return guid(f'vfx/glow/material/{style}{suffix}')


def dependencies():
    return {visual_id(s, shape): (material_id(s, shape),)
            for s in PALETTES for shape in ('sword', 'circle')}


def generate_resources(source):
    from sword_vfx_resources import _document, _write_xml, _convert
    template = ET.parse(TEMPLATES)
    banks = {}
    for kind in ('Material', 'Visual'):
        root, parent = _document(kind+'Bank')
        banks[kind] = root, ET.SubElement(parent, 'children')
    def attr(n,k,v):
        n.find(f'./attribute[@id="{k}"]').set('value',str(v))
    for style, rgb in PALETTES.items():
        for shape, key in (('sword','Sword'),('circle','Circle')):
            mat = copy.deepcopy(template.find('Material/node'))
            attr(mat,'ID',material_id(style,shape));attr(mat,'Name',f'ESC_Glow_{style}_{shape}')
            values={'_Use_GradientMap':0,'Color':' '.join(str(v/255) for v in (*rgb,255)),
                    'EmissiveMult':1.2 if shape=='circle' else 3}
            if shape=='circle': values['OpacityMult']=.25
            for n in mat.findall('./children/node'):
                p=n.find('./attribute[@id="ParameterName"]')
                if p is not None and p.get('value') in values:
                    attr(n,'Enabled','True');attr(n,'Value',values[p.get('value')])
            banks['Material'][1].append(mat)
            visual=copy.deepcopy(template.find(key+'/node'))
            attr(visual,'ID',visual_id(style,shape));attr(visual,'Name',f'ESC_Glow_{style}_{shape}')
            for obj in visual.findall('./children/node[@id="Objects"]'):attr(obj,'MaterialID',material_id(style,shape))
            banks['Visual'][1].append(visual)
    paths=[]
    for kind,(root,_) in banks.items():
        folder='Materials' if kind=='Material' else 'Models'
        p=Path(source)/f'Public/{FOLDER}/Content/Assets/Effects/{folder}/[PAK]_ESC_SwordGlow/_merged.lsx'
        _write_xml(p,root);paths.extend((p,_convert(p)))
    return paths


def _rotation(angles):
    x,y,z=map(math.radians,angles);sx,cx=math.sin(x),math.cos(x);sy,cy=math.sin(y),math.cos(y);sz,cz=math.sin(z),math.cos(z)
    return ((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),
            (sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))


def _mul(a,b):
    return tuple(tuple(sum(a[i][k]*b[k][j]for k in range(3))for j in range(3))for i in range(3))


def _euler(m):
    y=math.asin(max(-1,min(1,-m[2][0])))
    if abs(math.cos(y))>1e-7:x,z=math.atan2(m[2][1],m[2][2]),math.atan2(m[1][0],m[0][0])
    else:x,z=math.atan2(-m[1][2],m[1][1]),0
    return tuple(math.degrees(v)for v in (x,y,z))


def apply(root, dictionary, style):
    """Change only sword appearance; keep world paths, phases, timing and audio."""
    import taixuan_visual_polish as tx
    from tianqing_vfx_design import GREAT_SWORD
    fx=tx.fx
    rgb=PALETTES[style];color=(0xff000000|rgb[0]<<16|rgb[1]<<8|rgb[2])-0x100000000
    native_min,native_max=tx.NATIVE_SWORD['minimum'],tx.NATIVE_SWORD['maximum']
    native_size=tuple(b-a for a,b in zip(native_min,native_max))
    native_center=tuple((a+b)/2 for a,b in zip(native_min,native_max))
    changed=0
    def constant(c,key,values):
        fx.replace_ramp(dictionary,c,key,tuple([(0,v),(1,v)]for v in values))
    for group in list(root.find('trackgroups')):
        for track in list(group.findall('track')):
            c=track.find('component')
            if c is None or c.get('class')!='Model':continue
            mesh=c.find(f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value','')
            if EXTERIOR in mesh:
                # The native beam shader rendered foil-like flashes instead of
                # a blade outline. The complete luminous sword replaces it.
                group.remove(track);continue
            base=None
            if tx.LONGSWORD in mesh:base=tx.STEEL_SWORD_BOUNDS
            elif GREAT_SWORD['guid'] in mesh:base=(GREAT_SWORD['bounds_min'],GREAT_SWORD['bounds_max'])
            elif SWORD not in mesh:continue
            if base:
                old_scale=tx._native_constant_values(c,fx.MODEL_SCALE)
                old_angles=tx._native_constant_values(c,tx.MODEL_ROTATION)
                r=_rotation(old_angles)
                sizes=tuple((b-a)*s for a,b,s in zip(*base,old_scale))
                scales=(sizes[0]/native_size[0],sizes[2]/native_size[1],sizes[1]/native_size[2])
                # Native +Y points to the tip; steel points toward -Z.
                pre=_rotation((-90,0,0));mapped=_mul(r,pre)
                old_center=tuple((a+b)/2*s for a,b,s in zip(*base,old_scale))
                new_center=tuple(native_center[i]*scales[i]for i in range(3))
                delta=tuple(sum(r[i][k]*old_center[k]-mapped[i][k]*new_center[k]for k in range(3))for i in range(3))
                dictionary.property(c,fx.POSITION)
                p=c.find(f'./properties/property[@id="{fx.POSITION}"]/data/datum')
                position=tuple(map(float,p.get('value').split(',')))
                p.set('value',','.join(format(position[i]+delta[i],'.12g')for i in range(3)))
                constant(c,fx.MODEL_SCALE,scales);constant(c,tx.MODEL_ROTATION,_euler(mapped))
            fx.set_value(c,fx.MESH,f'ESC_Glow_{style}_sword <{visual_id(style)}>')
            constant(c,fx.MODEL_COLOR,(color,));constant(c,tx.MODEL_BRIGHTNESS,(2.5,));changed+=1
        if not group.findall('track'):root.find('trackgroups').remove(group)
    # The old cylinder plus particle perimeter produced upright arches. Use the
    # H10-visible XY annulus rotated into the horizontal XZ plane instead.
    for c in root.findall('./trackgroups/trackgroup/track/component[@class="Model"]'):
        mesh=c.find(f'./properties/property[@id="{fx.MESH}"]/data/datum').get('value','')
        label=c.find(f'./properties/property[@id="{fx.NAME}"]/data/datum').get('value','')
        if RING in mesh and ('domain perimeter' in label.lower() or '太清' in label):
            fx.set_value(c,fx.MESH,f'ESC_Glow_{style}_circle <{visual_id(style,"circle")}>')
            constant(c,fx.MODEL_SCALE,(6,6,1));constant(c,tx.MODEL_ROTATION,(90,0,0))
            fx.set_value(c,fx.POSITION,'0,0.4,0');constant(c,fx.MODEL_COLOR,(color,));constant(c,tx.MODEL_BRIGHTNESS,(1.2,))
    for group in list(root.find('trackgroups')):
        if group.get('name')=='Taiqing native particle domain perimeter':root.find('trackgroups').remove(group)
    return dict(luminous_swords=changed,palette=rgb,visual_acceptance='pending rendered skill acceptance')
