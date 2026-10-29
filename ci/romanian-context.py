# coding: utf-8
from pathlib import Path
import json,os,subprocess,sys,hashlib,unicodedata,zipfile,xml.etree.ElementTree as ET
r=Path(sys.argv[1]).resolve();cli=Path(sys.argv[2]).resolve()
if os.name=='nt' and cli.suffix.lower()!='.exe':cli=Path(str(cli)+'.exe')
out=r/'native-context';out.mkdir();(r/'tmp').mkdir(exist_ok=True)
env=os.environ.copy();env.update(WORDCRAFT_DICTIONARIES=str(r/'dictionaries'),TMPDIR=str(r/'tmp'),WORDCRAFT_REGION='ro-RO',WORDCRAFT_NO_PREFS='1')
cmd=lambda name,params={}: {'command':name,'params':params}
def run(name,commands,source=None,saves=None):
 payload={'commands':commands}
 if source:payload['file']=str(source)
 if saves:
  assert all(not p.exists() for p in saves);payload['save']=[str(p) for p in saves]
 script=out/(name+'.json');script.open('x',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False))
 p=subprocess.run([str(cli),'run','--script',str(script),'--print','--author','ro-legal-docx'],capture_output=True,text=True,encoding='utf-8',env=env,cwd=r,timeout=120)
 (out/(name+'.stdout.txt')).open('x',encoding='utf-8').write(p.stdout);(out/(name+'.stderr.txt')).open('x',encoding='utf-8').write(p.stderr)
 assert p.returncode==0,(name,p.stderr)
 trace=[]
 for line in p.stdout.splitlines():
  key,sep,value=line.partition(': ')
  if sep:trace.append((key,json.loads(value)))
 return trace
def start(text):return [cmd('document.setText',{'text':text}),'select.all',cmd('format.font',{'name':'Inter'}),cmd('review.language',{'lang':'ro-RO','default':True})]
def issues(trace):return next(v for k,v in reversed(trace) if k=='review.issues')
def contextual(found):return [i for i in found if i['message'].startswith('Diacritice în context juridic:')]
positive=[
 ('Instanta de judecată a stabilit termenul.','Instanta','Instanța'),
 ('Instanta de apel a stabilit termenul.','Instanta','Instanța'),
 ('Ne adresăm instantei de recurs.','instantei','instanței'),
 ('Cererea se află pe rolul instantei.','instantei','instanței'),
 ('Ne prezentăm în fața instantei.','instantei','instanței'),
 ('Persoana are calitatea de parat.','parat','pârât'),
 ('Persoana figurează în calitate de parat.','parat','pârât'),
 ('Cererea se judecă în contradictoriu cu paratul.','paratul','pârâtul'),
 ('Reclamantul și paratul au fost citați.','paratul','pârâtul'),
 ('Paratul a depus întâmpinare.','Paratul','Pârâtul'),
 ('Se solicită citarea paratului.','paratului','pârâtului'),
 ('Se solicită obligarea paratului.','paratului','pârâtului'),
 ('INSTANTA DE JUDECATĂ.','INSTANTA','INSTANȚA'),
 ('instanta de judecată a stabilit termenul.','instanta','Instanța'),
 (unicodedata.normalize('NFD','Ne prezentăm în faţa instantei.'),'instantei','instanței'),
 ('Reclamantul şi paratul au fost citați.','paratul','pârâtul'),
 ('Cererea este pe\u00a0rolul\u00a0instantei.','instantei','instanței'),
]
negative=[
 'Portarul a parat lovitura.','Sportivul a parat atacul.','Atacul a fost parat.','A parat de fiecare dată.',
 'Textul de probă: instanta.','Textul de probă: parat.','Instanta se inițializează.',
 'Instanta de apelare a funcției este separată.',
 'Instanța de judecată a stabilit termenul.','Persoana are calitatea de pârât.',
 'Exemplu: instanta_de_judecată.','Exemplu_instanta de judecată.','Exemplu: instanta.de.judecată.',
 'Exemplu: https://example.invalid/instanta/de/judecată.',
 'Se folosește «instanta» de judecată ca exemplu.',
 'În exemplu, `instanta de judecată` este text literal.',
 'Textul menționează calitate de «parat».',
 'Instanta. De judecată se discută separat.','Instanta\nde judecată este pe două linii.',
 'Se discută despre calitate de. Parat este alt cuvânt.','INSTAnTA de judecată.',
]
records=[]
for n,(text,wrong,fixed) in enumerate(positive):
 found=issues(run(f'positive-{n:02}',start(text)+['review.issues']));ctx=contextual(found)
 assert len(ctx)==1 and ctx[0]['text']==wrong and ctx[0]['suggestions']==[fixed],(text,found)
 assert ctx[0]['kind']=='grammar' and ctx[0]['lang']=='ro'
 # The lowercase sentence start gets one combined suggestion, not two competing marks.
 if n==13:assert len(found)==1,found
 records.append({'text':text,'expected':fixed,'findings':ctx,'passed':True,'other_issue_count':len(found)-len(ctx)})
for n,text in enumerate(negative):
 found=issues(run(f'negative-{n:02}',start(text)+['review.issues']));ctx=contextual(found);assert not ctx,(text,ctx)
 records.append({'text':text,'expected_contextual_issues':0,'passed':True,'other_issue_count':len(found)})
# A real DOCX round trip: three intended corrections and a valid verb which must remain `parat`.
source_text='\n'.join([unicodedata.normalize('NFD','Înscrisul este atașat.'),'Instanta de judecată a stabilit termenul.','Persoana are calitatea de parat.','Paratul a depus întâmpinare.','Atacul a fost parat.','Suma totală este de 1.234,56 lei.','Ă Â Î Ș Ț — ă â î ș ț.'])
source=out/'synthetic-context-source.docx';styling=[cmd('select.text',{'text':'Instanta'}),cmd('format.bold',{'value':True}),cmd('select.text',{'text':'parat'}),cmd('format.italic',{'value':True})];run('create-source',start(source_text)+styling,saves=[source]);source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
queried=out/'context-queried.docx';before_pdf=out/'context-queried.pdf';initial=issues(run('query-and-export',['review.issues'],source,[queried,before_pdf]));assert len(initial)==3 and len(contextual(initial))==3,initial
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def docx(path):
 with zipfile.ZipFile(path) as z:
  document=ET.fromstring(z.read('word/document.xml'));styles=ET.fromstring(z.read('word/styles.xml'))
 text='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in document.findall('.//w:body/w:p',ns))
 langs=[x.attrib for root in [document,styles] for x in root.findall('.//w:lang',ns)]
 return text,langs
assert docx(source)[0]==source_text and docx(queried)[0]==source_text
commands=['caret.docStart','review.spelling',cmd('review.applySuggestion',{'text':'Instanța'}),'edit.undo','review.issues','edit.redo','review.issues','caret.docStart','review.spelling',cmd('review.applySuggestion',{'text':'pârât'}),'caret.docStart','review.spelling',cmd('review.applySuggestion',{'text':'Pârâtul'}),'review.issues']
fixed=out/'context-corrected.docx';pdf=out/'context-corrected.pdf';trace=run('apply-suggestions',commands,source,[fixed,pdf])
assert [v['text'] for k,v in trace if k=='review.spelling']==['Instanta','parat','Paratul'],trace
assert [len(v) for k,v in trace if k=='review.issues']==[3,2,0],trace
expected=source_text.replace('Instanta de judecată','Instanța de judecată',1).replace('de parat.','de pârât.',1).replace('Paratul','Pârâtul',1)
assert docx(fixed)[0]==expected
def direct_style(path, word, prop):
 with zipfile.ZipFile(path) as z:document=ET.fromstring(z.read('word/document.xml'))
 for run in document.findall('.//w:r',ns):
  text=''.join(t.text or '' for t in run.findall('.//w:t',ns))
  if word in text:
   value=run.find('w:rPr/w:'+prop,ns)
   if value is not None and value.get('{'+ns['w']+'}val','1') not in ('0','false','off'):return True
 return False
for path,first,second in [(source,'Instanta','parat'),(queried,'Instanta','parat'),(fixed,'Instanța','pârât')]:
 assert direct_style(path,first,'b') and direct_style(path,second,'i'),(path,first,second)
assert any(x.get('{'+ns['w']+'}val')=='ro-RO' for x in docx(fixed)[1])
assert not issues(run('reopen-corrected',['review.issues'],fixed))
assert source_sha==hashlib.sha256(source.read_bytes()).hexdigest()
# Ignore All is a per-process choice; it does not silently rewrite the original spelling.
ignored=run('ignore-context',start('Persoana are calitatea de parat.')+['review.issues',cmd('review.ignoreAll',{'word':'parat'}),'review.issues'])
assert [len(contextual(v)) for k,v in ignored if k=='review.issues']==[1,0]
result={'synthetic_only':True,'cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest(),'positive_passed':len(positive),'negative_passed':len(negative),'cases':records,'source_sha256':source_sha,'inputs_unchanged':True,'query_does_not_mutate_text':True,'typed_unicode_preserved':True,'docx_ro_tag_preserved':True,'apply_undo_redo_save_reopen_passed':True,'legitimate_parat_verb_preserved':True,'ignore_all_passed':True,'bold_and_italic_preserved':True,'dictionary_provenance':'../dictionaries/provenance.json'}
(out/'results.json').open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('cases','dictionary_provenance')},ensure_ascii=False))
