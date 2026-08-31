from flask import Flask, render_template, request, jsonify
import feedparser, requests, re
from urllib.parse import quote
from collections import Counter
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

POS = {'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende'}
NEG = {'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso'}
STOP = {'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser'}
UA = {'User-Agent':'RADAR-Congreso/1.1 (+political-intelligence; public-source-counter)'}

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

def fetch_news(name, aliases, territory, days, limit):
    terms=search_terms(name, aliases)
    query=' OR '.join('"'+t+'"' for t in terms)
    if territory.strip(): query += ' '+territory.strip()
    query += f' when:{days}d'
    url='https://news.google.com/rss/search?q='+quote(query)+'&hl=es-419&gl=CO&ceid=CO:es-419'
    try:
        r=requests.get(url,timeout=15,headers=UA)
        r.raise_for_status(); feed=feedparser.parse(r.content)
    except Exception as e:
        return [], str(e)
    out=[]
    seen=set()
    for e in feed.entries[:limit]:
        link=e.get('link','#')
        if link in seen: continue
        seen.add(link)
        title=e.get('title','').strip(); source=e.get('source',{}).get('title','') if isinstance(e.get('source',{}),dict) else ''
        out.append({'title':title,'link':link,'published':e.get('published',''),'source':source,'sentiment':sentiment(title)})
    return out, None

def fetch_bluesky_count(name, aliases, territory, days, max_pages=5):
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    terms=search_terms(name, aliases)
    query=' OR '.join('"'+t+'"' for t in terms)
    if territory.strip(): query += ' '+territory.strip()
    cursor=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'q':query,'limit':100,'sort':'latest'}
            if cursor: params['cursor']=cursor
            r=requests.get('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts',params=params,timeout=12,headers=UA)
            r.raise_for_status(); data=r.json()
            posts=data.get('posts',[])
            if not posts: break
            reached_old=False
            for p in posts:
                uri=p.get('uri')
                created=((p.get('record') or {}).get('createdAt') or p.get('indexedAt') or '')
                try:
                    dt=datetime.fromisoformat(created.replace('Z','+00:00'))
                    if dt < cutoff:
                        reached_old=True
                        continue
                except Exception:
                    pass
                if uri: seen.add(uri)
            cursor=data.get('cursor')
            if reached_old or not cursor: break
        return len(seen), None
    except Exception as e:
        return 0, str(e)

def fetch_reddit_count(name, aliases, territory, days, max_pages=5):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).timestamp()
    terms=search_terms(name, aliases)
    query=' OR '.join('"'+t+'"' for t in terms)
    if territory.strip(): query += ' '+territory.strip()
    after=None; seen=set()
    try:
        for _ in range(max_pages):
            params={'q':query,'sort':'new','limit':100,'raw_json':1,'restrict_sr':'false'}
            if after: params['after']=after
            r=requests.get('https://www.reddit.com/search.json',params=params,timeout=12,headers=UA)
            r.raise_for_status(); data=r.json().get('data',{})
            children=data.get('children',[])
            if not children: break
            reached_old=False
            for ch in children:
                p=ch.get('data',{})
                if p.get('created_utc',0) < cutoff:
                    reached_old=True
                    continue
                if p.get('name'): seen.add(p['name'])
            after=data.get('after')
            if reached_old or not after: break
        return len(seen), None
    except Exception as e:
        return 0, str(e)

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
    pos=counts['Positivo']; neg=counts['Negativo']; neu=counts['Neutral']
    balance=round((pos-neg)/total*100,1) if total else 0

    bluesky,bsky_err=fetch_bluesky_count(name,aliases,territory,days)
    reddit,reddit_err=fetch_reddit_count(name,aliases,territory,days)
    social=bluesky+reddit
    mentions_total=total+social
    social_sources=[]
    if not bsky_err: social_sources.append('Bluesky')
    if not reddit_err: social_sources.append('Reddit')

    summary=f"{name} registra {total} resultados periodísticos en los últimos {days} días. El balance contextual preliminar es {balance:+.1f}, con {pos} titulares positivos, {neg} negativos y {neu} neutrales."
    return jsonify({
        'name':name,'days':days,'total':total,'positive':pos,'negative':neg,'neutral':neu,
        'balance':balance,'topics':topics(items,name),'summary':summary,'items':items,
        'mentions':{
            'web':total,
            'social':social,
            'combined':mentions_total,
            'social_sources':social_sources,
            'note':'Menciones detectadas en las fuentes conectadas. No equivale al total absoluto de internet ni incluye todavía X, Facebook, Instagram o TikTok.'
        }
    })

@app.get('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
