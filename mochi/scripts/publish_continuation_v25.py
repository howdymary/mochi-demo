"""Publish additive V25 paths using an alternate index, preserving active work."""
import argparse
import os
from pathlib import Path
import subprocess

p=argparse.ArgumentParser();p.add_argument('--message',required=True);p.add_argument('--push',action='store_true');args=p.parse_args()
root=Path(__file__).resolve().parents[2]
branch='mochi-continuation-v25'
base='4191dfc202fba3084eeed550d39b34d1dcb94f8b'
head_path=Path(subprocess.check_output(['git','rev-parse','--git-path','HEAD'],cwd=root,text=True).strip())
if not head_path.is_absolute():head_path=root/head_path
head=head_path.read_bytes();index=subprocess.check_output(['git','ls-files','-s'],cwd=root)
cache=root/'mochi/.cache/continuation-v25';cache.mkdir(parents=True,exist_ok=True)
env={**os.environ,'GIT_INDEX_FILE':str(cache/'delivery-index')}
def git(*arguments):return subprocess.check_output(['git',*arguments],cwd=root,env=env,text=True).strip()
try:parent=git('rev-parse','--verify','refs/heads/'+branch);old=parent
except subprocess.CalledProcessError:parent=base;old='0'*40
git('read-tree',parent)
paths=['mochi/README.md','mochi/src/mochi/navigation_v25','mochi/configs/continuation-v25',
    'mochi/web/desk/continuation-v25.html','mochi/web/desk/continuation-v25.js','mochi/web/desk/continuation-v25',
    'mochi/docs/continuation-v25-methods.md','mochi/tests/test_navigation_v25_checks.py','mochi/tests/test_navigation_v25_compact.py']
paths += [str(x.relative_to(root)) for x in (root/'mochi/scripts').glob('*v25*.py')]
paths += [str(x.relative_to(root)) for x in (root/'mochi/scripts').glob('*v25*.mjs')]
paths += [str(x.relative_to(root)) for x in (root/'mochi/scripts').glob('*v26*.py')]
if (root/'mochi/configs/laptop-contact-v26').exists():paths.append('mochi/configs/laptop-contact-v26')
if (root/'mochi/docs/continuation-v25-findings.md').exists():paths.append('mochi/docs/continuation-v25-findings.md')
if (root/'mochi/evidence/continuation-v25').exists():paths.append('mochi/evidence/continuation-v25')
paths += [str(x.relative_to(root)) for x in (root/'mochi/scripts').glob('*v27*.py')]
paths += [str(x.relative_to(root)) for x in (root/'mochi/scripts').glob('*v27*.mjs')]
paths += ['mochi/web/desk/showcase-v27.html','mochi/web/desk/showcase-v27-export.html',
    'mochi/web/desk/showcase-v27-export.js','mochi/web/desk/showcase-v27/manifest.json',
    'mochi/docs/showcase-v27.md','mochi/evidence/showcase-v27']
git('add','--',*paths)
changed=git('diff','--cached','--name-only',parent).splitlines()
assert changed
for name in changed:
    assert name.startswith('mochi/') and not any(x in name for x in ['private-','.pickle','.env','.json.gz']),name
    assert (root/name).stat().st_size<5_000_000,name
git('diff','--cached','--check',parent)
author=git('show','-s','--format=%an%n%ae',parent).splitlines()
for role in ['AUTHOR','COMMITTER']:env['GIT_'+role+'_NAME'],env['GIT_'+role+'_EMAIL']=author
commit=subprocess.check_output(['git','commit-tree',git('write-tree'),'-p',parent],cwd=root,env=env,text=True,input=args.message+'\n').strip()
git('update-ref','refs/heads/'+branch,commit,old)
assert head_path.read_bytes()==head
assert subprocess.check_output(['git','ls-files','-s'],cwd=root)==index
print(git('diff','--stat',parent,commit),flush=True)
print(commit,flush=True)
if args.push:print(git('push','origin',branch),flush=True)
