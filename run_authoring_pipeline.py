#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse,json,os,subprocess,sys
from pathlib import Path

def run(cmd):
    print('\n$ '+' '.join(str(x) for x in cmd)); env=os.environ.copy(); env.setdefault('PYTHONIOENCODING','utf-8')
    p=subprocess.run(cmd,text=True,capture_output=True,encoding='utf-8',errors='replace',env=env)
    if p.stdout: print(p.stdout)
    if p.stderr: print(p.stderr,file=sys.stderr)
    if p.returncode: raise SystemExit(p.returncode)
    return p.stdout

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('author_md'); ap.add_argument('out_dir'); ap.add_argument('--engine',default='fixed_truth_ai_gm_mvp.py'); ap.add_argument('--debug-judge',action='store_true'); ap.add_argument('--debug-llm',action='store_true'); ap.add_argument('--debug-embedding',action='store_true'); ap.add_argument('--debug-all',action='store_true'); a=ap.parse_args()
    py=sys.executable; out_dir=Path(a.out_dir)
    run([py,'md_to_scenario.py',a.author_md,str(out_dir/'scenario.json')]); run([py,'scenario_lint.py',str(out_dir/'scenario.json')])
    ex=json.loads((out_dir/'test_expectations.json').read_text(encoding='utf-8'))
    for name,spec in ex.items():
        cmd=[py,a.engine,'--scenario-dir',str(out_dir),'--script',str(out_dir/f'sample_inputs_{name}.txt')]
        if spec.get('dice_total') is not None: cmd += ['--dice-total',str(spec['dice_total'])]
        if spec.get('skill_dice_total') is not None: cmd += ['--skill-dice-total',str(spec['skill_dice_total'])]
        if a.debug_judge: cmd += ['--debug-judge']
        if a.debug_llm: cmd += ['--debug-llm']
        if a.debug_embedding: cmd += ['--debug-embedding']
        if a.debug_all: cmd += ['--debug-all']
        out=run(cmd); ok=True
        for exp in spec.get('expect',[]) or []:
            if exp not in out: print(f'[FAIL] {name}: missing expected text: {exp}'); ok=False
        for bad in spec.get('expect_not',[]) or []:
            if bad in out: print(f'[FAIL] {name}: forbidden text found: {bad}'); ok=False
        if not ok: raise SystemExit(1)
        print(f'[PASS] {name}')
    print('\n[OK] authoring pipeline completed.')
if __name__=='__main__': main()
