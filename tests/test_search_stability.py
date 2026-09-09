import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import app as radar
import news_sources as news
import web_discovery as web
import search_state
from threading import Event
from time import monotonic
from source_catalog import SOURCES


class StabilityTest(unittest.TestCase):
    def setUp(self):
        search_state.clear()
        self.end=datetime.now(timezone.utc).replace(microsecond=0)-timedelta(minutes=2)
        self.query=news.NewsQuery(('Alejandro Toro','David Alejandro Toro Ramírez'), 'Colombia')

    def item(self, title, hours):
        return {'title':title,'url':'https://medio.example/'+title,'link':'https://medio.example/'+title,
                'source':'Medio','publisher_domain':'medio.example','published':news.iso(self.end-timedelta(hours=hours)),
                'discovery':'Google Noticias'}

    def result(self, items, unavailable=False):
        return {'status':'unavailable' if unavailable else 'available','items':items,'count':None if unavailable else len(items),
                'limited':unavailable,'message':'Fallo temporal.' if unavailable else 'Resultados verificados.'}

    def test_same_window_24h_7d_24h_preserves_notes_and_reuses_identical_query(self):
        recent, older=self.item('reciente',1),self.item('anterior',72)
        with patch.object(news, '_search_news', side_effect=[self.result([recent]),self.result([older])]) as run:
            one=news.search_news(self.query,self.end-timedelta(days=1),self.end)
            seven=news.search_news(self.query,self.end-timedelta(days=7),self.end)
            again=news.search_news(self.query,self.end-timedelta(days=1),self.end)
        self.assertEqual(run.call_count,2)
        self.assertEqual(one['items'],again['items'])
        self.assertEqual(seven['count'],2)
        self.assertEqual(seven['retained_count'],1)

    def test_transient_failure_keeps_only_prior_valid_notes_and_no_other_zone(self):
        with patch.object(news,'_search_news',return_value=self.result([self.item('reciente',1),self.item('anterior',72)])):
            news.search_news(self.query,self.end-timedelta(days=7),self.end)
        with patch.object(news,'_search_news',return_value=self.result([],True)):
            current=news.search_news(self.query,self.end-timedelta(days=1),self.end)
            other=news.search_news(news.NewsQuery(self.query.terms,'Antioquia'),self.end-timedelta(days=1),self.end)
        self.assertEqual(current['count'],1)
        self.assertTrue(current['limited'])
        self.assertIsNone(other['count'])

    def test_verified_page_is_reused_across_periods_but_outside_dates_are_filtered(self):
        candidate={'url':'https://medio.example/nota','engine':'web','title':'Nota'}
        article=self.item('nota',30)
        with patch.object(web,'_verify_page',return_value=(article,0)) as read:
            self.assertIsNotNone(web.verify_page(candidate,self.query.terms,self.end-timedelta(days=7),self.end,'Colombia')[0])
        with patch.object(web,'_verify_page',side_effect=ValueError('HTTP 403')) as read:
            self.assertIsNone(web.verify_page(candidate,self.query.terms,self.end-timedelta(days=1),self.end,'Colombia')[0])
            self.assertIsNotNone(web.verify_page(candidate,self.query.terms,self.end-timedelta(days=7),self.end,'Colombia')[0])
            read.assert_not_called()

    def test_partial_verification_failure_is_not_a_confirmed_zero(self):
        candidate={'url':'https://medio.example/nota','engine':'web','title':'Nota','candidate':True}
        with patch.object(news,'BATCHES',()),patch.object(news,'google_news',return_value=([candidate],0,False)), \
             patch.object(web,'duckduckgo_web',return_value=([],0,False)),patch.object(web,'verify_candidates',return_value=([],1,False)):
            result=news.search_news(self.query,self.end-timedelta(days=1),self.end)
        self.assertEqual(result['status'],'unavailable')
        self.assertIsNone(result['count'])

    def test_all_38_sources_and_six_names_need_at_most_29_index_calls(self):
        names=('Nombre Uno','Nombre Dos','Nombre Tres','Nombre Cuatro','Nombre Cinco','Nombre Seis')
        with patch.object(news,'google_news',return_value=([],0,False)) as broad, \
             patch.object(news,'focused_news',return_value=([],0,False)) as focused, \
             patch.object(web,'duckduckgo_web',return_value=([],0,False)) as duck:
            result=news.search_news(news.NewsQuery(names,'Colombia'),self.end-timedelta(days=7),self.end)
        self.assertEqual(broad.call_count+focused.call_count+duck.call_count,29)
        for name in names:
            matched=[call for call in focused.call_args_list if name in ((call.args[0],) if isinstance(call.args[0],str) else call.args[0])]
            self.assertCountEqual([s.id for call in matched for s in call.args[4]], [s.id for s in SOURCES])
        self.assertEqual(result['catalog']['searchable'],38)

    def test_report_respects_explicit_cutoff_and_rejects_expired_windows(self):
        client=radar.app.test_client()
        with patch.object(radar,'fetch_news',return_value=([],None,{'status':'available','message':'OK'})) as fetch:
            response=client.post('/api/report',json={'name':'Alejandro Toro','days':1,'end_time':news.iso(self.end)})
        self.assertEqual(response.status_code,200)
        self.assertEqual(fetch.call_args.args[-1],self.end)
        with patch.object(radar,'fetch_news') as fetch:
            response=client.post('/api/report',json={'name':'Alejandro Toro','end_time':news.iso(self.end-timedelta(hours=1))})
            self.assertEqual(response.status_code,400)
            fetch.assert_not_called()

    def test_short_periods_share_discovery_but_old_notes_never_enter_24h(self):
        recent=dict(self.item('reciente',1),candidate=True,engine='Google Noticias')
        old=dict(self.item('anterior',72),candidate=True,engine='Google Noticias')
        calls=[]
        with patch.object(news,'BATCHES',()), \
             patch.object(news,'google_news',return_value=([recent,old],0,False)) as index, \
             patch.object(web,'duckduckgo_web',return_value=([],0,False)), \
             patch.object(web,'verify_candidates',side_effect=lambda found,*args,**kwargs:(found,0,False)):
            for days in (1,7):
                result=news.search_news(self.query,self.end-timedelta(days=days),self.end)
                calls.append(index.call_args_list.copy());index.reset_mock()
                self.assertEqual(result['count'],1 if days==1 else 2)
                self.assertTrue(all(self.end-timedelta(days=days) <= news.publication_date(i['published']) < self.end for i in result['items']))
        self.assertEqual(calls[0],calls[1])

    def test_expired_verification_budget_returns_partial_without_waiting_for_slow_sites(self):
        release=Event()
        candidate={'url':'https://slow.example/article','engine':'web','title':'Noticia'}
        def slow(*args):
            release.wait(2)
            return None,1
        try:
            with patch.object(web,'verify_page',side_effect=slow):
                started=monotonic()
                _,skipped,limited=web.verify_candidates([candidate],self.query.terms,self.end-timedelta(days=1),self.end,deadline=monotonic()-1)
                self.assertLess(monotonic()-started,0.5)
                self.assertEqual(skipped,1)
                self.assertTrue(limited)
        finally:
            release.set()

if __name__=='__main__': unittest.main()
