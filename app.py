from flask import Flask, render_template, request, jsonify
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from comparisons import comparison_api, search_end, iso
from news_sources import NewsQuery, search_news
from source_catalog import public_catalog

app = Flask(__name__)
app.register_blueprint(comparison_api)
POS={'apoyo','respaldo','logro','avance','acuerdo','lidera','celebra','aprobado','victoria','positivo','defiende','gracias','excelente','bien'}
NEG={'crítica','critica','denuncia','escándalo','escandalo','rechazo','ataque','investigación','investigacion','crisis','polémica','polemica','fracaso','corrupción','corrupcion','mentira'}
STOP={'para','como','sobre','entre','desde','ante','tras','este','esta','estos','estas','del','las','los','una','uno','que','por','con','sin','más','mas','sus','han','fue','son','ser','https','esto','pero','porque','cuando','donde'}

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
def fetch_news(name,aliases,territory,days,limit,end=None):
    end=end or search_end()
    coverage=search_news(NewsQuery(tuple(search_terms(name,aliases)),territory.strip()),end-timedelta(days=days),end,limit)
    items=[{**item,'sentiment':sentiment(item['title'])} for item in coverage['items']]
    return items,coverage['message'] if coverage['status']=='unavailable' else None,coverage
@app.get('/')
def home():return render_template('index.html', source_catalog=public_catalog())
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
        end=search_end(d.get('end_time'))
    except (TypeError,ValueError) as error:return jsonify({'error':str(error) or 'Elige un periodo válido.'}),400
    aliases=d.get('aliases','');territory=d.get('territory','Colombia')
    if not isinstance(aliases,str) or not isinstance(territory,str) or len(name)>200 or len(aliases)>1000 or len(territory)>100:
        return jsonify({'error':'Revisa el nombre, los términos asociados y la zona.'}),400
    items,err,coverage=fetch_news(name,aliases,territory,days,limit,end)
    if err:return jsonify({'error':'No fue posible consultar las fuentes en este momento.','detail':err}),502
    counts=Counter(x['sentiment'] for x in items)
    total=len(items);pos=counts['Positivo'];neg=counts['Negativo'];neu=counts['Neutral']
    balance=round((pos-neg)/total*100,1) if total else 0
    summary=(f"Se encontraron {total} publicaciones para {name} en los últimos {days} días. "
             "El conteo corresponde a las fuentes consultadas, no a todas las publicaciones existentes.") if total else (
             f"No se encontraron publicaciones para {name} en las fuentes consultadas durante los últimos {days} días. "
             "Esto no prueba que no existan menciones: la cobertura puede omitir medios o publicaciones recientes.")
    return jsonify({
        'name':name,'days':days,'total':total,'positive':pos,'negative':neg,
        'neutral':neu,'balance':balance,'topics':topics(items,name),'summary':summary,
        'items':items,'web_coverage':{k:v for k,v in coverage.items() if k!='items'},
        'mentions':{'web':total,'combined':total,'note':'Publicaciones detectadas en medios web.'}
    })
@app.get('/health')
def health():return {'status':'ok'}
@app.get('/api/search/window')
def search_window():
    response=jsonify({'end_time':iso(datetime.now(timezone.utc)-timedelta(seconds=45))})
    response.headers['Cache-Control']='no-store'
    return response
if __name__=='__main__':app.run(host='0.0.0.0',port=5000,debug=True)
