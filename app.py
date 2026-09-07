from flask import Flask, render_template, request, jsonify
import requests, re, os
from collections import Counter
from datetime import datetime, timedelta, timezone
from comparisons import comparison_api
from news_sources import NewsQuery, search_news

app = Flask(__name__)
app.register_blueprint(comparison_api)
POS={'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende','gracias','excelente','bien'}
NEG={'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso','corrupción','corrupcion','mentira'}
STOP={'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser','https','esto','pero','porque','cuando','donde'}
UA={'User-Agent':'RADAR-Congreso/1.8 (+political-intelligence; public-source-counter)'}

def sentiment(text):
    words=re.findall(r"[a-záéíóúñü]+",text.lower()); p=sum(w in POS for w in words); n=sum(w in NEG for w in words)
    return 'Positivo' if p>n else 'Negativo' if n>p else 'Neutral'
def topics(items,name):
    c=Counter(); banned=set(re.findall(r"[a-záéíóúñü]+",name.lower()))|STOP
    for x in items:
        for w in re.findall(r"[a-záéíóúñü]{4,}",x['title'].lower()):
            if w not in banned:c[w]+=1
    return [w for w,_ in c.most_common(8)]
def search_terms(name,aliases):return [name]+[a.strip() for a in aliases.split(',') if a.strip()]
def build_query(name,aliases,territory=''):
    q=' OR '.join('"'+t+'"' for t in search_terms(name,aliases)); return q+(' '+territory.strip() if territory.strip() else '')
def fetch_news(name,aliases,territory,days,limit):
    end=datetime.now(timezone.utc)
    coverage=search_news(NewsQuery(tuple(search_terms(name,aliases)),territory.strip()),end-timedelta(days=days),end,limit)
    items=[{**item,'sentiment':sentiment(item['title'])} for item in coverage['items']]
    return items,coverage['message'] if coverage['status']=='unavailable' else None,coverage
def fetch_bluesky_count(name,aliases,territory,days,max_pages=5):
    cutoff=datetime.now(timezone.utc)-timedelta(days=days);cursor=None;seen=set()
    try:
        for _ in range(max_pages):
            params={'q':build_query(name,aliases,territory),'limit':100,'sort':'latest'}
            if cursor:params['cursor']=cursor
            r=requests.get('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts',params=params,timeout=12,headers=UA);r.raise_for_status();data=r.json();posts=data.get('posts',[])
            if not posts:break
            old=False
            for p in posts:
                uri=p.get('uri');created=((p.get('record') or {}).get('createdAt') or p.get('indexedAt') or '')
                try:
                    if datetime.fromisoformat(created.replace('Z','+00:00'))<cutoff:old=True;continue
                except:pass
                if uri:seen.add(uri)
            cursor=data.get('cursor')
            if old or not cursor:break
        return len(seen),'active',None
    except Exception as e:return 0,'error',str(e)
def fetch_reddit_count(name,aliases,territory,days,max_pages=5):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).timestamp();after=None;seen=set()
    try:
        for _ in range(max_pages):
            params={'q':build_query(name,aliases,territory),'sort':'new','limit':100,'raw_json':1,'restrict_sr':'false'}
            if after:params['after']=after
            r=requests.get('https://www.reddit.com/search.json',params=params,timeout=12,headers=UA);r.raise_for_status();data=r.json().get('data',{});children=data.get('children',[])
            if not children:break
            old=False
            for ch in children:
                p=ch.get('data',{})
                if p.get('created_utc',0)<cutoff:old=True;continue
                if p.get('name'):seen.add(p['name'])
            after=data.get('after')
            if old or not after:break
        return len(seen),'active',None
    except Exception as e:return 0,'error',str(e)
def fetch_youtube_count(*args,**kwargs):return (0,'credential_required',None) if not os.getenv('YOUTUBE_API_KEY','').strip() else (0,'credential_required',None)
def restricted_platform(name):return 0,'restricted_access',None
@app.get('/')
def home():return render_template('index.html')
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error':'Ruta no encontrada.'}),404
    return render_template('not_found.html'),404
@app.post('/api/report')
def report():
    d=request.get_json(silent=True)
    if not isinstance(d,dict):return jsonify({'error':'La consulta no es válida.'}),400
    name=d.get('name','')
    if not isinstance(name,str):return jsonify({'error':'Escribe un nombre.'}),400
    name=name.strip()
    if not name:return jsonify({'error':'Escribe un nombre.'}),400
    try:
        days=max(1,min(int(d.get('days',30)),90));limit=max(10,min(int(d.get('limit',60)),100))
    except (TypeError,ValueError):return jsonify({'error':'Elige un periodo válido.'}),400
    aliases=d.get('aliases','');territory=d.get('territory','Colombia')
    if not isinstance(aliases,str) or not isinstance(territory,str) or len(name)>200 or len(aliases)>1000 or len(territory)>100:
        return jsonify({'error':'Revisa el nombre, los términos asociados y la zona.'}),400
    items,err,coverage=fetch_news(name,aliases,territory,days,limit)
    if err:return jsonify({'error':'No fue posible consultar las fuentes en este momento.','detail':err}),502
    counts=Counter(x['sentiment'] for x in items);total=len(items);pos=counts['Positivo'];neg=counts['Negativo'];neu=counts['Neutral'];balance=round((pos-neg)/total*100,1) if total else 0;bsky,bs,_=fetch_bluesky_count(name,aliases,territory,days);reddit,rs,_=fetch_reddit_count(name,aliases,territory,days);yt,ys,_=fetch_youtube_count();fb,fbs,_=restricted_platform('Facebook');ig,igs,_=restricted_platform('Instagram');tt,tts,_=restricted_platform('TikTok');pc={'YouTube':yt,'Bluesky':bsky,'Reddit':reddit,'Facebook':fb,'Instagram':ig,'TikTok':tt};ps={'YouTube':ys,'Bluesky':bs,'Reddit':rs,'Facebook':fbs,'Instagram':igs,'TikTok':tts};social=sum(pc[k] for k,v in ps.items() if v=='active');active=[k for k,v in ps.items() if v=='active']
    summary=(f"Se encontraron {total} publicaciones para {name} en los últimos {days} días. "
             "El conteo corresponde a las fuentes consultadas, no a todas las publicaciones existentes.") if total else (
             f"No se encontraron publicaciones para {name} en las fuentes consultadas durante los últimos {days} días. "
             "Esto no prueba que no existan menciones: la cobertura puede omitir medios o publicaciones recientes.")
    return jsonify({'name':name,'days':days,'total':total,'positive':pos,'negative':neg,'neutral':neu,'balance':balance,'topics':topics(items,name),'summary':summary,'items':items,'web_coverage':{k:v for k,v in coverage.items() if k!='items'},'mentions':{'web':total,'social':social,'combined':total+social,'platform_counts':pc,'platform_status':ps,'active_sources':active,'note':'Total detectado únicamente en fuentes activas.'}})
@app.get('/health')
def health():return {'status':'ok'}
if __name__=='__main__':app.run(host='0.0.0.0',port=5000,debug=True)
