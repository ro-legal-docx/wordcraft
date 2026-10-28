from pathlib import Path
from xml.sax.saxutils import escape
import zipfile,json,hashlib,sys
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True);out=root/'synthetic-v2';out.mkdir()
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';P='http://schemas.openxmlformats.org/package/2006/relationships'
def para(t='',before=''):
 return '<w:p>'+before+'<w:r><w:rPr><w:rFonts w:ascii="Source Sans 3" w:hAnsi="Source Sans 3"/><w:sz w:val="20"/></w:rPr><w:t>'+escape(t)+'</w:t></w:r></w:p>'
def table(mark,position='',percent=False,merge=False):
 width='<w:tblW w:w="5000" w:type="pct"/>' if percent else '<w:tblW w:w="9000" w:type="dxa"/>'
 borders='<w:tblBorders>'+''.join(f'<w:{e} w:val="single" w:sz="8" w:color="224466"/>' for e in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
 props='<w:tblPr>'+width+borders+position+'</w:tblPr>'
 def cell(t,span=1):
  return '<w:tc><w:tcPr><w:tcW w:w="'+str(4500*span)+'" w:type="dxa"/>'+('<w:gridSpan w:val="2"/>' if span==2 else '')+'</w:tcPr>'+para(t)+'</w:tc>'
 row1='<w:tr>'+ (cell(mark+'-MERGED',2) if merge else cell(mark+'-LEFT')+cell(mark+'-RIGHT'))+'</w:tr>'
 row2='<w:tr>'+cell(mark+'-ROW2')+cell('ă â î ș ț Ă Â Î Ș Ț')+'</w:tr>'
 return '<w:tbl>'+props+'<w:tblGrid><w:gridCol w:w="4500"/><w:gridCol w:w="4500"/></w:tblGrid>'+row1+row2+'</w:tbl>'
manifest=[]
def save(name,parts,expected,sectextra='',settings='',sectbody=None,last_refs=True):
 p=out/(name+'.docx');entries={}
 types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
 rels=f'<Relationships xmlns="{P}"><Relationship Id="rSettings" Type="{R}/settings" Target="settings.xml"/>';refs=''
 for i,(kind,slot,content) in enumerate(parts,1):
  fname=f'{kind}{i}.xml';id=f'rHf{i}'
  entries['word/'+fname]=f'<w:{"hdr" if kind=="header" else "ftr"} xmlns:w="{W}" xmlns:r="{R}">'+content+'</w:'+('hdr' if kind=='header' else 'ftr')+'>'
  types+=f'<Override PartName="/word/{fname}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}+xml"/>'
  rels+=f'<Relationship Id="{id}" Type="{R}/{kind}" Target="{fname}"/>'
  refs+=f'<w:{kind}Reference w:type="{slot}" r:id="{id}"/>'
 def sect(refs,width=11906):return '<w:sectPr>'+refs+f'<w:pgSz w:w="{width}" w:h="16838"/><w:pgMar w:top="2000" w:bottom="2000" w:left="1440" w:right="1440" w:header="500" w:footer="500"/>'+sectextra+'</w:sectPr>'
 pages=len(expected);body=''
 for i in range(pages):
  body+=para(f'BODY-{i+1}', '<w:pPr><w:pageBreakBefore/></w:pPr>' if i else '')+para('DOCUMENT SINTETIC pentru compatibilitate — fără date reale.')
 if sectbody:body=sectbody(sect,refs)
 entries.update({'[Content_Types].xml':types+'</Types>','_rels/.rels':f'<Relationships xmlns="{P}"><Relationship Id="rDoc" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>','word/_rels/document.xml.rels':rels+'</Relationships>','word/document.xml':f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'+body+sect(refs if last_refs else '')+'</w:body></w:document>','word/settings.xml':f'<w:settings xmlns:w="{W}">'+settings+'</w:settings>'})
 with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for k,v in entries.items():z.writestr(k,v.encode())
 manifest.append({'name':name,'input':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected_per_page':expected})
save('01-inline-header',[('header','default',table('HEADER'))],[['HEADER-LEFT','HEADER-RIGHT','HEADER-ROW2']])
save('02-inline-footer',[('footer','default',table('FOOTER'))],[['FOOTER-LEFT','FOOTER-RIGHT','FOOTER-ROW2']])
save('03-floating-header',[('header','default',table('FLOATHEAD','<w:tblpPr w:leftFromText="0" w:rightFromText="0" w:vertAnchor="page" w:horzAnchor="page" w:tblpX="1440" w:tblpY="500"/>')+para())],[['FLOATHEAD-LEFT','FLOATHEAD-RIGHT','FLOATHEAD-ROW2']])
save('04-floating-footer',[('footer','default',table('FLOATFOOT','<w:tblpPr w:leftFromText="0" w:rightFromText="0" w:vertAnchor="page" w:horzAnchor="page" w:tblpX="1440" w:tblpY="14500"/>')+para())],[['FLOATFOOT-LEFT','FLOATFOOT-RIGHT','FLOATFOOT-ROW2']])
parts=[(kind,slot,table(k+label,percent=True,merge=True)+para()) for kind,k in [('header','H'),('footer','F')] for slot,label in [('default','ODD'),('first','FIRST'),('even','EVEN')]]
save('05-first-even-default',parts,[[x+'FIRST-MERGED' for x in ['H','F']],[x+'EVEN-MERGED' for x in ['H','F']],[x+'ODD-MERGED' for x in ['H','F']]],sectextra='<w:titlePg/>',settings='<w:evenAndOddHeaders/>')
control='<w:sdt><w:sdtPr><w:alias w:val="Synthetic header table"/><w:id w:val="100"/></w:sdtPr><w:sdtContent>'+table('CONTROL',merge=True)+'</w:sdtContent></w:sdt>'
save('06-content-control',[('header','default',control+para()),('footer','default',table('PERCENT',percent=True)+para())],[['CONTROL-MERGED','CONTROL-ROW2','PERCENT-LEFT','PERCENT-ROW2']])
inner=table('NESTED',percent=True);outer='<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="9000"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w="9000" w:type="dxa"/></w:tcPr>'+inner+para()+'</w:tc></w:tr></w:tbl>'
save('07-nested-header',[('header','default',outer+para())],[['NESTED-LEFT','NESTED-RIGHT','NESTED-ROW2']])
save('08-inherited-section',[('header','default',table('LINKED',percent=True)+para())],[['LINKED-LEFT','LINKED-ROW2'],['LINKED-LEFT','LINKED-ROW2']],sectbody=lambda sect,refs:para('BODY-1')+para('', '<w:pPr>'+sect(refs)+'</w:pPr>')+para('BODY-2'),last_refs=False)
with (root/'synthetic-manifest-v2.json').open('x') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
print('Created',len(manifest),'original synthetic cases.')
