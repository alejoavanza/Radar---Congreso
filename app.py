from flask import Flask, render_template, request, jsonify
import feedparser, requests, re, os
from urllib.parse import quote
from collections import Counter
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
POS={'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende','gracias','excelente','bien'}
NEG={'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso','corrupción','corrupcion','mentira'}
STOP={'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser','https','esto','pero','porque','cuando','donde'}
UA={'User-Agent':'RADAR-Congreso/1.7 (+political-intelligence; public-source-counter)'}

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
    url='https://news.google.com/rss/search?q='+quote(build_query(name,aliases,territory)+f' when:{days}d')+'&hl=es-419&gl=CO&ceid=CO:es-419'
    try:r=requests.get(url,timeout=15,headers=UA);r.raise_for_status();feed=feedparser.parse(r.content)
    except Exception as e:return [],str(e)
    out=[];seen=set()
    for e in feed.entries[:limit]:
        link=e.get('link','#')
        if link in seen:continue
        seen.add(link);title=e.get('title','').strip();source=e.get('source',{}).get('title','') if isinstance(e.get('source',{}),dict) else ''
        out.append({'title':title,'link':link,'published':e.get('published',''),'source':source,'sentiment':sentiment(title)})
    return out,None
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
def x_status_detail(code):return {400:'Solicitud rechazada por X.',401:'Token rechazado por X.',402:'X exige créditos o facturación activa para esta consulta.',403:'La app no tiene permiso para este endpoint de X.',429:'Límite de consultas de X alcanzado temporalmente.'}.get(code,f'X respondió con HTTP {code}.')
def x_headers():return {'Authorization':f"Bearer {os.getenv('X_BEARER_TOKEN','').strip()}",'User-Agent':UA['User-Agent']}
def x_get(url,params=None):
    r=requests.get(url,params=params,timeout=15,headers=x_headers());return r,r.json() if r.ok else {}
def x_user_by_username(username):
    if not username:return None,None
    r,d=x_get(f'https://api.x.com/2/users/by/username/{username.lstrip("@")} ',{'user.fields':'name,username,public_metrics,verified,verified_type'})
    if r.status_code==404 or not r.ok:
        r,d=x_get(f'https://api.x.com/2/users/by/username/{username.lstrip("@")} ',{'user.fields':'name,username,public_metrics,verified,verified_type'})
    return (d.get('data') if r.ok else None),r.status_code

def x_intelligence(posts,users,name):
    sc=Counter();words=Counter();authors=Counter();daily=Counter();total_eng=0;post_rows=[];banned=set(re.findall(r"[a-záéíóúñü]+",name.lower()))|STOP
    for p in posts:
        text=p.get('text','');s=sentiment(text);sc[s]+=1;pm=p.get('public_metrics') or {};likes=int(pm.get('like_count',0) or 0);reposts=int(pm.get('retweet_count',pm.get('repost_count',0)) or 0);replies=int(pm.get('reply_count',0) or 0);quotes=int(pm.get('quote_count',0) or 0);eng=likes+reposts+replies+quotes;total_eng+=eng;aid=p.get('author_id');authors[aid]+=1;u=users.get(aid,{});username=u.get('username','');followers=int((u.get('public_metrics') or {}).get('followers_count',0) or 0);pid=p.get('id','');url=f'https://x.com/{username}/status/{pid}' if username and pid else ''
        post_rows.append({'id':pid,'author_id':aid,'text':text,'created_at':p.get('created_at',''),'author_name':u.get('name','Cuenta X'),'username':username,'followers':followers,'verified':bool(u.get('verified',False)),'verified_type':u.get('verified_type','') or '','likes':likes,'reposts':reposts,'replies':replies,'quotes':quotes,'engagement':eng,'url':url,'sentiment':s})
        if p.get('created_at','')[:10]:daily[p['created_at'][:10]]+=1
        for w in re.findall(r"[a-záéíóúñü]{4,}",text.lower()):
            if w not in banned:words[w]+=1
    top_authors=[];top_accounts=[]
    for aid,count in authors.items():
        u=users.get(aid,{});username=u.get('username','');base={'name':u.get('name','Cuenta X'),'username':username,'profile_url':f'https://x.com/{username}' if username else '','mentions':count,'followers':int((u.get('public_metrics') or {}).get('followers_count',0) or 0),'verified':bool(u.get('verified',False)),'verified_type':u.get('verified_type','') or ''};top_accounts.append(base)
        aps=sorted([p for p in post_rows if p['author_id']==aid],key=lambda p:(p['engagement'],p['created_at']),reverse=True)[:5];top_authors.append({**base,'posts':[{'text':p['text'],'url':p['url'],'engagement':p['engagement']} for p in aps]})
    top_authors=sorted(top_authors,key=lambda a:a['mentions'],reverse=True)[:5];top_accounts=sorted(top_accounts,key=lambda a:(a['followers'],a['mentions']),reverse=True)[:10];top_posts=sorted(post_rows,key=lambda p:(p['engagement'],p['followers']),reverse=True)[:10];n=len(posts)
    return {'total':n,'positive':sc['Positivo'],'negative':sc['Negativo'],'neutral':sc['Neutral'],'balance':round((sc['Positivo']-sc['Negativo'])/n*100,1) if n else 0,'engagement':total_eng,'avg_engagement':round(total_eng/n,1) if n else 0,'top_topics':[w for w,_ in words.most_common(8)],'top_authors':top_authors,'top_accounts':top_accounts,'top_posts':top_posts,'daily':[{'date':d,'count':c} for d,c in sorted(daily.items())]}
def fetch_x_count(name,aliases,territory,days,max_pages=10):
    if not os.getenv('X_BEARER_TOKEN','').strip():return 0,'credential_required',{'code':'missing_token','label':'X: falta Bearer Token'},None
    endpoint='https://api.x.com/2/tweets/search/recent' if days<=7 else 'https://api.x.com/2/tweets/search/all';start=(datetime.now(timezone.utc)-timedelta(days=days)).replace(microsecond=0).isoformat().replace('+00:00','Z');nxt=None;posts={};users={}
    try:
        for _ in range(max_pages):
            params={'query':build_query(name,aliases,territory),'max_results':100,'start_time':start,'tweet.fields':'created_at,author_id,public_metrics,lang,referenced_tweets','expansions':'author_id','user.fields':'name,username,public_metrics,verified,verified_type'}
            if nxt:params['next_token']=nxt
            r=requests.get(endpoint,params=params,timeout=15,headers=x_headers())
            if not r.ok:return 0,'error',{'code':f'http_{r.status_code}','label':x_status_detail(r.status_code),'http_status':r.status_code},None
            data=r.json()
            for u in (data.get('includes') or {}).get('users',[]):users[u.get('id')]=u
            for p in data.get('data',[]):
                if p.get('id'):posts[p['id']]=p
            nxt=(data.get('meta') or {}).get('next_token')
            if not nxt:break
        intel=x_intelligence(list(posts.values()),users,name);return len(posts),'active',{'code':'ok','label':f'X conectado: {len(posts)} menciones detectadas.','http_status':200},intel
    except requests.Timeout:return 0,'error',{'code':'timeout','label':'X no respondió a tiempo.'},None
    except Exception:return 0,'error',{'code':'unexpected_error','label':'Error al procesar X.'},None

def mi_red(username,max_followers_pages=3):
    username=(username or '').strip().lstrip('@')
    if not username:return {'status':'needs_username','label':'Escribe tu @usuario de X para analizar MI RED.'}
    try:
        r,d=x_get(f'https://api.x.com/2/users/by/username/{username}',{'user.fields':'name,username,public_metrics,verified,verified_type'})
        if not r.ok:return {'status':'error','label':x_status_detail(r.status_code),'http_status':r.status_code}
        me=d.get('data') or {};uid=me.get('id');followers=[];token=None
        for _ in range(max_followers_pages):
            params={'max_results':1000,'user.fields':'name,username,public_metrics,verified,verified_type'}
            if token:params['pagination_token']=token
            fr,fd=x_get(f'https://api.x.com/2/users/{uid}/followers',params)
            if not fr.ok:return {'status':'partial','label':f'Perfil conectado, pero X no permitió leer seguidores ({fr.status_code}).','profile':me,'profile_url':f'https://x.com/{username}','followers':[],'verified_followers':[]}
            followers.extend(fd.get('data') or []);token=(fd.get('meta') or {}).get('next_token')
            if not token:break
        def row(u):
            un=u.get('username','');return {'id':u.get('id'),'name':u.get('name','Cuenta X'),'username':un,'profile_url':f'https://x.com/{un}' if un else '','followers':int((u.get('public_metrics') or {}).get('followers_count',0) or 0),'verified':bool(u.get('verified',False)),'verified_type':u.get('verified_type','') or ''}
        rows=[row(u) for u in followers];top=sorted(rows,key=lambda x:x['followers'],reverse=True)[:10];verified=sorted([x for x in rows if x['verified']],key=lambda x:x['followers'],reverse=True)[:20]
        return {'status':'active','label':f'MI RED conectada: {len(rows)} seguidores analizados.','profile':row(me),'profile_url':f'https://x.com/{username}','followers_analyzed':len(rows),'top_followers':top,'verified_count':sum(1 for x in rows if x['verified']),'verified_followers':verified,'coverage_note':'Ranking calculado sobre los seguidores recuperados en esta consulta; puede ser parcial si la cuenta supera el límite de páginas analizadas.'}
    except requests.Timeout:return {'status':'error','label':'X no respondió a tiempo al consultar MI RED.'}
    except Exception:return {'status':'error','label':'No fue posible procesar MI RED.'}
def fetch_youtube_count(*args,**kwargs):return (0,'credential_required',None) if not os.getenv('YOUTUBE_API_KEY','').strip() else (0,'credential_required',None)
def restricted_platform(name):return 0,'restricted_access',None
@app.get('/')
def home():return render_template('index.html')
@app.post('/api/report')
def report():
    d=request.get_json(force=True);name=(d.get('name') or '').strip()
    if not name:return jsonify({'error':'Escribe un nombre.'}),400
    days=max(1,min(int(d.get('days',30)),90));limit=max(10,min(int(d.get('limit',60)),100));aliases=d.get('aliases','');territory=d.get('territory','Colombia');items,err=fetch_news(name,aliases,territory,days,limit)
    if err:return jsonify({'error':'No fue posible consultar las fuentes en este momento.','detail':err}),502
    counts=Counter(x['sentiment'] for x in items);total=len(items);pos=counts['Positivo'];neg=counts['Negativo'];neu=counts['Neutral'];balance=round((pos-neg)/total*100,1) if total else 0;bsky,bs,_=fetch_bluesky_count(name,aliases,territory,days);reddit,rs,_=fetch_reddit_count(name,aliases,territory,days);xcount,xs,xd,xintel=fetch_x_count(name,aliases,territory,days);yt,ys,_=fetch_youtube_count();fb,fbs,_=restricted_platform('Facebook');ig,igs,_=restricted_platform('Instagram');tt,tts,_=restricted_platform('TikTok');pc={'X':xcount,'YouTube':yt,'Bluesky':bsky,'Reddit':reddit,'Facebook':fb,'Instagram':ig,'TikTok':tt};ps={'X':xs,'YouTube':ys,'Bluesky':bs,'Reddit':rs,'Facebook':fbs,'Instagram':igs,'TikTok':tts};social=sum(pc[k] for k,v in ps.items() if v=='active');active=[k for k,v in ps.items() if v=='active'];summary=f"{name} registra {total} resultados periodísticos en los últimos {days} días. El balance contextual preliminar es {balance:+.1f}, con {pos} titulares positivos, {neg} negativos y {neu} neutrales."
    return jsonify({'name':name,'days':days,'total':total,'positive':pos,'negative':neg,'neutral':neu,'balance':balance,'topics':topics(items,name),'summary':summary,'items':items,'mentions':{'web':total,'social':social,'combined':total+social,'platform_counts':pc,'platform_status':ps,'active_sources':active,'diagnostics':{'X':xd},'x_intelligence':xintel,'note':'Total detectado únicamente en fuentes activas.'}})
@app.post('/api/mi-red')
def network():return jsonify(mi_red((request.get_json(force=True) or {}).get('username','')))
@app.get('/health')
def health():return {'status':'ok'}
if __name__=='__main__':app.run(host='0.0.0.0',port=5000,debug=True)
