"""Verify the selected art set, record evidence, and produce a standalone ZIP."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote
import hashlib
import json
import zipfile
from PIL import Image
import manage_assets as manager

ROOT, OUT = manager.ROOT, manager.OUT
data = manager.load()
manager.build_gallery(data)
report = manager.validate()
report['selected_exports'] = sum(len(r['exports']) for r in data['assets'] if r['kind']!='illustration')
report['sources_match_snapshot'] = {}
for name, expected in data['sources_sha256'].items():
    actual = hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest()
    report['sources_match_snapshot'][name] = actual == expected
    if actual != expected:
        report['errors'].append('Source document changed: '+name)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        self.urls.extend(v for k,v in attrs if k in ('href','src') and v)

links = Links()
links.feed((OUT/'gallery.html').read_text('utf-8'))
for url in links.urls:
    if '://' in url or url.startswith('#'):
        continue
    if not (OUT/unquote(url)).is_file():
        report['errors'].append('Broken gallery link: '+url)
report['gallery_links_checked'] = len(links.urls)
pngs = list(OUT.rglob('*.png'))
for path in pngs:
    with Image.open(path) as im:
        im.verify()
report['png_files_verified'] = len(pngs)
report['game_validation'] = 'Not performed; PNG source assets only, no DDS or game bindings.'
(OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if report['errors']:
    raise ValueError(json.dumps(report,ensure_ascii=True))

target = ROOT/'art'/'bg3-sword-cultivator-static-v1.zip'
counter = 2
while target.exists():
    target = ROOT/'art'/('bg3-sword-cultivator-static-v1-'+str(counter)+'.zip')
    counter += 1
files = [p for p in OUT.rglob('*') if p.is_file()]
files += [p for p in (ROOT/'art'/'production').glob('*') if p.is_file()]
files += [ROOT/'docs'/name for name in data['sources_sha256']]
prefix = 'bg3-sword-cultivator-static-v1/'
with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
    for path in files:
        archive.write(path,prefix+path.relative_to(ROOT).as_posix())
    archive.writestr(prefix+'START-HERE.txt','Open art/static-v1/gallery.html in your browser.\nThe manifest identifies selected images. Prior revisions are preserved.\nPNG files are source art, not an installed or game-validated mod.\n')
with zipfile.ZipFile(target) as archive:
    if archive.testzip() is not None:
        raise ValueError('ZIP integrity check failed')
print(json.dumps({'assets':report['complete'],'selected_exports':report['selected_exports'],'pngs_verified':len(pngs),'zip':str(target),'zip_bytes':target.stat().st_size,'errors':report['errors']},ensure_ascii=True))
