import json
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import app as radar
import comparisons as comp
import news_sources as news
import source_catalog as catalog
import web_discovery as web


class CatalogSearchTest(unittest.TestCase):
    def setUp(self):
        self.end = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        self.start = self.end - timedelta(days=7)
        self.terms = ('Alejandro Toro', 'David Alejandro Toro Ramírez')
        comp.collect.cache_clear()
        news.focused_bytes.cache_clear()
        web.google_article.cache_clear()

    def test_catalog_preserves_all_38_sources_and_the_requested_section(self):
        self.assertEqual(len(catalog.SOURCES), 38)
        self.assertEqual(len({s.id for s in catalog.SOURCES}), 38)
        self.assertEqual(Counter(s.group for s in catalog.SOURCES), {
            'Internacionales': 15, 'Regionales': 8, 'Política e investigación': 15})
        source = catalog.matching_source('https://www.elespectador.com/colombia-20/paz/nota')
        self.assertEqual(source.id, 'colombia20')
        for url in ('https://www.elespectador.com/deportes/nota',
                    'https://www.elespectador.com/colombia-200/nota',
                    'https://elespectador.com.evil.example/colombia-20/nota'):
            self.assertIsNone(catalog.matching_source(url))

    def test_both_apis_search_the_whole_catalog_with_names_dates_and_zone(self):
        client = radar.app.test_client()
        member = next(m for m in comp.members().values() if m['search_name'] == 'Alejandro Toro')
        other = next(mid for mid in comp.members() if mid != member['id'])
        for days, zone in ((1, 'Antioquia'), (90, '')):
            with patch.object(news, 'google_news', return_value=([], 0, False)), \
                 patch.object(web, 'duckduckgo_web', return_value=([], 0, False)), \
                 patch.object(news, 'focused_news', return_value=([], 0, False)) as google, \
                 patch.object(web, 'focused_web', return_value=([], 0, False)) as duck:
                response = client.post('/api/report', json={'name':self.terms[0], 'aliases':self.terms[1], 'days':days, 'territory':zone})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['web_coverage']['catalog']['configured'], 38)
                self.assertEqual(response.json['web_coverage']['catalog']['searchable'], 38)
                self.assert_whole_catalog(google, duck, self.terms, zone, days)
                google.reset_mock(); duck.reset_mock()
                meta = client.post('/api/compare/start', json={'member_ids':[member['id'],other], 'days':days, 'territory':zone}).json
                result = client.post('/api/compare/member', json={'member_id':member['id'], 'days':days, 'territory':zone, 'end_time':meta['end_time']})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json['sources']['Web']['catalog']['configured'], 38)
                expected = comp.query_for(member, zone).terms
                self.assert_whole_catalog(google, duck, expected, zone, days)
                self.assertTrue(all(call.args[2] == comp.date(meta['start_time']) and call.args[3] == comp.date(meta['end_time']) for call in google.call_args_list))

    def assert_whole_catalog(self, google, duck, terms, zone, days):
        for term in terms:
            calls = [call for call in google.call_args_list if call.args[0] == term]
            self.assertCountEqual([s.id for call in calls for s in call.args[4]], [s.id for s in catalog.SOURCES])
        self.assertCountEqual([s.id for call in duck.call_args_list for s in call.args[4]], [s.id for s in catalog.SOURCES])
        for call in google.call_args_list + duck.call_args_list:
            self.assertEqual(call.args[1], zone)
            self.assertEqual(call.args[3] - call.args[2], timedelta(days=days))

    def test_targeted_news_uses_independent_names_and_discards_wrong_publishers_and_dates(self):
        entries = ''
        for title, host, date in (('Dentro', 'vanguardia.com', self.end-timedelta(hours=23)),
                                  ('Fuera', 'vanguardia.com', self.end-timedelta(hours=25)),
                                  ('Ajeno', 'another.example', self.end-timedelta(hours=2))):
            entries += f'<item><title>{title}</title><link>https://{host}/{title}</link><pubDate>{date.isoformat()}</pubDate><source url="https://{host}">{host}</source></item>'
        xml = ('<rss version="2.0"><channel>' + entries + '</channel></rss>').encode()
        batch = catalog.BATCHES[4]
        with patch.object(news, 'focused_bytes', return_value=xml) as get:
            items, _, _ = news.focused_news(self.terms[0], 'Antioquia', self.end-timedelta(days=1), self.end, batch)
        query = parse_qs(urlsplit(get.call_args.args[0]).query)['q'][0]
        self.assertIn('"Alejandro Toro" "Antioquia"', query)
        self.assertIn('after:2026-09-07 before:2026-09-10', query)
        self.assertTrue(all('site:' + s.scope in query for s in batch))
        self.assertEqual([item['title'] for item in items], ['Dentro'])

    def test_web_verification_requires_name_zone_and_original_date_and_section(self):
        candidate = {'url':'https://www.elespectador.com/colombia-20/nota', 'title':'Nota', 'engine':'DuckDuckGo fuentes', 'catalog_source':'colombia20'}
        def html(body, published='2026-09-09T11:00:00Z'):
            return '<script type="application/ld+json">' + json.dumps({'@type':'NewsArticle', 'headline':'Nota', 'datePublished':published, 'articleBody':body}) + '</script>'
        for body, zone, expected in (
                ('Alejandro Toro habló en Antioquia', 'Antioquia', True),
                ('Alejandro Toro habló en Bogotá', 'Antioquia', False),
                ('Alejandro Toros habló en Antioquia', 'Antioquia', False),
                ('Alejandro Toro habló en Bogotá', '', True)):
            with patch.object(web, 'cached_page', return_value=(candidate['url'], html(body))):
                item, _ = web.verify_page(candidate, self.terms, self.start, self.end, zone)
            self.assertEqual(item is not None, expected)
        with patch.object(web, 'cached_page', return_value=('https://www.elespectador.com/deportes/nota', html('Alejandro Toro Antioquia'))):
            self.assertIsNone(web.verify_page(candidate, self.terms, self.start, self.end, 'Antioquia')[0])
        with patch.object(web, 'cached_page', return_value=(candidate['url'], html('Alejandro Toro Antioquia', '2026-07-01T00:00:00Z'))):
            self.assertIsNone(web.verify_page(candidate, self.terms, self.start, self.end, 'Antioquia')[0])

    def test_extra_source_adds_a_mention_without_losing_general_or_duplicating(self):
        def item(title, url, domain):
            return dict(title=title, url=url, link=url, published='2026-09-09T11:00:00Z', source=domain, publisher_domain=domain, discovery='google_news')
        original = item('General', 'https://other.example/nota', 'other.example')
        extra = item('Nueva', 'https://news.google.com/rss/articles/123', 'elespectador.com')
        direct = dict(extra, url='https://www.elespectador.com/colombia-20/nota', discovery='DuckDuckGo fuentes')
        candidate = dict(direct, engine='DuckDuckGo fuentes', catalog_source='colombia20', candidate=True)
        with patch.object(news, 'google_news', return_value=([original, extra],0,False)), \
             patch.object(web, 'duckduckgo_web', return_value=([],0,False)), \
             patch.object(news, 'focused_news', return_value=([extra],0,False)), \
             patch.object(web, 'focused_web', return_value=([candidate],0,False)), \
             patch.object(web, 'verify_candidates', return_value=([direct],0,False)):
            result = news.search_news(news.NewsQuery(self.terms, 'Colombia'), self.start, self.end)
        self.assertEqual(result['count'], 2)
        self.assertCountEqual([i['url'] for i in result['items']], [original['url'], direct['url']])

    def test_focused_web_filters_wrong_domains_and_preserves_all_terms_and_zone(self):
        with patch.object(web, 'web_query', return_value=([
                {'url':'https://vanguardia.com/politica/nota', 'title':'Noticia'},
                {'url':'https://vanguardia.com.evil.example/nota', 'title':'Falsa'},
                {'url':'https://facebook.com/post', 'title':'Social'}], False)) as request:
            items, _, _ = web.focused_web(self.terms, 'Santander', self.start, self.end, catalog.BATCHES[4])
        q = request.call_args.args[0]
        self.assertTrue(all('"' + term + '"' in q for term in self.terms))
        self.assertIn('"Santander"', q)
        self.assertEqual([item['catalog_source'] for item in items], ['vanguardia'])

    def test_outage_is_partial_and_never_claims_all_sources_were_accessible(self):
        with patch.object(news, 'google_news', return_value=([],0,False)), \
             patch.object(web, 'duckduckgo_web', return_value=([],0,False)), \
             patch.object(news, 'focused_news', side_effect=news.requests.Timeout), \
             patch.object(web, 'focused_web', side_effect=ValueError('challenge')):
            result = news.search_news(news.NewsQuery(self.terms, 'Colombia'), self.start, self.end)
        self.assertTrue(result['limited'])
        self.assertEqual(result['catalog']['configured'], 38)
        self.assertEqual(result['catalog']['searchable'], 0)
        self.assertIn('Consulta parcial', result['message'])

    def test_source_catalog_is_visible_and_matches_the_search_configuration(self):
        html = radar.app.test_client().get('/').get_data(as_text=True)
        self.assertIn('Ver las 38 fuentes adicionales', html)
        for source in catalog.SOURCES:
            self.assertIn(source.url, html)

    def test_google_candidates_must_match_the_original_article_not_the_search_snippet(self):
        candidate = {'url':'https://news.google.com/rss/articles/CBMiExample',
                     'title':'Alejandro Toro en Colombia', 'summary':'Alejandro Toro Colombia',
                     'engine':'Google Noticias', 'catalog_source':'infobae'}
        original = 'https://www.infobae.com/colombia/2026/09/09/nota/'
        def html(body):
            return '<meta property="article:published_time" content="2026-09-09T11:00:00Z"><article>' + body + '</article>'
        for body, accepted in (('Préstamo para empresas hondureñas', False),
                               ('David Toro informa sobre fútbol en Croacia', False),
                               ('Alejandro Toro presenta un proyecto en Colombia', True)):
            with patch.object(web, 'google_article', return_value=(original, html(body))):
                item, _ = web.verify_page(candidate, self.terms, self.start, self.end, 'Colombia')
            self.assertEqual(item is not None, accepted)
        with patch.object(web, 'google_article', return_value=('https://www.infobae.com/deportes/nota/', html('Alejandro Toro Colombia'))):
            self.assertIsNone(web.verify_page(candidate, self.terms, self.start, self.end, 'Colombia')[0])

    def test_google_public_link_resolution_preserves_original_url_and_stops_on_challenges(self):
        token = 'CBMiAAAAAAAAAAAA'
        url = 'https://news.google.com/rss/articles/' + token
        original = 'https://confidencialnoticias.com/politica/nota/'
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [(")]}'\n\n123\n" + json.dumps([
            ['wrb.fr', 'Fbv4je', json.dumps(['garturlres', original])]])).encode()]
        google_html = '<div data-n-a-ts="123" data-n-a-sg="public-signature"></div>'
        with patch.object(web, 'cached_page', side_effect=[('https://news.google.com/articles/' + token, google_html), (original, '<article>Original</article>')]), \
             patch.object(web.requests, 'post', return_value=response) as post:
            self.assertEqual(web.google_article(url, 0), (original, '<article>Original</article>'))
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        with patch.object(web, 'cached_page', return_value=(url, '<form>Interactive challenge</form>')), \
             patch.object(web.requests, 'post') as post:
            with self.assertRaises(ValueError):
                web.google_article(url, 1)
            post.assert_not_called()

    def test_google_link_metadata_after_large_scripts_is_read_without_unbounded_articles(self):
        raw = ('<script>' + ' ' * 650_000 + '</script><div data-n-a-ts="123" data-n-a-sg="signature"></div>').encode()
        response = MagicMock(status=200, headers={'Content-Type':'text/html'})
        response.read.side_effect = lambda size, **kwargs: raw[:size]
        pool = MagicMock()
        pool.urlopen.return_value = response
        with patch.object(web.socket, 'getaddrinfo', return_value=[(2,1,6,'',('93.184.216.34',443))]), \
             patch.object(web.urllib3, 'HTTPSConnectionPool', return_value=pool):
            _, google_html = web.cached_page('https://news.google.com/articles/large-fixture', 0)
            _, article_html = web.cached_page('https://public.example/large-fixture', 0)
        self.assertEqual(web.GoogleLinkPage(google_html).signature, 'signature')
        self.assertLess(len(article_html), len(raw))
        self.assertLess(len(google_html), 2_000_000)


if __name__ == '__main__':
    unittest.main()
