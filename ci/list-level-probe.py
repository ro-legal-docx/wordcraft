from pathlib import Path
import zipfile,json,subprocess,os,sys,hashlib,xml.etree.ElementTree as ET
from PIL import Image,ImageChops
from pypdf import PdfReader
R=Path(sys.argv[1]).resolve();R.mkdir();OUT=R/'results';OUT.mkdir()
CLI=Path(sys.argv[2]).resolve()
if os.name=='nt':CLI=CLI.with_suffix('.exe')
ENV=os.environ.copy();ENV.update(WORDCRAFT_REGION='ro-RO',XDG_CACHE_HOME=str(R/'word-cache'),XDG_CONFIG_HOME=str(R/'word-config'),XDG_DATA_HOME=str(R/'word-data'))
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';NS={'w':W}
TEXT='ITEM SINTETIC — ă â î ș ț Ă Â Î Ș Ț'

def make(path,initial,inherited,override=True,cancel=False,target=None):
    num=lambda level,num=1:f'<w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="{num}"/></w:numPr>'
    props='<w:pStyle w:val="SyntheticChild"/>' if inherited else ''
    props+=num(initial,0) if cancel else (num(target if target is not None else initial) if target is not None or not inherited else '')
    if override:props+='<w:ind w:left="2400" w:hanging="120"/>'
    styles=f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Inter" w:hAnsi="Inter"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:styleId="SyntheticBase"><w:name w:val="Synthetic base"/><w:pPr>{num(initial)}</w:pPr></w:style><w:style w:type="paragraph" w:styleId="SyntheticChild"><w:name w:val="Synthetic child"/><w:basedOn w:val="SyntheticBase"/></w:style></w:styles>'
    levels=''.join(f'<w:lvl w:ilvl="{n}"><w:start w:val="1"/><w:numFmt w:val="'+('upperLetter' if n==0 else 'lowerLetter')+f'"/><w:lvlText w:val="%{n+1}."/><w:pPr><w:ind w:left="{720*(n+1)}" w:hanging="240"/></w:pPr></w:lvl>' for n in range(9))
    parts={'[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>',
    '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    'word/_rels/document.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>',
    'word/document.xml':f'<w:document xmlns:w="{W}"><w:body><w:p><w:pPr>{props}</w:pPr><w:r><w:t>{TEXT}</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:bottom="1440" w:left="1440" w:right="1440"/></w:sectPr></w:body></w:document>',
    'word/styles.xml':styles,'word/numbering.xml':f'<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0">{levels}</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'}
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data.encode())

def call(args,log):
    with log.open('x') as f:p=subprocess.run([str(CLI),*map(str,args)],env=ENV,stdout=f,stderr=subprocess.STDOUT,timeout=120)
    assert p.returncode==0,(args,log.read_text()[-1800:])

cases=[('direct-level',0,False,'para.listLevel',{'level':1},1,False),('direct-indent',0,False,'para.indent',{},1,False),('direct-outdent',1,False,'para.outdent',{},0,False),('style-level',0,True,'para.listLevel',{'level':1},1,False),('style-indent',0,True,'para.indent',{},1,False),('style-outdent',1,True,'para.outdent',{},0,False),('style-min-boundary',0,True,'para.outdent',{},0,False),('style-max-boundary',8,True,'para.indent',{},8,False),('style-same-level',2,True,'para.listLevel',{'level':2},2,False),('style-numbering-cancelled',0,True,'para.listLevel',{'level':1},0,True)]
results=[]
for name,initial,inherited,command,params,expected,cancel in cases:
    d=OUT/name;d.mkdir();src=d/'input.docx';reference=d/'reference.docx';changed=expected!=initial and not cancel
    make(src,initial,inherited,cancel=cancel)
    make(reference,initial,inherited,override=not changed,cancel=cancel,target=expected if changed else None)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,reference]}
    script={'file':str(src),'commands':[{'command':'select.text','params':{'text':'ITEM SINTETIC'}},{'command':command,'params':params}],'save':[str(d/'saved.docx'),str(d/'edited.pdf')]}
    with (d/'run.json').open('x') as f:json.dump(script,f,ensure_ascii=False,indent=2)
    call(['run','--script',d/'run.json'],d/'run.log')
    call(['convert',reference,d/'reference.pdf'],d/'reference.log')
    call(['convert',d/'saved.docx',d/'reopened.pdf'],d/'reopened.log')
    traces={}
    for stem in ['reference','edited','reopened']:
        pdf=PdfReader(d/f'{stem}.pdf');assert len(pdf.pages)==1
        trace=[]
        def visitor(text,cm,tm,font,size):
            if text.strip():trace.append([text,[round(float(n),4) for n in cm],[round(float(n),4) for n in tm],round(float(size),4)])
        text=pdf.pages[0].extract_text(visitor_text=visitor)
        assert all(c in text for c in 'ăâîșțĂÂÎȘȚ') and 'ITEM SINTETIC' in text,(name,text)
        traces[stem]=trace
    for stem,docx in [('reference',reference),('reopened',d/'saved.docx')]:
        call(['render',docx,d/f'{stem}.png','--scale','1'],d/f'{stem}-render.log')
    ref=Image.open(d/'reference.png').convert('RGB');reopened=Image.open(d/'reopened.png').convert('RGB')
    matches={'edited':traces['edited']==traces['reference'],'reopened':traces['reopened']==traces['reference'] and ref.size==reopened.size and ImageChops.difference(ref,reopened).getbbox() is None}
    with zipfile.ZipFile(d/'saved.docx') as z:
        xml=ET.fromstring(z.read('word/document.xml'));p=xml.find('w:body/w:p',NS)
        ind=p.find('w:pPr/w:ind',NS)
        if changed:assert ind is None or all('{'+W+'}'+k not in ind.attrib for k in ['left','hanging','firstLine','leftChars','hangingChars','firstLineChars'])
    assert all(matches.values()),(name,matches)
    unchanged=all(hashlib.sha256((d/p).read_bytes()).hexdigest()==h for p,h in hashes.items());assert unchanged
    result={'case':name,'expected_level':expected,'edited_matches_reference':matches['edited'],'saved_reopened_matches_reference':matches['reopened'],'romanian_letters':10,'inputs_unchanged':unchanged}
    results.append(result);print(result,flush=True)
with (OUT/'results.json').open('x') as f:json.dump(results,f,indent=2)
