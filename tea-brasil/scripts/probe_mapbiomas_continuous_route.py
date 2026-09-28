#!/usr/bin/env python3
"""Inspeciona metadados/rotas do produto contínuo de temperatura MapBiomas."""
import json,re,urllib.error,urllib.parse,urllib.request
HOME='https://plataforma.mapbiomas.org/projects/mapbiomas/brazil'
API='https://prd.plataforma.mapbiomas.org/api/v1/brazil'
UA={'User-Agent':'TEA-Brasil/1.0'}
APIH={'User-Agent':'TEA-Brasil/1.0','tenant-id':'mapbiomas','Accept':'application/json'}
KEYS={'atmosphere_annual_mean_air_temperature','atmosphere_annual_maximum_air_temperature','atmosphere_annual_minimum_air_temperature'}
def get_text(u,headers=UA):
 with urllib.request.urlopen(urllib.request.Request(u,headers=headers),timeout=90) as r:return r.read().decode('utf-8',errors='replace')
def get_json(path):
 try:
  return json.loads(get_text(API+path,APIH))
 except urllib.error.HTTPError as e:
  b=e.read().decode(errors='replace');return {'http':e.code,'raw':b[:3000]}
def contexts(js,needle,radius=1200,limit=20):
 out=[]
 for m in re.finditer(re.escape(needle),js):
  frag=re.sub(r'\s+',' ',js[max(0,m.start()-radius):min(len(js),m.end()+radius)])
  if frag not in out:out.append(frag)
  if len(out)>=limit:break
 return out
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values():yield from walk(v)
 elif isinstance(o,list):
  for v in o:yield from walk(v)
def main():
 obj=get_json('/themes/subthemes')
 matches=[]
 for d in walk(obj):
  if str(d.get('key','')) in KEYS:matches.append(d)
 print('SUBTHEME_MATCHES',len(matches))
 for d in matches:print('SUBTHEME_JSON',json.dumps(d,ensure_ascii=False,indent=2)[:30000])
 h=get_text(HOME);scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',h,re.I)
 for src in scripts:
  if '/assets/' not in src or not src.endswith('.js'):continue
  url=urllib.parse.urljoin(HOME,src);js=get_text(url)
  if 'atmosphere_annual_mean_air_temperature' not in js and '/statistics/ranking/subtheme' not in js:continue
  print('BUNDLE',url)
  for needle in ('/statistics/ranking/subtheme','/maps/tiles','/tiles','tileUrl','mapUrl','downloadUrl','asset','subthemeKey'):
   vals=contexts(js,needle)
   if not vals:continue
   print('\nNEEDLE',needle,'COUNT',len(vals))
   for i,v in enumerate(vals,1):print('CTX',needle,i,v[:2600])
if __name__=='__main__':main()
