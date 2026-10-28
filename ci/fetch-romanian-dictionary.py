from pathlib import Path
import sys,json,urllib.request,hashlib,time
meta = {'repository': 'https://github.com/LibreOffice/dictionaries', 'commit': '4f1df64b2e8e14751aa7c2205d170ca016071315', 'directory': 'ro', 'files': [{'name': 'COPYING.GPL', 'git_blob': 'f9c5fda5a3bf0bafbd4084452f1bbea510e4307e', 'sha256': '2233a3eecf299bc271f1a9f57f0b3198343ad4ab16571d70320133002c51496b', 'bytes': 18325}, {'name': 'COPYING.LGPL', 'git_blob': 'c4792dd27a32d2ce510ec3e6ea008d87a7bdbe9a', 'sha256': '5bbcbb737e60fe9deba08ecbd00920cfcc3403ba2e534c64fdeea49d6bb87509', 'bytes': 26532}, {'name': 'COPYING.MPL', 'git_blob': '7714141d154290f53e9e60c615a8edc9b51a8df7', 'sha256': '53692a2ed6c6a2c6ec9b32dd0b820dfae91e0a1fcdf625ca9ed0bdf8705fcc4f', 'bytes': 25755}, {'name': 'README_EN.txt', 'git_blob': '57aea88c095e83ced12cfd68e058ecc067b4cee3', 'sha256': '854c3b7e6575da37d066d5a09945af336a8ecc62c5e3c1049e97504dc67cbd81', 'bytes': 1633}, {'name': 'ro_RO.aff', 'git_blob': '757892ee0d74c778cedebfdd2a07ef135ddd3e7b', 'sha256': '0c83a02f0ac5202c068e60e1aef5ce99e13d7f6c92ae8e68ca8b9e06829edfd1', 'bytes': 55195}, {'name': 'ro_RO.dic', 'git_blob': '1a843e14aaa3458b6550a06567d648749903293c', 'sha256': 'c26a9356f598a0ae89e7be650f6bdd9ba70acce66b41d7ab14c0c68639b6ed33', 'bytes': 2202394}], 'included_in_git': False}
r=Path(sys.argv[1]).resolve();r.mkdir(exist_ok=True);d=r/'dictionaries';d.mkdir()
for f in meta['files']:
 url=f"https://raw.githubusercontent.com/LibreOffice/dictionaries/{meta['commit']}/ro/{f['name']}"
 for attempt in range(3):
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'WordCraft-Romanian-proofing-verification'})
   with urllib.request.urlopen(request,timeout=40) as response:data=response.read()
   assert hashlib.sha256(data).hexdigest()==f['sha256'],f['name']
   break
  except Exception:
   if attempt==2:raise
   time.sleep(2)
 with (d/f['name']).open('xb') as out:out.write(data)
(d/'provenance.json').open('x',encoding='utf-8').write(json.dumps(meta,indent=2))
print('Pinned external Rospell data and licence files verified; no dictionary data in source.')
