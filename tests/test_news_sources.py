import search_state
import json
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import app as radar
import news_sources as news
import web_discovery as web

EMPTY = b'<rss version="2.0"><channel><title>Resultados</title></channel></rss>'


def rss(title, link, published=None, source='Medio'):
    date = '<pubDate>' + format_datetime(published) + '</pubDate>' if published else ''
    return ('<rss version="2.0"><channel><item><title>' + title + '</title><link>' + link +
            '</link>' + date + '<source url="https://regional.example">' + source +
            '</source><description>María Ejemplo en Colombia</description></item></channel></rss>').encode()


def page(title, date=None, author='María Ejemplo'):
    data = {'@type':'NewsArticle', 'headline':title, 'author':{'name':author}, 'articleBody':'Colombia'}
    if date:
        data['datePublished'] = date
    return '<meta property="og:site_name" content="Medio Regional"><script type="application/ld+json">' + json.dumps(data) + '</script>'


class BroadSearchTest(unittest.TestCase):
    def setUp(self):
        search_state.clear()
        batches = patch.object(news, "BATCHES", ())
        batches.start()
        self.addCleanup(batches.stop)
        news.cached_source.cache_clear()
        web.cached_page.cache_clear()
        self.end = datetime(2026, 9, 7, 5, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=7)
        self.query = news.NewsQuery(('María Ejemplo', 'María Lucía Ejemplo Ramírez'), 'Colombia')

    def test_web_pages_are_discovered_for_any_person_when_google_is_empty(self):
        first, second = 'https://regional.example/columna', 'https://revista.example/nota'
        def index(url):
            if url.startswith('https://html.duckduckgo.com/html/?'):
                return (f'<a class="result__a" href="{first}">Columna de opinión</a>'
                        f'<a class="result__a" href="{second}">Otra noticia</a>'
                        '<a class="result__a" href="https://facebook.com/post">Red social</a>').encode()
            raise AssertionError('No hardcoded publishers: ' + url)
        def article(url, bucket):
            return url, page('Columna de opinión' if url == first else 'Otra noticia', '2026-09-06T02:00:00-05:00')
        with patch.object(news, 'google_news', return_value=([], 0, False)), \
             patch.object(web, 'source_bytes', side_effect=index), patch.object(web, 'cached_page', side_effect=article):
            result = news.search_news(self.query, self.start, self.end)
        self.assertEqual(result['count'], 2)
        self.assertCountEqual([item['url'] for item in result['items']], [first,second])
        self.assertCountEqual([item['discovery'] for item in result['items']], ['DuckDuckGo web','DuckDuckGo web'])
        self.assertTrue(all(item['published'] == '2026-09-06T07:00:00Z' for item in result['items']))
        self.assertNotIn('La Chiva', result['message'])
        self.assertNotIn('Confidencial', result['message'])

    def test_search_challenge_cannot_be_reported_as_an_empty_search(self):
        with patch.object(web, 'source_bytes', return_value=b'<form id="challenge-form">Challenge</form>'):
            with self.assertRaises(ValueError):
                web.duckduckgo_web(self.query.terms, 'Colombia', self.start, self.end)

    def test_explicit_publication_time_is_supported_but_updated_time_is_not(self):
        candidate = {'url':'https://regional.example/a','title':'María Ejemplo','engine':'DuckDuckGo web'}
        for field in ('<time class="entry-date published" datetime="2026-09-06T12:00:00Z"></time>',
                      '<meta itemprop="datePublished" content="2026-09-06T12:00:00Z">'):
            with patch.object(web, 'cached_page', return_value=(candidate['url'], field + '<article>María Ejemplo</article>')):
                self.assertIsNotNone(web._verify_page(candidate, self.query.terms, self.start, self.end)[0])
        with patch.object(web, 'cached_page', return_value=(candidate['url'], '<time class="updated" datetime="2026-09-06T12:00:00Z"></time>')):
            self.assertIsNone(web._verify_page(candidate, self.query.terms, self.start, self.end)[0])

    def test_name_variants_remain_independent_on_google(self):
        def response(url, **kwargs):
            from urllib.parse import urlsplit, parse_qs
            query = parse_qs(urlsplit(url).query)['q'][0]
            self.assertNotIn(' OR ', query)
            self.assertIn('"Colombia"', query)
            return Mock(content=rss('Mención', 'https://regional.example/nota', self.end-timedelta(days=2))
                        if query.startswith('"María Ejemplo"') else EMPTY)
        with patch.object(news.requests, 'get', side_effect=response), \
             patch.object(web, 'duckduckgo_web', return_value=([],0,False)), \
             patch.object(web, 'cached_page', return_value=('https://regional.example/nota', page('Mención', '2026-09-05T05:00:00Z'))):
            result = news.search_news(self.query,self.start,self.end)
        self.assertEqual(result['count'],1)

    def test_publication_date_is_required_and_updates_or_index_dates_cannot_replace_it(self):
        candidate = {'url':'https://regional.example/a','title':'María Ejemplo','engine':'DuckDuckGo web','seendate':'20260906T120000Z'}
        for html in (page('María Ejemplo'), page('María Ejemplo','2026-08-01T00:00:00Z') + '<meta property="article:modified_time" content="2026-09-06T12:00:00Z">'):
            with patch.object(web,'cached_page',return_value=(candidate['url'],html)):
                self.assertIsNone(web._verify_page(candidate,self.query.terms,self.start,self.end)[0])
        with patch.object(web,'cached_page',return_value=(candidate['url'],page('María Ejemplo','2026-09-06T02:00:00Z'))):
            self.assertIsNone(web._verify_page(candidate,self.query.terms,self.end-timedelta(days=1),self.end)[0])

    def test_date_from_an_unrelated_schema_object_cannot_count_a_page(self):
        html = '<script type="application/ld+json">' + json.dumps({'@type':'Organization','datePublished':'2026-09-06T12:00:00Z','name':'María Ejemplo'}) + '</script>'
        candidate = {'url':'https://regional.example/a','title':'María Ejemplo','engine':'DuckDuckGo web'}
        with patch.object(web,'cached_page',return_value=(candidate['url'],html)):
            self.assertIsNone(web._verify_page(candidate,self.query.terms,self.start,self.end)[0])

    def test_same_story_across_indexes_uses_direct_link_once(self):
        article = {'title':'Una mención','url':'https://regional.example/a','link':'https://regional.example/a',
                   'source':'Medio Regional','publisher_domain':'regional.example','published':'2026-09-06T12:00:00Z','discovery':'DuckDuckGo web'}
        google = dict(article,url='https://news.google.com/rss/articles/example',discovery='google_news')
        candidate = {'url':article['url'],'title':article['title'],'engine':'DuckDuckGo web','candidate':True}
        with patch.object(news,'google_news',return_value=([google],0,False)), \
             patch.object(web,'duckduckgo_web',return_value=([candidate],0,False)), \
             patch.object(web,'verify_candidates',return_value=([article],0,False)):
            result = news.search_news(self.query,self.start,self.end)
        self.assertEqual(result['count'],1)
        self.assertEqual(result['items'][0]['url'],article['url'])

    def test_outages_do_not_become_a_complete_zero(self):
        with patch.object(news,'get_bytes',side_effect=news.requests.Timeout):
            result = news.search_news(self.query,self.start,self.end)
        self.assertIsNone(result['count'])
        with patch.object(news,'get_bytes',side_effect=news.requests.Timeout), patch.object(news,'google_news',return_value=([],0,False)):
            result = news.search_news(self.query,self.start,self.end)
        self.assertIsNone(result['count'])
        self.assertTrue(result['limited'])
        self.assertIn('fallida',result['message'])

    def test_social_results_are_excluded_from_all_indexes(self):
        self.assertEqual(web.candidates([{'url':'https://www.facebook.com/post','title':'María Ejemplo'}],'DuckDuckGo web'),[])
        self.assertEqual(news.feed_items(rss('Social','https://news.google.com/rss/articles/post',self.end-timedelta(days=2),'facebook.com'),self.start,self.end)[0],[])
        self.assertTrue(news.social_result('https://news.google.com/article',{'href':'https://www.instagram.com'}))
        self.assertFalse(news.social_result('https://regional.example/noticia-sobre-facebook',{}))
        self.assertFalse(news.matches('María Ejemplos', ['María Ejemplo']))

    def test_private_or_social_targets_are_rejected_before_connecting(self):
        for url in ('http://127.0.0.1/','http://169.254.169.254/metadata','https://www.facebook.com/post'):
            with patch.object(web.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',80))]), patch.object(web.urllib3,'HTTPConnectionPool') as pool:
                with self.assertRaises(ValueError):
                    web.cached_page(url,0)
                pool.assert_not_called()

    def test_validated_dns_address_is_pinned_and_private_redirect_is_rejected(self):
        response = Mock(status=302,headers={'Location':'http://127.0.0.1/private'})
        pool = Mock(); pool.urlopen.return_value=response
        def resolve(host,port,**kwargs):
            return [(2,1,6,'',('93.184.216.34' if host=='regional.example' else '127.0.0.1',port))]
        with patch.object(web.socket,'getaddrinfo',side_effect=resolve) as dns, patch.object(web.urllib3,'HTTPSConnectionPool',return_value=pool) as constructor:
            with self.assertRaises(ValueError):
                web.cached_page('https://regional.example/a',0)
        self.assertEqual(constructor.call_args.args[0],'93.184.216.34')
        self.assertEqual(constructor.call_args.kwargs['assert_hostname'],'regional.example')
        self.assertEqual(pool.urlopen.call_count,1)
        self.assertEqual(dns.call_count,2)

    def test_zero_message_and_total_outage_api_behavior(self):
        with patch.object(radar,'fetch_news',return_value=([],None,{'status':'available','message':'Cobertura parcial'})):
            response=radar.app.test_client().post('/api/report',json={'name':'Persona','days':7})
        self.assertEqual(response.status_code,200)
        self.assertIn('No se encontraron',response.json['summary'])
        with patch.object(radar,'fetch_news',return_value=([],'No disponible',{})):
            self.assertEqual(radar.app.test_client().post('/api/report',json={'name':'Persona'}).status_code,502)

if __name__=='__main__':
    unittest.main()
