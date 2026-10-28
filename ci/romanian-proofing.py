from pathlib import Path
import os,json,subprocess,hashlib,unicodedata,zipfile,sys,xml.etree.ElementTree as ET
r=Path(sys.argv[1]).resolve();out=r/'native-probe';out.mkdir();cli=Path(sys.argv[2]).resolve();
if os.name=='nt' and cli.suffix.lower()!='.exe':cli=Path(str(cli)+'.exe')
env=os.environ.copy();env.update(WORDCRAFT_DICTIONARIES=str(r/'dictionaries'),TMPDIR=str(r/'tmp'),WORDCRAFT_REGION='ro-RO',WORDCRAFT_NO_PREFS='1')
def run(name,commands,source=None,saves=None):
 payload={'commands':commands}
 if source:payload['file']=str(source)
 if saves:payload['save']=[str(p) for p in saves];assert all(not p.exists() for p in saves)
 f=out/(name+'.json');f.open('x',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False))
 p=subprocess.run([str(cli),'run','--script',str(f),'--print'],env=env,capture_output=True,text=True,encoding="utf-8",timeout=120)
 (out/(name+'.stdout.txt')).open('x',encoding='utf-8').write(p.stdout);(out/(name+'.stderr.txt')).open('x',encoding='utf-8').write(p.stderr)
 assert p.returncode==0,(name,p.stderr)
 result=[]
 for line in p.stdout.splitlines():
  key,sep,value=line.partition(': ')
  if sep:result.append((key,json.loads(value)))
 return result
cmd=lambda c,p={}: {'command':c,'params':p}
def start(text):return [cmd('document.setText',{'text':text}),'select.all',cmd('format.font',{'name':'Inter'}),cmd('review.language',{'lang':'ro-RO','default':True})]
def issues(result):return [v for k,v in result if k=='review.issues'][-1]
correct=[
 'Cererea și întâmpinarea sunt depuse. Înscrisurile justifică suma solicitată.',
 'Reclamantul solicită judecarea cererii. Pârâtul contestă cuantumul creanței.',
 'Anexăm documentele și dovada comunicării. Anexăm copie CI pentru verificare.',
 'Suma totală este de 1.234,56 lei. Termenul este stabilit pentru mâine.',
 'Ştiinţa şi cunoaşterea sunt importante. Ţara are școli și biblioteci.',
 unicodedata.normalize('NFD','Înscrisul este atașat. Cererea este depusă.'),
 'Fata citește o carte. Fața și fata sunt cuvinte diferite.',
]
typoes=[('cerre','cerere'),('atasat','atașat'),('semnatura','semnătura'),('instanta','instanța'),('creanta','creanța'),('atasata','atașată'),('cîine','câine'),('mîine','mâine'),('scoala','școala'),('dictionar','dicționar'),('stiinta','știință'),('instiintare','înștiințare')]
records=[]
for i,text in enumerate(correct):
 found=issues(run(f'correct-{i:02}',start(text)+['review.issues']));records.append({'case':f'correct-{i:02}','text':text,'expected_issues':0,'issues':found,'passed':not found})
for i,(wrong,want) in enumerate(typoes):
 text=f'Textul de probă: {wrong}.';found=issues(run(f'typo-{i:02}',start(text)+['review.issues']))
 hit=next((x for x in found if x['kind']=='spelling' and x['text']==wrong),None)
 suggestions=hit['suggestions'] if hit else []
 records.append({'case':f'typo-{i:02}','wrong':wrong,'expected_suggestion':want,'suggestions':suggestions,'passed':want in suggestions,'first_is_expected':bool(suggestions) and suggestions[0]==want})
# Querying proofing must not change source text, even in decomposed Unicode or old cedilla text.
text='\n'.join(correct+['Ă Â Î Ș Ț — ă â î ș ț.'])
source=out/'synthetic-office-ro.docx';run('create-office',start(text),saves=[source]);before=hashlib.sha256(source.read_bytes()).hexdigest()
queried=out/'office-queried.docx';pdf=out/'office-queried.pdf';found=issues(run('query-and-export',['review.issues'],source,[queried,pdf]))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def data(path):
 with zipfile.ZipFile(path) as z:
  tree=ET.fromstring(z.read('word/document.xml'));styles=ET.fromstring(z.read('word/styles.xml'))
  t='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in tree.findall('.//w:body/w:p',ns))
  langs=[x.attrib for root in [tree,styles] for x in root.findall('.//w:lang',ns)]
 return t,langs
assert data(source)[0]==data(queried)[0]
assert any(a.get('{'+ns['w']+'}val')=='ro-RO' for a in data(queried)[1])
assert before==hashlib.sha256(source.read_bytes()).hexdigest()
# Apply the explicit suggestion, then check the saved/reopened document with the real dictionary.
bad=out/'synthetic-typo.docx';run('create-typo',start('Înscrisul este atasat.'),saves=[bad]);badsha=hashlib.sha256(bad.read_bytes()).hexdigest()
fixed=out/'typo-corrected.docx';fixedpdf=out/'typo-corrected.pdf'
res=run('apply-suggestion',['caret.docStart','review.spelling',cmd('review.applySuggestion',{'text':'atașat'}),'review.issues'],bad,[fixed,fixedpdf]);assert not issues(res)
assert data(fixed)[0]=='Înscrisul este atașat.'
assert not issues(run('reopen-corrected',['review.issues'],fixed))
assert badsha==hashlib.sha256(bad.read_bytes()).hexdigest()
result={'synthetic_only':True,'cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'dictionary_provenance':'../dictionaries/provenance.json','cases':records,'passed':sum(c['passed'] for c in records),'total':len(records),'office_input_sha256':before,'typo_input_sha256':badsha,'inputs_unchanged':True,'query_does_not_mutate_text':True,'docx_ro_tag_preserved':True,'apply_save_reopen_passed':True,'office_export_issues':found}
(out/'results.json').open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'passed':result['passed'],'total':result['total'],'failures':[c for c in records if not c['passed']],'first_suggestions':sum(c.get('first_is_expected',False) for c in records),'roundtrip':True},ensure_ascii=False,indent=2))

# Orthographic scope: all correct-text controls and unambiguous targets must pass.
# The fixed dictionary accepts instanta from instantă/A; document that contextual limitation.
known=[c for c in records if c.get('wrong')=='instanta']
assert len(known)==1 and not known[0]['suggestions'],known
assert all(c['passed'] for c in records if c.get('wrong')!='instanta'),records
