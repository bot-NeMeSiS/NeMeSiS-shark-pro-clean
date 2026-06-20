#!/usr/bin/env python3
from pathlib import Path
import re, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION="V839_REAL_CHATGPT_REVIEW_CLEAN_PRODUCT_FINAL"
errors=[]
def text(path):
    return (ROOT/path).read_text(encoding='utf-8',errors='replace')
if text('VERSION.txt').strip()!=VERSION: errors.append('VERSION.txt no es V839')
app=text('app.py')
base=text('templates/base.html')
css=text('static/app.css')
for marker in [VERSION,"has_v839_shell","has_v839_css","has_v839_real_chatgpt_review"]:
    if marker not in app: errors.append(f'app.py sin {marker}')
for marker in ['data-v839-shell="true"','NEMESIS V839 REAL CHATGPT REVIEW CLEAN PRODUCT FINAL ACTIVE',VERSION]:
    if marker not in base: errors.append(f'base.html sin {marker}')
for marker in ['V839 REAL CHATGPT REVIEW CLEAN PRODUCT FINAL START','bottom-nav-clean','safe-area-inset-bottom','overflow-x:hidden']:
    if marker not in css: errors.append(f'app.css sin {marker}')
if "{{ title or 'NeMeSiS SHARK PRO' }}" in base: errors.append('literal title antiguo en base.html')
for forbidden in ['.git/','.venv/','v636work/']:
    if (ROOT/forbidden).exists(): errors.append(f'basura no eliminada de working copy: {forbidden}')
# __pycache__ puede reaparecer durante compileall; el release builder/audit lo excluye del ZIP final.
print('V839 check:', 'OK' if not errors else 'FAIL')
for e in errors: print('-',e)
sys.exit(1 if errors else 0)
