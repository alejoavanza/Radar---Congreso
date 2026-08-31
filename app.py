from flask import Flask, render_template, request, jsonify
import feedparser, requests, re, os
from urllib.parse import quote
from collections import Counter
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

POS = {'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende'}
NEG = {'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso'}
STOP = {'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser'}
UA = {'User-Agent':'RADAR-Congreso/1.3 (+political-intelligence; public-source-counter)'}

def sentiment(text):
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    p = sum(w in POS for w in words); n = sum(w in NEG for w in words)
    if p > n: return 'Positivo'
    if n > p: return 'Negativo'
    return 'Neutral'

def topics(items, name):
    c=Counter(); banned=set(re.findall(r"[a-záéíóúñü]+", name.lower()))|STOP
    for x in items:
        for w in re.findall(r"[a-záéíóúñü]{4,}", x['title'].lower()):
            if w not in banned: c[w]+=1
    return [w for w,_ in c.most_common(8)]

def search_terms(name, aliases):
    return [name]+[a.strip() for a in aliases.split(',') if a.strip()]

def build_query(name, aliases, territory=''):
    terms=search_terms(name, aliases)
    q=' OR '.join('"'+t+'"' for t in terms)
    if territory.strip(): q += ' '+territory.strip()
    return q

def fetch_news(name, aliases, territory, days, limit):
    query=build_query(name,aliases,territory)+f' when:{days}d'
    url='https://news.google.com/rss/search?q='+quote(query)+'&hl=es-419&gl=CO&ceid=CO:es-419'
    try:
        r=requests.get(url,timeout=15,headers=UA); r.raise_for_status(); feed=feedparser.parse(r.content)
    except Exception as e:
        return [], str(e)
    out=[]; seen=set()
    for e in feed.entries[:limit]:
        link=e.get('link','#')
        if link in seen: continue
        seen.add(link)
        title=e.get('title','').strip(); source=e.get('source',{}).get('title','') if isinstance(e.get('source',{}),dict) else ''
        out.append({'title':title,'link':link,'published':e.get('published',''),'source':source,'sentiment':sentiment(title)})
    return out, None

def fetch_bluesky_count(name, aliases, territory, days, max_pages=5):
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    query=build_query(name,aliases,territory)
    cursor=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'q':query,'limit':100,'sort':'latest'}
            if cursor: params['cursor']=cursor
            r=requests.get('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts',params=params,timeout=12,headers=UA)
            r.raise_for_status(); data=r.json(); posts=data.get('posts',[])
            if not posts: break
            reached_old=False
            for p in posts:
                uri=p.get('uri'); created=((p.get('record') or {}).get('createdAt') or p.get('indexedAt') or '')
                try:
                    dt=datetime.fromisoformat(created.replace('Z','+00:00'))
                    if dt < cutoff: reached_old=True; continue
                except Exception: pass
                if uri: seen.add(uri)
            cursor=data.get('cursor')
            if reached_old or not cursor: break
        return len(seen), 'active', None
    except Exception as e:
        return 0, 'error', str(e)

def fetch_reddit_count(name, aliases, territory, days, max_pages=5):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).timestamp()
    query=build_query(name,aliases,territory)
    after=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'q':query,'sort':'new','limit':100,'raw_json':1,'restrict_sr':'false'}
            if after: params['after']=after
            r=requests.get('https://www.reddit.com/search.json',params=params,timeout=12,headers=UA)
            r.raise_for_status(); data=r.json().get('data',{}); children=data.get('children',[])
            if not children: break
            reached_old=False
            for ch in children:
                p=ch.get('data',{})
                if p.get('created_utc',0) < cutoff: reached_old=True; continue
                if p.get('name'): seen.add(p['name'])
            after=data.get('after')
            if reached_old or not after: break
        return len(seen), 'active', None
    except Exception as e:
        return 0, 'error', str(e)

def x_status_detail(status_code):
    mapping={
        400:'Solicitud rechazada por X (consulta o parámetros no admitidos).',
        401:'Token rechazado por X. Revisa que el Bearer Token sea válido.',
        402:'X exige créditos o facturación activa para esta consulta.',
        403:'La cuenta/app no tiene permiso para este endpoint de X.',
        404:'Endpoint de X no disponible para esta app.',
        429:'Límite de consultas de X alcanzado temporalmente.'
    }
    return mapping.get(status_code, f'X respondió con HTTP {status_code}.')

def fetch_x_count(name, aliases, territory, days, max_pages=10):
    token=os.getenv('X_BEARER_TOKEN','').strip()
    if not token:
        return 0, 'credential_required', {'code':'missing_token','label':'X: falta Bearer Token','http_status':None,'endpoint':None}
    endpoint='https://api.x.com/2/tweets/search/recent' if days <= 7 else 'https://api.x.com/2/tweets/search/all'
    endpoint_name='recent' if days <= 7 else 'all'
    query=build_query(name,aliases,territory)
    start=(datetime.now(timezone.utc)-timedelta(days=days)).replace(microsecond=0).isoformat().replace('+00:00','Z')
    headers={'Authorization':f'Bearer {token}','User-Agent':UA['User-Agent']}
    next_token=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'query':query,'max_results':100,'start_time':start,'tweet.fields':'created_at'}
            if next_token: params['next_token']=next_token
            r=requests.get(endpoint,params=params,timeout=15,headers=headers)
            if not r.ok:
                status=r.status_code
                return 0, 'error', {
                    'code':f'http_{status}',
                    'label':x_status_detail(status),
                    'http_status':status,
                    'endpoint':endpoint_name
                }
            data=r.json()
            for item in data.get('data',[]):
                if item.get('id'): seen.add(item['id'])
            next_token=(data.get('meta') or {}).get('next_token')
            if not next_token: break
        return len(seen), 'active', {
            'code':'ok',
            'label':f'X conectado: {len(seen)} menciones detectadas.',
            'http_status':200,
            'endpoint':endpoint_name
        }
    except requests.Timeout:
        return 0, 'error', {'code':'timeout','label':'X no respondió a tiempo.','http_status':None,'endpoint':endpoint_name}
    except requests.RequestException:
        return 0, 'error', {'code':'network_error','label':'Error de conexión al consultar X.','http_status':None,'endpoint':endpoint_name}
    except Exception:
        return 0, 'error', {'code':'unexpected_error','label':'Error inesperado al procesar la respuesta de X.','http_status':None,'endpoint':endpoint_name}

def fetch_youtube_count(name, aliases, territory, days, max_pages=10):
    key=os.getenv('YOUTUBE_API_KEY','').strip()
    if not key: return 0, 'credential_required', None
    query=build_query(name,aliases,territory)
    published_after=(datetime.now(timezone.utc)-timedelta(days=days)).replace(microsecond=0).isoformat().replace('+00:00','Z')
    page=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'part':'snippet','q':query,'type':'video','order':'date','maxResults':50,'publishedAfter':published_after,'regionCode':'CO','relevanceLanguage':'es','key':key}
            if page: params['pageToken']=page
            r=requests.get('https://www.googleapis.com/youtube/v3/search',params=params,timeout=15,headers=UA); r.raise_for_status(); data=r.json()
            for item in data.get('items',[]):
                vid=(item.get('id') or {}).get('videoId')
                if vid: seen.add(vid)
            page=data.get('nextPageToken')
            if not page: break
        return len(seen), 'active', None
    except Exception as e:
        return 0, 'error', str(e)

def restricted_platform(name):
    return 0, 'restricted_access', None

@app.get('/')
def home(): return render_template('index.html')

@app.post('/api/report')
def report():
    d=request.get_json(force=True); name=(d.get('name') or '').strip()
    if not name: return jsonify({'error':'Escribe un nombre.'}),400
    days=max(1,min(int(d.get('days',30)),90)); limit=max(10,min(int(d.get('limit',60)),100))
    aliases=d.get('aliases',''); territory=d.get('territory','Colombia')
    items,err=fetch_news(name,aliases,territory,days,limit)
    if err: return jsonify({'error':'No fue posible consultar las fuentes en este momento.','detail':err}),502
    counts=Counter(x['sentiment'] for x in items); total=len(items)
    pos=counts['Positivo']; neg=counts['Negativo']; neu=counts['Neutral']; balance=round((pos-neg)/total*100,1) if total else 0

    bsky,bsky_status,_=fetch_bluesky_count(name,aliases,territory,days)
    reddit,reddit_status,_=fetch_reddit_count(name,aliases,territory,days)
    xcount,xstatus,xdetail=fetch_x_count(name,aliases,territory,days)
    yt,ytstatus,_=fetch_youtube_count(name,aliases,territory,days)
    fb,fbstatus,_=restricted_platform('Facebook')
    ig,igstatus,_=restricted_platform('Instagram')
    tt,ttstatus,_=restricted_platform('TikTok')

    platform_counts={'X':xcount,'YouTube':yt,'Bluesky':bsky,'Reddit':reddit,'Facebook':fb,'Instagram':ig,'TikTok':tt}
    platform_status={'X':xstatus,'YouTube':ytstatus,'Bluesky':bsky_status,'Reddit':reddit_status,'Facebook':fbstatus,'Instagram':igstatus,'TikTok':ttstatus}
    social=sum(platform_counts[k] for k,v in platform_status.items() if v=='active')
    mentions_total=total+social
    active=[k for k,v in platform_status.items() if v=='active']

    summary=f"{name} registra {total} resultados periodísticos en los últimos {days} días. El balance contextual preliminar es {balance:+.1f}, con {pos} titulares positivos, {neg} negativos y {neu} neutrales."
    return jsonify({
        'name':name,'days':days,'total':total,'positive':pos,'negative':neg,'neutral':neu,
        'balance':balance,'topics':topics(items,name),'summary':summary,'items':items,
        'mentions':{
            'web':total,'social':social,'combined':mentions_total,
            'platform_counts':platform_counts,'platform_status':platform_status,'active_sources':active,
            'diagnostics':{'X':xdetail},
            'note':'Total detectado únicamente en fuentes activas. Facebook, Instagram y TikTok requieren acceso especializado/restringido para monitoreo público general.'
        }
    })

@app.get('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
