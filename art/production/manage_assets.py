"""Register native ImageGen outputs, export PNG sizes, and build a local gallery."""
from pathlib import Path
import argparse
import html
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art'/'static-v1'
MANIFEST=OUT/'manifest.json'

def load():return json.loads(MANIFEST.read_text('utf-8'))
def save(data):MANIFEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def square_export(im,size,margin=0):
    canvas=Image.new('RGBA',(size,size),(0,0,0,0))
    scaled=im.copy()
    scaled.thumbnail((size-2*margin,size-2*margin),Image.Resampling.LANCZOS)
    canvas.alpha_composite(scaled,((size-scaled.width)//2,(size-scaled.height)//2))
    return canvas

def register(asset_id, source):
    data=load()
    row=next(r for r in data['assets'] if r['id']==asset_id)
    source=Path(source)
    if not source.is_file() or source.stat().st_size==0:raise ValueError('Missing generated source')
    with Image.open(source) as original:
        original.load()
        im=original.convert('RGBA')
        alpha=im.getchannel('A').getextrema()
        if row['transparent'] and alpha[0]==255:raise ValueError('Generated asset has no transparent pixels')
        row.update(width=im.width,height=im.height,alpha_extrema=alpha)
        master=OUT/row['master']
        master.parent.mkdir(parents=True,exist_ok=True)
        if master.exists() and row['status']=='complete':raise ValueError('Refusing to replace completed master')
        shutil.copy2(source,master)
        if row['kind']=='badge':
            specs=[('class_300',300,12),('class_hotbar_64',64,3)]
        elif row['kind']=='illustration':specs=[]
        else:specs=[('hotbar_64',64,0),('controller_144',144,0),('tooltip_380',380,0)]
        for folder,size,margin in specs:
            dest=OUT/'exports'/folder/(row.get('basename',row['id'])+'.png')
            dest.parent.mkdir(parents=True,exist_ok=True)
            square_export(im,size,margin).save(dest)
        preview=OUT/'previews'/(row['id']+'.png')
        preview.parent.mkdir(parents=True,exist_ok=True)
        square_export(im,256,8 if row['kind']=='badge' else 0).save(preview)
    row['status']='complete'
    row['attempts']+=1
    row['source_generated_path']=str(source)
    save(data)
    build_gallery(data)
    return {'id':asset_id,'status':row['status'],'size':[row['width'],row['height']],'alpha':alpha,'master':str(master)}

def build_gallery(data=None):
    data=data or load()
    labels={'common':'共同','taixuan':'太玄','tianqing':'天倾','xueyan':'血魇','xingge':'行歌'}
    kinds={'badge':'徽记','skill':'技能','passive':'被动','status':'状态','resource':'资源','illustration':'插画'}
    cards=[]
    for r in data['assets']:
        title=html.escape(r['name']); rid=html.escape(r['id']); complete=r['status']=='complete'
        picture=(f'<a href="{r["master"]}" target="_blank"><img src="previews/{rid}.png" alt="{title}" loading="lazy"></a>' if complete else '<div class="pending">等待生成</div>')
        links=''
        if complete:
            basename=html.escape(r.get('basename',r['id']))
            links=f'<a href="{r["master"]}" download>母版</a> '+''.join(f'<a href="exports/{folder}/{basename}.png" download>{folder.split("_")[-1]}px</a> ' for folder in r['exports'] if folder!='illustration_master')
            links+=''.join(f'<a href="{html.escape(old["master"])}" target="_blank">旧稿{i+1}</a> ' for i,old in enumerate(r.get('revision_history',[])))
        cards.append(f'<article data-group="{r["group"]}" data-kind="{r["kind"]}" data-name="{title} {rid}"><div class="picture">{picture}</div><h3>{title}</h3><div class="meta">{labels[r["group"]]} · {kinds[r["kind"]]}</div><code>{rid}</code><div class="links">{links}</div><details><summary>提示词与设定</summary><p>{html.escape(r["subject"])}</p><pre>{html.escape(r["prompt"])}</pre></details></article>')
    done=sum(r['status']=='complete' for r in data['assets'])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>东方剑修 · 静态美术资产</title><style>
    *{box-sizing:border-box}body{margin:0;background:#111516;color:#eee8dc;font:15px "Segoe UI","Microsoft YaHei",sans-serif}header{padding:32px 5vw 20px;border-bottom:1px solid #435250}h1{margin:0 0 8px;font-size:30px;color:#d8b875}p{line-height:1.6;color:#bac9c6}.tools{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}input,select,button{padding:10px;background:#202c2b;border:1px solid #50635e;color:#eee;border-radius:5px}main{padding:24px 5vw;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:18px}article{border:1px solid #36413f;border-radius:8px;background:#192120;overflow:hidden;padding:12px}.picture{height:210px;display:flex;justify-content:center;align-items:center;background:#101817;border-radius:5px}.picture img{max-width:100%;max-height:100%;object-fit:contain}.light .picture{background:#e1e4dc}.pending{color:#70847b}h3{margin:12px 0 7px;font-size:19px}.meta{font-size:12px;color:#b6b5a1}code{display:block;font-size:10px;color:#9aa8a5;overflow-wrap:anywhere;margin-top:8px}.links{margin-top:12px;display:flex;gap:10px;flex-wrap:wrap}a{color:#c6dacc}details{margin-top:14px;color:#a6b6ad}summary{cursor:pointer;font-size:12px}pre{white-space:pre-wrap;font-size:11px;line-height:1.5}footer{padding:20px 5vw;color:#aeb8ae}[hidden]{display:none!important}
    </style><header><h1>东方剑修 · 一脉四途</h1><p>正式静态资产首版 · 主体符号与 BG3 手绘图标分开制作 · 点击图片查看母版</p><p>PROGRESS</p><div class="tools"><input id="query" placeholder="查找技能、名称或 ID"><select id="group"><option value="">全部分支</option><option value="common">共同</option><option value="taixuan">太玄</option><option value="tianqing">天倾</option><option value="xueyan">血魇</option><option value="xingge">行歌</option></select><select id="kind"><option value="">全部类别</option><option value="badge">徽记</option><option value="skill">技能</option><option value="passive">被动</option><option value="status">状态</option><option value="resource">资源</option><option value="illustration">插画</option></select><button id="bg">切换浅色底</button></div></header><main>CARDS</main><footer>图片为内置 ImageGen 原创生成首版。PNG 为制作与导入源图，DDS 转换、资源绑定和游戏内验证需在 Toolkit 中完成。技能用 64/144/380px；职业用300px，另附64px制作版本，实际hotbar尺寸仍以接入模板核对。状态与被动使用相同导出集便于接入，资源最终尺寸以实际UI定义为准。<br><a href="manifest.json">资产清单</a> · <a href="prompts.jsonl">全部提示词</a> · <a href="../../docs/20-eastern-sword-cultivator-gdd.md">职业总稿</a></footer><script>
    const query=document.getElementById('query'),group=document.getElementById('group'),kind=document.getElementById('kind');function filter(){document.querySelectorAll('article').forEach(a=>a.hidden=!(a.dataset.name.toLowerCase().includes(query.value.toLowerCase())&&(!group.value||a.dataset.group===group.value)&&(!kind.value||a.dataset.kind===kind.value)))}[query,group,kind].forEach(x=>x.addEventListener('input',filter));document.getElementById('bg').onclick=()=>document.body.classList.toggle('light');
    </script></html>'''
    page=page.replace('PROGRESS',f'已完成 {done} / {len(data["assets"])} 项独立资产').replace('CARDS','\n'.join(cards))
    (OUT/'gallery.html').write_text(page,encoding='utf-8')

def validate():
    data=load();errors=[]
    for r in data['assets']:
        if r['status']!='complete':errors.append(f'{r["id"]}: incomplete');continue
        path=OUT/r['master']
        if not path.is_file():errors.append(f'{r["id"]}: missing master');continue
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            if r['transparent']:
                if im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0:
                    errors.append(f'{r["id"]}: master transparency invalid')
        for folder in r['exports']:
            if folder=='illustration_master':continue
            size=int(folder.split('_')[-1]);p=OUT/'exports'/folder/(r.get('basename',r['id'])+'.png')
            if not p.is_file():errors.append(f'{r["id"]}: missing {folder}');continue
            with Image.open(p) as im:
                if im.size!=(size,size) or im.mode!='RGBA':errors.append(f'{r["id"]}: bad export {folder}')
                elif im.getchannel('A').getextrema()[0]!=0 or im.getchannel('A').getextrema()[1]<32:
                    errors.append(f'{r["id"]}: export transparency invalid {folder}')
    return {'complete':sum(r['status']=='complete' for r in data['assets']),'total':len(data['assets']),'errors':errors}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','gallery','validate']);p.add_argument('--id');p.add_argument('--source');a=p.parse_args()
    if a.action=='register':print(json.dumps(register(a.id,a.source),ensure_ascii=True))
    elif a.action=='gallery':build_gallery()
    else:print(json.dumps(validate(),ensure_ascii=True))
