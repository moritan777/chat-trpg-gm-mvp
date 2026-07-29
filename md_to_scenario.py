#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse,json,re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('author_md'); ap.add_argument('scenario_json'); a=ap.parse_args()
    text=Path(a.author_md).read_text(encoding='utf-8')
    m=re.search(r"```scenario-json\s*(.*?)\s*```", text, re.S)
    if not m: raise SystemExit('scenario-json block not found')
    sc=json.loads(m.group(1)); tests=sc.pop('tests',{})
    out=Path(a.scenario_json); out.parent.mkdir(parents=True,exist_ok=True)
    ex={}
    for name,spec in tests.items():
        script=out.parent/f'sample_inputs_{name}.txt'
        script.write_text('\n'.join(spec.get('commands',[]))+'\n', encoding='utf-8')
        print(f'Wrote {script}')
        ex[name]={k:spec[k] for k in ['expect','expect_not','dice_total','skill_dice_total'] if k in spec}
    (out.parent/'test_expectations.json').write_text(json.dumps(ex,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Wrote {out.parent/'test_expectations.json'}")
    out.write_text(json.dumps(sc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Wrote {out}')
if __name__=='__main__': main()
