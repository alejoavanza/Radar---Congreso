from flask import Flask, render_template, request, jsonify
import feedparser, requests, re
from urllib.parse import quote
from collections import Counter

app = Flask(__name__)

POS = {'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende'}
NEG = {'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso'}
STOP = {'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser'}

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

def fetch_news(name, aliases, territory, days, limit):
    terms=[name]+[a.strip() for a in aliases.split(',') if a.strip()]
    query=' OR '.join('"'+t+'"' for t in terms)
    if territory.strip(): query += ' '+territory.strip()
    query += f' when:{days}d'
    url='https://news.google.com/rss/search?q='+quote(query)+'&hl=es-419&gl=CO&ceid=CO:es-419'
    try:
        r=requests.get(url,timeout=15,headers={'User-Agent':'Mozilla/5.0 RADAR-Congreso/1.0'})
        r.raise_for_status(); feed=feedparser.parse(r.content)
    except Exception as e:
        return [], str(e)
    out=[]
    for e in feed.entries[:limit]:
        title=e.get('title','').strip(); source=e.get('source',{}).get('title','') if isinstance(e.get('source',{}),dict) else ''
        out.append({'title':title,'link':e.get('link','#'),'published':e.get('published',''),'source':source,'sentiment':sentiment(title)})
    return out, None

@app.get('/')
def home(): return render_template('index.html')

@app.post('/api/report')
def report():
    d=request.get_json(force=True); name=(d.get('name') or '').strip()
    if not name: return jsonify({'error':'Escribe un nombre.'}),400
    days=max(1,min(int(d.get('days',30)),90)); limit=max(10,min(int(d.get('limit',60)),100))
    items,err=fetch_news(name,d.get('aliases',''),d.get('territory','Colombia'),days,limit)
    if err: return jsonify({'error':'No fue posible consultar las fuentes en este momento.','detail':err}),502
    counts=Counter(x['sentiment'] for x in items); total=len(items)
    pos=counts['Positivo']; neg=counts['Negativo']; neu=counts['Neutral']
    balance=round((pos-neg)/total*100,1) if total else 0
    summary=f"{name} registra {total} resultados periodísticos en los últimos {days} días. El balance contextual preliminar es {balance:+.1f}, con {pos} titulares positivos, {neg} negativos y {neu} neutrales."
    return jsonify({'name':name,'days':days,'total':total,'positive':pos,'negative':neg,'neutral':neu,'balance':balance,'topics':topics(items,name),'summary':summary,'items':items})

@app.get('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
