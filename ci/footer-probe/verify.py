"""Portable synthetic DOCX footer probe; exclusive outputs, no real files, no servers."""
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
import json,hashlib,subprocess,os,sys,zipfile,xml.etree.ElementTree as E,platform,importlib.metadata
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def signature(p):
 result=[]
 with zipfile.ZipFile(p) as z:
  for name in z.namelist():
   if not(name.startswith(('word/header','word/footer')) and name.endswith('.xml')):continue
   part=E.fromstring(z.read(name));tables=[]
   for t in part.iter(W+'tbl'):
    pr=t.find(W+'tblPr');width=pr.find(W+'tblW') if pr is not None else None;pos=pr.find(W+'tblpPr') if pr is not None else None;rows=[]
    for row in t.findall(W+'tr'):
     cells=[]
     for cell in row.findall(W+'tc'):
      span=cell.find(W+'tcPr/'+W+'gridSpan');merge=cell.find(W+'tcPr/'+W+'vMerge')
      cells.append({'text':''.join(e.text or '' for e in cell.iter(W+'t')),'span':int(span.get(W+'val','1')) if span is not None else 1,'vmerge':None if merge is None else merge.get(W+'val','continue')})
     rows.append(cells)
    tables.append({'width':None if width is None else [width.get(W+'type'),width.get(W+'w')],'position':None if pos is None else {k:pos.get(W+k) for k in ['vertAnchor','horzAnchor','tblpX','tblpY']},'rows':rows})
   result.append({'kind':'header' if name.startswith('word/header') else 'footer','tables':tables})
 return sorted(result,key=lambda x:json.dumps(x,sort_keys=True))

def run(binary,args,log,env):
    with log.open('x',encoding='utf-8') as f:
        p=subprocess.run([str(binary)]+list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,env=env,timeout=180)
    if p.returncode:raise RuntimeError(log.name+': '+log.read_text(encoding='utf-8')[-1500:])

def table_bounds(p):
    im=Image.open(p).convert('RGB');points=[]
    for i,(red,green,blue) in enumerate(im.getdata()):
        if red<100 and blue>red+20 and green>red+10:points.append((i%im.width,i//im.width))
    if not points:raise AssertionError('No synthetic table border in '+p.name)
    return [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]

def main():
    binary=Path(sys.argv[1]).resolve();binary=binary.with_suffix('.exe') if os.name=='nt' else binary;root=Path(sys.argv[2]).resolve();out=root/'results';out.mkdir()
    env=os.environ.copy();env['WORDCRAFT_REGION']='ro-RO';env['PYTHONUTF8']='1'
    for key in ['CACHE','CONFIG','DATA']:env['XDG_'+key+'_HOME']=str(root/('runtime-'+key.lower()))
    if os.name=='nt':
        env['APPDATA']=str(root/'runtime-appdata');env['LOCALAPPDATA']=str(root/'runtime-localappdata')
    manifest=json.loads((root/'synthetic-manifest-v2.json').read_text(encoding='utf-8'))+json.loads((root/'synthetic-extra-manifest.json').read_text(encoding='utf-8'))
    results=[]
    for case in manifest:
        name=case['name'];src=Path(case['input']);dest=out/(name+'.docx');pdf=out/(name+'.pdf');script=out/(name+'.json')
        if hashlib.sha256(src.read_bytes()).hexdigest()!=case['sha256']:raise AssertionError(name+' input changed')
        with script.open('x',encoding='utf-8') as f:
            json.dump({'file':str(src),'commands':[{'command':'caret.docEnd'},{'command':'text.insert','params':{'text':' EDITARE SINTETICA'}}],'save':[str(dest),str(pdf)]},f)
        run(binary,['run','--script',script],out/(name+'.log'),env)
        pages=PdfReader(pdf).pages;texts=[p.extract_text() or '' for p in pages]
        assert len(pages)==len(case['expected_per_page']),name
        assert all(all(marker in text for marker in markers) for text,markers in zip(texts,case['expected_per_page'])),name+' PDF markers'
        assert signature(src)==signature(dest),name+' table structure'
        images=[]
        for i in range(1,len(pages)+1):
            before=out/(name+f'-before-{i}.png');after=out/(name+f'-after-{i}.png')
            run(binary,['render',src,before,'--page',i,'--scale','1.333333'],out/(name+f'-before-{i}.log'),env)
            run(binary,['render',dest,after,'--page',i,'--scale','1.333333'],out/(name+f'-after-{i}.log'),env)
            images.append([before.name,after.name])
        geometry=None
        if name in ['02-inline-footer','09-vertical-merge-footer']:
            before=table_bounds(out/images[0][0]);after=table_bounds(out/images[0][1]);assert before==after,(name,before,after)
            geometry={'before':before,'after':after,'vertical_shift_pixels':after[1]-before[1]}
        assert hashlib.sha256(src.read_bytes()).hexdigest()==case['sha256']
        results.append({'case':name,'pages':len(pages),'markers_preserved':True,'table_structure_preserved':True,'source_unchanged':True,'geometry':geometry,'images':images})
    summary={'platform':platform.system(),'python':platform.python_version(),'pypdf':importlib.metadata.version('pypdf'),'Pillow':importlib.metadata.version('Pillow'),'scope':'Synthetic native CLI rendering and DOCX/PDF content checks; no native GUI or Microsoft Word reference acceptance','cases':results,'total_cases':len(results),'total_pdf_pages':sum(x['pages'] for x in results)}
    with (out/'summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
    print(json.dumps({'platform':summary['platform'],'cases':summary['total_cases'],'pages':summary['total_pdf_pages'],'status':'PASS'}),flush=True)

if __name__=='__main__':main()
