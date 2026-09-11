import zipfile, re, sys, os
from xml.etree import ElementTree as ET

src = r"D:\SlideShare_Presentation macular dystrophies.pptx"
out = r"C:\Users\Shash\AndroidStudioProjects\MediGyaan\tmp_pptx_text.txt"

z = zipfile.ZipFile(src)
names = z.namelist()
slide_files = sorted([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)],
                     key=lambda n: int(re.search(r'\d+', n).group()))

lines = []
lines.append(f"TOTAL FILES IN PPTX: {len(names)}")
lines.append(f"SLIDES FOUND: {len(slide_files)}")
lines.append("=" * 70)

for sf in slide_files:
    num = int(re.search(r'\d+', sf).group())
    xml = z.read(sf)
    root = ET.fromstring(xml)
    paras = []
    for p in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}p'):
        para_txt = ''.join(t.text or '' for t in p.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'))
        if para_txt.strip():
            paras.append(para_txt.strip())
    rels_name = f"ppt/slides/_rels/slide{num}.xml.rels"
    imgs = []
    if rels_name in names:
        rels = ET.fromstring(z.read(rels_name))
        for rel in rels:
            tgt = rel.get('Target', '')
            if '/media/' in tgt and 'image' in rel.get('Type', ''):
                imgs.append(tgt.split('/')[-1])
    lines.append(f"\n{'='*70}\n### SLIDE {num}  (images: {', '.join(imgs) if imgs else 'none'})")
    for para in paras:
        lines.append(para)

with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Wrote {out} — {len(lines)} lines")
for l in lines[:50]:
    print(l)