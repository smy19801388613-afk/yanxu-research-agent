"""Optional local Windows OCR. Rendered pages and recognizer output stay on this machine."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from statistics import median
import pypdfium2
from .config import ROOT


def row_text(words):
    if not words: return ""
    heights=[w['h'] for w in words if re.search(r'\w',w['text'])] or [w['h'] for w in words]
    tolerance=max(5,median(heights)*.7)
    rows=[]
    for word in sorted(words,key=lambda w:w['y']+w['h']/2):
        center=word['y']+word['h']/2
        row=next((r for r in reversed(rows) if abs(r[0]-center)<tolerance),None)
        if row is None: rows.append([center,[word]])
        else: row[1].append(word)
    lines=[]
    for _,values in rows:
        previous=None;line=""
        for word in sorted(values,key=lambda w:w['x']):
            adjacent=previous and word['x']-(previous['x']+previous['w'])<max(3,word['h']*.55)
            line+=("" if adjacent else " ")+word['text']
            previous=word
        lines.append(line.strip())
    text="\n".join(lines)
    return re.sub(r"(?<=[\u3400-\u9fff])[ \t]+(?=[\u3400-\u9fff])","",text)


def recognize(path,pages):
    if os.name!='nt': raise ValueError("扫描页需要 OCR；当前本机识别仅支持 Windows 中文识别组件")
    with tempfile.TemporaryDirectory(prefix='research-ocr-') as temp:
        folder=Path(temp);manifest=[]
        with pypdfium2.PdfDocument(path) as pdf:
            for index in pages:
                page=pdf[index-1]
                try:
                    scale=min(3,2500/max(page.get_size()))
                    target=folder/f'{index}.png';bitmap=page.render(scale=scale)
                    try: bitmap.to_pil().save(target)
                    finally: bitmap.close()
                    manifest.append({'page':index,'path':str(target)})
                finally: page.close()
        input_path=folder/'input.json';output_path=folder/'output.json'
        input_path.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                str(ROOT/'scripts/ocr_pdf_pages.ps1'),'-ManifestPath',str(input_path),'-OutputPath',str(output_path)],
                capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode!=0: raise ValueError("本机中文 OCR 未能完成，请确认 Windows 中文识别组件可用，或打开原文人工核对")
            values=json.loads(output_path.read_text(encoding='utf-8-sig'))
        except (OSError,subprocess.TimeoutExpired,json.JSONDecodeError):
            raise ValueError("本机 OCR 未完成或超时，可重试较少页数，或打开原文人工核对") from None
        return {int(v['page']):row_text(v['words']) for v in values}
