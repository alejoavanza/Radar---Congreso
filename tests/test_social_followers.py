"""Provider replies are synthetic fixtures only; never deployed as measurements."""
from datetime import datetime, timedelta, timezone
import json
import os
import unittest
from unittest.mock import patch

from app import app
import follower_store as store
import social_followers as sf

CHANNEL = 'UC' + 'a' * 22
MEMBER = {'id': 'test-only-ana', 'display_name': 'Prueba, Ana', 'full_name': 'Ana Prueba',
          'profile_url': 'https://www.camara.gov.co/representantes/test-only-ana/'}


class Reply:
    def __init__(self, body, status=200, content_type='application/json'):
        self.raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.status_code = status
        self.headers = {'Content-Type': content_type}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_content(self, size): yield self.raw


def account(**extra):
    return dict(member_id=MEMBER['id'], platform='youtube', account_id=CHANNEL,
                status='reviewed', evidence_url=MEMBER['profile_url'],
                reviewed_at=sf.iso(sf.now()), **extra)


class FollowersTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start(); self.addCleanup(self.env.stop)
        self.people = patch('social_followers.members', return_value={MEMBER['id']: MEMBER}); self.people.start(); self.addCleanup(self.people.stop)
        self.client = app.test_client()
        sf._CACHE.clear(); sf.discover_links.cache_clear()

    def call(self):
        return self.client.post('/api/social/followers', json={'member_id': MEMBER['id']})

    def test_public_screen_has_no_demo_or_legacy_exporter(self):
        text = self.client.get('/').get_data(as_text=True)
        self.assertIn('followers-search', text)
        self.assertNotIn('social-piece-example', text)
        self.assertNotIn('/static/social-export.js', text)
        self.assertNotIn('/static/social-history.js', text)

    def test_no_credentials_no_external_calls_no_fabricated_values(self):
        with patch('social_followers.requests.get') as request:
            response = self.call()
        request.assert_not_called()
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertFalse(data['simulated_data'])
        self.assertTrue(all(item['followers'] is None for item in data['results']))
        self.assertFalse(data['history_configured'])
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_status_exposes_no_credentials_or_false_active_claim(self):
        os.environ['YOUTUBE_API_KEY'] = 'test-secret-do-not-expose'
        response = self.client.get('/api/social/status')
        self.assertTrue(response.json['youtube_configured'])
        self.assertFalse(response.json['automatic_collection'])
        self.assertNotIn('test-secret', response.get_data(as_text=True))

    def test_unknown_identity_and_oversized_input_are_rejected(self):
        with patch('social_followers.requests.get') as request:
            self.assertEqual(self.client.post('/api/social/followers', json={'member_id': 'unknown'}).status_code, 400)
            self.assertEqual(self.client.post('/api/social/discover', json={'member_id': 'unknown'}).status_code, 400)
            self.assertEqual(self.client.post('/api/social/followers', json={'member_id': 'a' * 5000}).status_code, 413)
        request.assert_not_called()

    def test_key_does_not_turn_unreviewed_link_into_verified_account(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        with patch('social_followers.registry', return_value=[]), patch('social_followers.requests.get') as request:
            youtube = next(item for item in self.call().json['results'] if item['platform'] == 'youtube')
        request.assert_not_called(); self.assertEqual(youtube['status'], 'account_pending')

    def test_unreviewed_expired_duplicate_or_invalid_registry_is_rejected(self):
        good = account()
        for records in [[dict(good, status='candidate')], [dict(good, reviewed_at=sf.iso(sf.now()-timedelta(days=31)))],
                        [dict(good, account_id='a handle')], [good, good], [dict(good, evidence_url='javascript:alert(1)')]]:
            with patch('social_followers.registry', return_value=records):
                self.assertEqual(sf.reviewed_accounts(MEMBER['id']), {})
        with patch('social_followers.registry', return_value=[good]):
            self.assertEqual(sf.reviewed_accounts(MEMBER['id'])['youtube']['account_id'], CHANNEL)

    def test_zero_is_a_measured_value_and_cache_preserves_timestamp(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        reply = Reply({'items': [{'id': CHANNEL, 'statistics': {'subscriberCount': '0', 'hiddenSubscriberCount': False}}]})
        with patch('social_followers.requests.get', return_value=reply) as request:
            first = sf.youtube_observation(account()); second = sf.youtube_observation(account())
        self.assertEqual(first['followers'], 0)
        self.assertEqual(first['observed_at'], second['observed_at'])
        self.assertTrue(second['reused']); self.assertEqual(request.call_count, 1)
        self.assertNotIn('key', request.call_args.kwargs['params'])
        self.assertEqual(request.call_args.kwargs['headers']['X-Goog-Api-Key'], 'fixture-key')
        self.assertFalse(request.call_args.kwargs['allow_redirects'])

    def test_missing_hidden_malformed_and_wrong_channel_are_not_zero(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        for stats, channel in [({}, CHANNEL), ({'subscriberCount': '5', 'hiddenSubscriberCount': True}, CHANNEL),
                               ({'subscriberCount': '-1'}, CHANNEL), ({'subscriberCount': True}, CHANNEL),
                               ({'subscriberCount': '100'}, 'different')]:
            sf._CACHE.clear()
            with patch('social_followers.requests.get', return_value=Reply({'items': [{'id': channel, 'statistics': stats}]})):
                result = sf.youtube_observation(account())
            self.assertIsNone(result['followers'])

    def test_provider_errors_do_not_expose_body_or_secret(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        for code in [301, 401, 403, 429, 500]:
            sf._CACHE.clear()
            with patch('social_followers.requests.get', return_value=Reply({'secret': 'private-provider-body'}, code)):
                result = sf.youtube_observation(account())
            self.assertIsNone(result['followers']); self.assertNotIn('private-provider-body', json.dumps(result))

    def test_response_from_same_channel_never_changes_member_identity(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        reply = Reply({'items': [{'id': CHANNEL, 'statistics': {'subscriberCount': '12300'}}]})
        with patch('social_followers.requests.get', return_value=reply):
            sf.youtube_observation(account())
            other = sf.youtube_observation(dict(account(), member_id='test-only-other'))
        self.assertEqual(other['member_id'], 'test-only-other')

    def test_storage_failure_retains_current_real_count_but_not_false_persistence(self):
        os.environ['YOUTUBE_API_KEY'] = 'fixture-key'
        reply = Reply({'items': [{'id': CHANNEL, 'statistics': {'subscriberCount': '12000'}}]})
        with patch('social_followers.registry', return_value=[account()]), patch('social_followers.requests.get', return_value=reply), \
             patch('follower_store.configured', return_value=True), patch('follower_store.save', side_effect=store.StoreUnavailable('test')):
            item = next(item for item in self.call().json['results'] if item['platform'] == 'youtube')
        self.assertEqual(item['followers'], 12000); self.assertFalse(item['persisted'])
        self.assertEqual(item['history_status'], 'unavailable'); self.assertIsNone(item['growth'])

    def test_candidates_never_supply_counts_or_approve_identity(self):
        html = '<a href="https://www.instagram.com/institution/">Institution</a><a href="https://x.com/intent/post">Share</a>'
        with patch('social_followers.requests.get', return_value=Reply(html, content_type='text/html')) as get:
            data = self.client.post('/api/social/discover', json={'member_id': MEMBER['id'], 'url': 'http://127.0.0.1'}).json
        self.assertEqual(get.call_args.args[0], MEMBER['profile_url'])
        self.assertEqual(len(data['candidates']), 1)
        self.assertEqual(data['candidates'][0]['status'], 'candidate'); self.assertIsNone(data['candidates'][0]['followers'])

    def test_discovery_refuses_arbitrary_hosts_and_social_subdomains(self):
        with patch('social_followers.requests.get') as get:
            self.assertEqual(sf.discover_links('https://127.0.0.1/x', 1), [])
            self.assertEqual(sf.discover_links('https://www.camara.gov.co.evil.test/x', 1), [])
        get.assert_not_called()
        self.assertIsNone(sf.account_link('https://instagram.com.evil.test/person'))
        self.assertIsNone(sf.account_link('https://youtube.com/watch?v=x'))
        self.assertIsNone(sf.account_link('https://x.com/person/status/123'))

    def test_storage_configuration_requires_a_valid_https_project(self):
        self.assertFalse(store.configured())
        with patch.dict(os.environ, {'SOCIAL_SUPABASE_URL': 'https://project.supabase.co', 'SOCIAL_SUPABASE_SERVICE_KEY': 'test-only'}):
            self.assertTrue(store.configured())
        with patch.dict(os.environ, {'SOCIAL_SUPABASE_URL': 'http://127.0.0.1', 'SOCIAL_SUPABASE_SERVICE_KEY': 'test-only'}):
            self.assertFalse(store.configured())

    def test_history_filters_expiry_foreign_id_future_and_nonmeasured_values(self):
        stamp = sf.now()
        valid = {'member_id': MEMBER['id'], 'platform': 'youtube', 'account_id': CHANNEL,
                 'followers': 0, 'source_kind': 'official_api', 'observed_at': sf.iso(stamp-timedelta(days=1)),
                 'expires_at': sf.iso(stamp+timedelta(days=1))}
        invalid = [dict(valid, followers=None), dict(valid, member_id='other'), dict(valid, source_kind='user_import'),
                   dict(valid, observed_at=sf.iso(stamp-timedelta(days=30))), dict(valid, observed_at=sf.iso(stamp+timedelta(days=1))),
                   dict(valid, expires_at=sf.iso(stamp-timedelta(seconds=1)))]
        with patch('follower_store.configured', return_value=True), patch('follower_store.rpc', return_value=[valid]+invalid):
            self.assertEqual(store.history(MEMBER['id'], 'youtube', CHANNEL), [valid])


if __name__ == '__main__': unittest.main()
