from pathlib import Path
import zipfile,json,hashlib,sys
r=Path(sys.argv[1]).resolve();out=r/'synthetic-extra';out.mkdir()
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def p(t=''):return '<w:p><w:r><w:rPr><w:rFonts w:ascii="Source Sans 3" w:hAnsi="Source Sans 3"/><w:sz w:val="18"/></w:rPr><w:t>'+t+'</w:t></w:r></w:p>'
widths=[800,800,1200,1200,1000,3500,500]
def cell(text,width,merge=None):
 pr=f'<w:tcW w:type="dxa" w:w="{width}"/><w:vAlign w:val="center"/>'
 if merge:pr+='<w:vMerge'+(' w:val="restart"' if merge=='restart' else '')+'/>'
 return '<w:tc><w:tcPr>'+pr+'</w:tcPr>'+p(text)+'</w:tc>'
def table(float=False):
 positioning='<w:tblpPr w:vertAnchor="margin" w:horzAnchor="margin" w:tblpX="0" w:tblpYSpec="bottom"/>' if float else ''
 b='<w:tblBorders>'+''.join(f'<w:{e} w:val="single" w:sz="10" w:color="28556A"/>' for e in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
 rows=''
 for row in range(3):
  cells=''.join(cell('COL-'+chr(65+i) if row==0 else ('ROW3' if row==2 and i==0 else 'TEST'),width) for i,width in enumerate(widths[:5]))
  cells+=cell('SYNTHETIC-MERGED' if row==0 else '',widths[5],'restart' if row==0 else 'continue')
  cells+=cell('P' if row==0 else '',widths[6],'restart' if row==0 else 'continue')
  rows+='<w:tr><w:trPr><w:trHeight w:val="400" w:hRule="atLeast"/></w:trPr>'+cells+'</w:tr>'
 return '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/>'+b+positioning+'</w:tblPr><w:tblGrid>'+''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)+'</w:tblGrid>'+rows+'</w:tbl>'
with zipfile.ZipFile(r/'synthetic-v2/02-inline-footer.docx') as z:base={n:z.read(n) for n in z.namelist()}
cases=[('09-vertical-merge-footer',table()),('10-textbox-footer','<w:p><w:r><w:pict><v:rect id="synthetic-footer-box" style="position:absolute;margin-left:0pt;margin-top:0pt;width:450pt;height:85pt;mso-position-horizontal-relative:margin;mso-position-vertical-relative:margin;mso-position-vertical:bottom" stroked="f" filled="f"><v:textbox inset="0,0,0,0"><w:txbxContent>'+table()+p()+'</w:txbxContent></v:textbox></v:rect></w:pict></w:r></w:p>'),('11-floating-merged-footer',table(True)+p())]
manifest=[]
for name,body in cases:
 entries=dict(base);entries['word/footer1.xml']=(f'<w:ftr xmlns:w="{W}" xmlns:v="urn:schemas-microsoft-com:vml">'+body+'</w:ftr>').encode()
 path=out/(name+'.docx')
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for key,data in entries.items():z.writestr(key,data)
 manifest.append({'name':name,'input':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'expected_per_page':[['SYNTHETIC-MERGED','COL-A','ROW3']]})
with (r/'synthetic-extra-manifest.json').open('x') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
