"""Visible steel blades with the complete native TrueStrike emissive model.

Only visual composition changes. Damage, dispatch, audio and phase lifetimes
remain owned by the existing factories. Native rendered acceptance is separate.
"""
import copy
import xml.etree.ElementTree as ET
from sword_cultivator_spec import guid

CYAN = (0xff000000 | 170 << 16 | 230 << 8 | 255) - 0x100000000
EXTERIOR = '27169e30-e769-5199-2378-1cb3f2ad4f38'


class Blades:
    def __init__(self, data, dictionary):
        import taixuan_visual_polish as tx
        self.tx, self.fx, self.dictionary = tx, tx.fx, dictionary
        steel, steel_origin = self.fx.projectile(data)
        guard, guard_origins, _ = self.fx.guard_status(data, dictionary, emissive_cores=True)
        self.steel = self.select(steel, tx.LONGSWORD)
        self.core = self.select(guard, EXTERIOR)
        # The compiled moving-blade donor already has scale activated by the
        # flight factory. Activate it before adding the same rotation modules.
        dictionary.property(self.steel.find('component'), self.fx.MODEL_SCALE)
        self.origins = [steel_origin, *guard_origins]

    def mesh(self, component):
        return component.find(f'./properties/property[@id="{self.fx.MESH}"]/data/datum').get('value')

    def select(self, root, mesh_id):
        return copy.deepcopy(next(t for t in root.findall('./trackgroups/trackgroup/track')
            if t.find('component').get('class') == 'Model' and mesh_id in self.mesh(t.find('component'))))

    def ramp(self, component, key, channels):
        self.fx.replace_ramp(self.dictionary, component, key, channels)

    def constant(self, component, key, values):
        self.ramp(component, key, tuple([(0,v),(1,v)] for v in values))

    def position(self, component, value):
        self.dictionary.property(component, self.fx.POSITION)
        self.fx.set_value(component, self.fx.POSITION, ','.join(format(v,'.12g') for v in value))

    def append(self, root, template, label, duration):
        groups=root.find('trackgroups')
        ids=[int(n.get('value')) for n in groups.findall('./trackgroup/ids/id')]
        group=ET.SubElement(groups,'trackgroup',name=label)
        ET.SubElement(ET.SubElement(group,'ids'),'id',value=str(max(ids)+1))
        track=copy.deepcopy(template)
        track.set('name',label);track.set('muted','False');track.set('mutestateoverride','Unmuted')
        component=track.find('component')
        component.set('instancename',guid('vfx/candidate/H1/visible-sword/'+label))
        self.fx.set_value(component,self.fx.NAME,label)
        self.fx.timing(component,0,duration)
        self.constant(component,self.tx.MODEL_ROTATION_RPM,(0,0,0))
        self.constant(component,self.tx.MODEL_ROTATION_LIFE,(0,0,0))
        self.constant(component,self.fx.MODEL_COLOR,(CYAN,))
        group.append(track)
        return component

    def copy_curve(self, source, target, key):
        self.dictionary.property(target,key)
        old=target.find(f'./properties/property[@id="{key}"]')
        donor=source.find(f'./properties/property[@id="{key}"]')
        assert old is not None and donor is not None
        props=target.find('properties');index=list(props).index(old)
        props.remove(old);props.insert(index,copy.deepcopy(donor))

    def remove(self, root, components):
        for group in list(root.find('trackgroups')):
            for track in list(group.findall('track')):
                if track.find('component') in components:group.remove(track)
            if not group.findall('track'):root.find('trackgroups').remove(group)

    def pair(self, root, label, duration, width, depth, length, core_length, core_width):
        steel=self.append(root,self.steel,label+' steel sword',duration)
        core=self.append(root,self.core,label+' cyan blade core',duration)
        low,high=self.tx.STEEL_SWORD_BOUNDS
        self.constant(steel,self.fx.MODEL_SCALE,(width/(high[0]-low[0]),depth/(high[1]-low[1]),length/(high[2]-low[2])))
        # Put the emissive surface outside the opaque steel cross section.
        # A smaller tube entirely inside the blade was occluded in native H2.
        self.constant(core,self.fx.MODEL_SCALE,((width/2+.04)/.3824824,(depth/2+.04)/.3824274,core_length/10.000001))
        return steel,core

    def domain_perimeter(self, data, root):
        from pathlib import Path
        origin=Path(data)/self.fx.BASE/'Status/VFX_Status_Haste_01.lsefx'
        native=ET.parse(origin).getroot()
        donor,= [t for t in native.findall('./trackgroups/trackgroup/track')
                 if t.find('component').get('instancename')=='23907259-6b52-4bb4-976f-d85084aaa2cd']
        track=copy.deepcopy(donor);c=track.find('component')
        assert c.get('class')=='ParticleSystem' and self.tx.NATIVE_RING in ET.tostring(c,encoding='unicode')
        label='Taiqing native particle domain perimeter'
        track.set('name',label);track.set('muted','False');track.set('mutestateoverride','Unmuted')
        c.set('instancename',guid('vfx/visible-sword/domain-perimeter/native-particle'))
        self.fx.set_value(c,self.fx.NAME,label)
        ids=[int(n.get('value')) for n in root.findall('./trackgroups/trackgroup/ids/id')]
        group=ET.SubElement(root.find('trackgroups'),'trackgroup',name=label)
        ET.SubElement(ET.SubElement(group,'ids'),'id',value=str(max(ids)+1));group.append(track)
        def key(name):
            matches=[(k,p) for (kind,k),p in self.dictionary.properties.items() if kind=='ParticleSystem' and p.get('name')==name]
            assert len(matches)==1,name
            return matches[0]
        def scalar(name,value):
            k,_=key(name);self.dictionary.property(c,k);self.fx.set_value(c,k,value)
        emitter,definition=key('Type')
        choices=definition.find('definition/viewdata/datum').get('strings').split('|')
        self.dictionary.property(c,emitter);self.fx.set_value(c,emitter,choices.index('Point'))
        self.fx.timing(c,0,4.2)
        scalar('Initial Particle Count','1,1');scalar('Maximum Particle Count',1)
        scalar('Pivot Rotation','0,0,0')
        self.constant(c,self.fx.EMIT_RATE,(0,))
        self.constant(c,self.fx.LIFESPAN,(4.2,4.2))
        self.constant(c,self.fx.PARTICLE_SCALE,(1,1))
        self.constant(c,self.fx.PARTICLE_AXES,(6,.12,6))
        velocity,_=key('Initial Velocity');self.constant(c,velocity,(0,0))
        self.dictionary.property(c,self.tx.PARTICLE_OFFSET)
        self.fx.set_value(c,self.tx.PARTICLE_OFFSET,'0,0.45,0')
        self.constant(c,self.fx.PARTICLE_COLOR,(CYAN,))
        # Native Haste selects Color, not the dormant Color Over Effect Life.
        self.constant(c,'7b01f163-d329-4cd0-97f0-31115055b9c8',(2,))
        alpha,_=key('Alpha');self.ramp(c,alpha,([(0,0),(.2/4.2,.7),(3.8/4.2,.7),(1,0)],))
        return origin


def improve_projectile(data, style, root, dictionary):
    if style not in ('common','taixuan'):return [],{}
    b=Blades(data,dictionary);tx,fx=b.tx,b.fx
    steel=next(c for c in root.findall('./trackgroups/trackgroup/track/component')
        if c.get('class')=='Model' and tx.LONGSWORD in b.mesh(c))
    low,high=tx.STEEL_SWORD_BOUNDS;scale=tx._native_constant_values(steel,fx.MODEL_SCALE)
    length=.82*(high[2]-low[2])*scale[2]
    core=b.append(root,b.core,style.title()+' moving cyan blade core',1.2)
    width=(high[0]-low[0])*scale[0]/2+.04
    depth=(high[1]-low[1])*scale[1]/2+.04
    b.constant(core,fx.MODEL_SCALE,(width/.3824824,depth/.3824274,length/10.000001))
    for key in (tx.MODEL_OFFSET,tx.MODEL_ROTATION,tx.MODEL_ROTATION_RPM,tx.MODEL_ROTATION_LIFE,tx.MODEL_ALPHA):
        b.copy_curve(steel,core,key)
    b.position(core,(0,0,(high[2]+low[2])*scale[2]/2+length/2))
    wake=next(c for c in root.findall('./trackgroups/trackgroup/track/component')
        if 'Native luminous flight afterglow' in c.find(f'./properties/property[@id="{fx.NAME}"]/data/datum').get('value',''))
    b.constant(wake,fx.LIFESPAN,(.50,.50))
    ribbon=next(c for c in root.findall('./trackgroups/trackgroup/track/component') if c.get('class')=='Ribbon 2.0')
    key='edfa1f19-e70e-453a-a5af-310875d04854'
    dictionary.property(ribbon,key);fx.set_value(ribbon,key,.50)
    return b.origins,dict(blue_blade_core_length=length,blue_blade_core_diameter=width*2)


def improve_polish(data, key, root, dictionary):
    if key not in ('taixuan_liuguang_hit','taixuan_taiqing_status'):return [],{}
    b=Blades(data,dictionary);tx,fx=b.tx,b.fx
    if key=='taixuan_liuguang_hit':
        steel,core=b.pair(root,'Liuguang actual-stage',.75,.34,.14,2.4,1.9,.055)
        for c in (steel,core):
            b.constant(c,tx.MODEL_ROTATION,(0,-90,0));b.position(c,(-1.2,0,0))
            b.ramp(c,tx.MODEL_OFFSET,([(0,-2.8),(.04/.75,-2.8),(.18/.75,0),(1,0)],[(0,0),(1,0)],[(0,0),(1,0)]))
            b.ramp(c,tx.MODEL_ALPHA,([(0,0),(.025/.75,.80),(.22/.75,.90),(.42/.75,.45),(.65/.75,0),(1,0)],))
        fx.bounds(dictionary,root,8,1.0)
        detail=dict(local_short_thrust=True,actual_stage_steel_length=2.4)
    else:
        old=[c for c in root.findall('./trackgroups/trackgroup/track/component')
            if c.get('class')=='Model' and tx.NATIVE_SWORD['guid'] in b.mesh(c)]
        assert len(old)==6
        # Keep the original group allocation order of the compiled candidate.
        for index,previous in enumerate(old):
            for group in root.find('trackgroups'):
                for track in list(group.findall('track')):
                    if track.find('component') is previous:group.remove(track)
            steel,core=(
                b.append(root,b.steel,f'Taiqing orbit steel sword {index}',4.2),
                b.append(root,b.core,f'Taiqing orbit cyan blade core {index}',4.2))
            low,high=tx.STEEL_SWORD_BOUNDS
            b.constant(steel,fx.MODEL_SCALE,(.34/(high[0]-low[0]),.14/(high[1]-low[1]),1.9/(high[2]-low[2])))
            b.constant(core,fx.MODEL_SCALE,(.21/.3824824,.11/.3824274,1.5/10.000001))
            for c in (steel,core):
                b.constant(c,tx.MODEL_ROTATION,(90,0,0))
                b.position(c,(0,high[2]*1.9/(high[2]-low[2]) if c is steel else .18,0))
                b.copy_curve(previous,c,tx.MODEL_OFFSET)
                b.ramp(c,tx.MODEL_ALPHA,([(0,0),(.2/4.2,.7),(3.8/4.2,.7),(1,0)],))
        ring=next(c for c in root.findall('./trackgroups/trackgroup/track/component')
            if c.get('class')=='Model' and tx.NATIVE_RING in b.mesh(c))
        b.constant(ring,fx.MODEL_SCALE,(6,.12,6));b.position(ring,(0,.45,0))
        b.ramp(ring,tx.MODEL_ALPHA,([(0,0),(.2/4.2,.75),(3.8/4.2,.75),(1,0)],))
        b.constant(ring,tx.MODEL_BRIGHTNESS,(1.5,))
        b.origins.append(b.domain_perimeter(data,root))
        b.remove(root,[])
        detail=dict(orbit_steel_core_count=6,native_ring_scale=(6,.12,6),ring_height=.45,
            native_sword_visual=tx.LONGSWORD,original_sword_world_aabb_preserved=False,
            original_orbit_alpha_and_timing_preserved=False,orbit_and_status_timing_preserved=True,
            ring_y_range=(.33,.57),ring_alpha_hold=.75,native_particle_perimeter_count=1)
    return b.origins,detail


def improve_world_rain(data, role, variant, root, dictionary):
    if (role,variant)!=('taiqing','spiritual'):return [],{}
    b=Blades(data,dictionary);tx,fx=b.tx,b.fx
    old=next(c for c in root.findall('./trackgroups/trackgroup/track/component') if c.get('class')=='Model')
    b.remove(root,[old])
    steel=b.append(root,b.steel,'Taiqing fixed-world steel rain sword',.80)
    core=b.append(root,b.core,'Taiqing fixed-world cyan blade core',.80)
    low,high=tx.STEEL_SWORD_BOUNDS
    scale=(.42/(high[0]-low[0]),.17/(high[1]-low[1]),2.6/(high[2]-low[2]))
    b.constant(steel,fx.MODEL_SCALE,scale)
    b.constant(core,fx.MODEL_SCALE,(.25/.3824824,.125/.3824274,2.3/10.000001))
    for c in (steel,core):
        b.constant(c,tx.MODEL_ROTATION,(-90,0,0))
        pivot=(-(low[0]+high[0])*scale[0]/2,-low[2]*scale[2],(low[1]+high[1])*scale[1]/2)
        b.position(c,pivot if c is steel else (0,2.45,0))
        b.copy_curve(old,c,tx.MODEL_OFFSET)
        b.ramp(c,tx.MODEL_ALPHA,([(0,0),(.005/.8,1),(.28/.8,1),(.52/.8,.35),(.70/.8,0),(1,0)],))
    from taixuan_world_rain import transformed_bounds
    return b.origins,dict(model_count=2,visible_steel_length=2.6,blue_blade_core_length=2.3,
        model_scale=scale,pivot=pivot,size_xyz=(.42,2.6,.17),
        world_footprint_at_contact=transformed_bounds(low,high,scale,False,pivot),
        actual_rendered_sword_visibility='pending native rendered acceptance',variant_resource_name_preserved=True)
