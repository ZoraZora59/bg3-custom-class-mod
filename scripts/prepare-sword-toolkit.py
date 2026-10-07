"""Build editable Toolkit tables from formal LSX/stats; never installs into game Data."""
import argparse
import copy
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from sword_cultivator_spec import FOLDER, MOD, guid

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'mods'/MOD/'Source'


def save(path,root):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(root,space='  ')
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def schema(data,relative):
    refs=[]
    for module in ('Shared','SharedDev'):
        path=data/'Editor/Mods'/module/relative
        if path.exists(): refs.append(ET.parse(path).getroot())
    if not refs: raise ValueError(f'Missing installed Toolkit schema: {relative}')
    definitions={}
    names={}
    for ref in refs:
        for field in ref.iter('field'):
            definitions.setdefault(field.get('name'),dict(field.attrib))
        for obj in ref.findall('./stat_objects/stat_object'):
            fields={f.get('name'):f.get('value') for f in obj.findall('./fields/field')}
            if fields.get('Name') and fields.get('UUID'): names[fields['Name']]=fields['UUID']
    return refs[0].get('stat_object_definition_id'),definitions,names


def fields_for(obj,definitions,values):
    fields=ET.SubElement(obj,'fields')
    for key,value in values.items():
        if key not in definitions: raise ValueError(f'Unknown Toolkit field {key}')
        attrs={k:v for k,v in definitions[key].items() if k not in ('value','handle','version')}
        if isinstance(value,dict): attrs.update(value)
        else: attrs['value']=str(value)
        if attrs.get('value')=='': attrs['clear_inherited_value']='true'
        ET.SubElement(fields,'field',**attrs)
    return fields


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data'))
    args=p.parse_args()
    report=[]
    for rel in ('ClassDescriptions/ClassDescriptions','Progressions/Progressions','Progressions/ProgressionDescriptions','Lists/SkillLists','Lists/AbilityLists','Lists/SpellLists','ActionResourceDefinitions/ActionResourceDefinitions','CharacterCreationPresets/AbilityDistributionPresets','DefaultValues/Skills','ErrorDescriptions/ConditionErrors','Levelmaps/LevelMapValues'):
        definition,defs,_=schema(args.data,rel+'.tbl')
        root=ET.Element('stats',stat_object_definition_id=definition)
        rows=ET.SubElement(root,'stat_objects')
        for i,obj in enumerate(ET.parse(SOURCE/'Public'/FOLDER/(rel+'.lsx')).getroot().findall('./region/node/children/node')):
            values={'Name':f'ESC_{rel.split("/")[-1]}_{i}'}
            for a in obj.findall('attribute'):
                key=a.get('id')
                if rel.startswith('ClassDescriptions'): key={'Name':'NameFS','ParentGuid':'ParentUUID'}.get(key,key)
                elif rel.startswith('ActionResourceDefinitions'): key='NameFS' if key=='Name' else key
                elif rel.startswith('DefaultValues'): key={'Add':'DefaultValues','TableUUID':'ProgressionUUID'}.get(key,key)
                elif rel.startswith('Levelmaps/'):
                    key='PreferredClass' if key=='PreferredClassUUID' else key
                elif rel.startswith('Lists/') and key=='Name':
                    expected=values['Name']
                    if a.get('value')!=expected:
                        raise ValueError(f'{rel} row {i} Name mismatch: {a.get("value")!r} != {expected!r}')
                else: key='FSName' if key=='Name' else key
                value={k:v for k,v in a.attrib.items() if k in ('value','handle','version')}
                if a.get('type')=='bool': value['value']=value['value'].title()
                values[key]=value
            subclasses=[a.get('value') for a in obj.findall('./children/node[@id="SubClasses"]/children/node/attribute[@id="Object"]')]
            if subclasses: values['SubClasses']=';'.join(subclasses)
            fields_for(ET.SubElement(rows,'stat_object',is_substat='false'),defs,values)
        save(SOURCE/'Editor/Mods'/FOLDER/(rel+'.tbl'),root)
        report.append({'file':rel+'.tbl','rows':len(rows)})
    statdir=SOURCE/'Public'/FOLDER/'Stats/Generated/Data'
    for txt in sorted(statdir.glob('*.txt')):
        if txt.stem.startswith('Spell_'):
            kind=txt.stem.removeprefix('Spell_'); relative=f'Stats/SpellData/{kind}.stats'; prefix=kind+'_'
        elif txt.stem=='Interrupt': relative='Stats/Stats/Interrupt.stats';prefix=''
        elif txt.stem=='Passive': relative='Stats/Stats/Passive.stats';prefix=''
        elif txt.stem.startswith('Status_'): relative='Stats/StatusData/'+txt.stem+'.stats';prefix=''
        else: raise ValueError(txt)
        definition,defs,names=schema(args.data,relative)
        if relative.startswith('Stats/SpellData/'):
            for other in ('Target','Projectile','Shout','Zone','Rush','Teleportation','Throw','ProjectileStrike','Wall'):
                try:
                    _,extra,_=schema(args.data,f'Stats/SpellData/{other}.stats')
                except ValueError: continue
                for k,v in extra.items(): defs.setdefault(k,v)
        root=ET.Element('stats',stat_object_definition_id=definition)
        rows=ET.SubElement(root,'stat_objects')
        blocks=re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)',txt.read_text(encoding='utf-8'),re.S)
        local_names={name:guid('editor-stat/'+name) for name,_ in blocks}
        for name,body in blocks:
            values={'UUID':local_names[name],'Name':name.removeprefix(prefix)}
            inherited=re.search(r'^using "([^"]+)"$',body,re.M)
            if inherited:
                base=inherited.group(1); basekey=base.removeprefix(prefix)
                values['Using']=local_names.get(base) or names.get(basekey) or names.get(base)
                if not values['Using']: raise ValueError(f'Unknown base {base} in {relative}')
            for key,value in re.findall(r'^data "([^"]+)" "([^"]*)"$',body,re.M):
                key={'WeaponTypes':'WeaponType','SpellAnimation':'SpellAnimation'}.get(key,key)
                if key in ('SpellType','StatusType'): continue # native .stats table definition fixes the spell type
                field=defs.get(key)
                if not field: raise ValueError(f'Unknown Toolkit stats field {txt.name}:{key}')
                if field.get('type')=='TranslatedStringTableFieldDefinition':
                    if not value:
                        values[key]={'clear_inherited_value':'true'}
                    else:
                        handle,version=value.rsplit(';',1);values[key]={'handle':handle,'version':version}
                else: values[key]=value
            fields_for(ET.SubElement(rows,'stat_object',is_substat='false'),defs,values)
        save(SOURCE/'Editor/Mods'/FOLDER/relative,root)
        report.append({'file':relative,'rows':len(rows)})
    definition,defs,_=schema(args.data,'Stats/Equipment/Equipment.stats')
    root=ET.Element('stats',stat_object_definition_id=definition);rows=ET.SubElement(root,'stat_objects')
    body=(SOURCE/'Public'/FOLDER/'Stats/Generated/Equipment.txt').read_text(encoding='utf-8')
    values={'UUID':guid('editor-equipment'),'Name':'EQP_CC_ESC','InitialWeaponSet':'Melee'}
    for i,item in enumerate(re.findall(r'add equipment entry "([^"]+)"',body),1):values[str(i)]=item
    fields_for(ET.SubElement(rows,'stat_object',is_substat='false'),defs,values)
    save(SOURCE/'Editor/Mods'/FOLDER/'Stats/Equipment/Equipment.stats',root)
    report.append({'file':'Stats/Equipment/Equipment.stats','rows':1})
    (REPO/'mods'/MOD/'toolkit-source-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
