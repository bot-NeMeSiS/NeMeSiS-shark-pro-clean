"""Record the local candidate's exact source scope without staging anything."""
import ast
import hashlib
import json
import os
from pathlib import Path
import py_compile
import subprocess

from jinja2 import Environment

ROOT=Path(__file__).resolve().parents[1]
GIT=os.environ.get('NEMESIS_QA_GIT','git')
BASE='c4a81003de1b5ccdb3036831583e9c1eb65e4417'
OUT=ROOT/'data/local_dev'


def git(*args):
    return subprocess.check_output([GIT,'-C',str(ROOT),*args],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}).decode('utf-8').strip()


assert git('branch','--show-current')=='codex/sentinel-operaciones-local'
assert git('rev-parse','HEAD')==BASE
assert not git('diff','--cached','--name-only')
names=sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
design=set(git('diff','--name-only',BASE,'317ac8c37c3c74f39b736a207f55079c7d454856').splitlines())
sports=set(git('diff','--name-only',BASE,'ef759cb88d46463424342598a765a68a0a057a7a').splitlines())
manifest=[]; digest=hashlib.sha256()
for name in names:
    path=ROOT/name
    assert path.is_file(), name
    origin=[]
    if name in design: origin.append('R8_VERSIONED_317ac8c3')
    if name in sports: origin.append('PR14_EF759CB8')
    origin.append('LOCAL_INTEGRATION_REVIEW')
    content=path.read_bytes()
    kind='DOCUMENTATION' if name.startswith(('project_control/','reports/')) else 'TEST' if name.startswith('tests/') else 'TOOL' if name.startswith('tools/') else 'PRODUCT'
    manifest.append({'path':name,'scope':kind,'origin':origin,'sha256':hashlib.sha256(content).hexdigest(),'size':len(content)})
    if kind!='DOCUMENTATION': digest.update(name.encode()+b'\0'+content+b'\0')
    if path.suffix=='.py':
        ast.parse(content,filename=name)
        py_compile.compile(str(path),cfile=str(OUT/'bytecode'/ (hashlib.sha256(name.encode()).hexdigest()+'.pyc')),doraise=True)
jinja=Environment()
templates=list((ROOT/'templates').rglob('*.html'))
for path in templates: jinja.parse(path.read_text(encoding='utf-8-sig'))
protected=['engines/v935_launch_trust_engine.py','static/v937-product-client.js']
protected+=git('ls-files','static/img/app-icons/*','*SPORTS_DATA_LIVE_CERTIFICATION*').splitlines()
for name in protected:
    assert git('hash-object','--path='+name,name)==git('rev-parse','HEAD:'+name), name
result={'head':BASE,'branch':git('branch','--show-current'),'staged':0,'changed_files':len(manifest),
        'source_fingerprint':digest.hexdigest(),'jinja_templates':len(templates),'protected_unchanged':protected,'files':manifest,
        'scope_counts':{kind:sum(row['scope']==kind for row in manifest) for kind in ('PRODUCT','TEST','TOOL','DOCUMENTATION')},
        'publication':'NONE','environment':'LOCAL_ONLY'}
latest=OUT/'final-source-manifest.json'
if latest.exists():
    prior=latest.read_bytes()
    preserved=OUT/('preserved-source-manifest-'+hashlib.sha256(prior).hexdigest()[:16]+'.json')
    if not preserved.exists(): preserved.write_bytes(prior)
encoded=json.dumps(result,indent=2)
(OUT/('final-source-manifest-'+digest.hexdigest()[:16]+'.json')).write_text(encoded,encoding='utf-8')
latest.write_text(encoded,encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key not in {'files','protected_unchanged'}}))
