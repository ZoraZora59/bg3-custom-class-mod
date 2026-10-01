"""Prepare a versioned visual revision while preserving every prior image."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'art'/'static-v1'
p = argparse.ArgumentParser()
p.add_argument('--id',required=True)
p.add_argument('--prompt-file',required=True)
a = p.parse_args()
manifest = OUT/'manifest.json'
data = json.loads(manifest.read_text('utf-8'))
r = next(r for r in data['assets'] if r['id']==a.id)
if r['status']!='complete':
    raise ValueError('Finish the current version before preparing a revision')
prior = {k:r[k] for k in ['master','prompt','source_generated_path','width','height','alpha_extrema']}
prior['basename'] = r.get('basename',r['id'])
history = r.setdefault('revision_history',[])
history.append(prior)
r['references'] = [r['master']]
r['basename'] = r['id']+'-v'+str(len(history)+1)
r['master'] = 'masters/'+r['kind']+'/'+r['basename']+'.png'
r['prompt'] = Path(a.prompt_file).read_text('utf-8').strip()
r['status'] = 'pending'
manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'prompts.jsonl').write_text(''.join(json.dumps({k:r[k] for k in ['id','name','kind','group','prompt','transparent']},ensure_ascii=False)+'\n' for r in data['assets']),encoding='utf-8')
print(json.dumps({'id':r['id'],'version':len(history)+1,'prior_preserved':prior['master']},ensure_ascii=True))
