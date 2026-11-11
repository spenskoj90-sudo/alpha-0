"""Offline protocol tests; generated JWT-shaped fixtures are not credentials."""
import base64
import contextlib
import io
import json
import unittest

import infisical_oidc_lifecycle as runner


def token(chain, now=1000, ttl=600):
    def b64(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
    return b64({'alg': 'fixture'}) + '.' + b64({
        'iat': now, 'exp': now + ttl, 'identityId': runner.IDENTITY,
        'jti': chain,
    }) + '.fixture'


class Clock:
    def __init__(self):
        self.value = 1000
    def time(self):
        return self.value
    def monotonic(self):
        return self.value - 1000
    def sleep(self, seconds):
        self.value += seconds


class Provider:
    """Models network only. Runner owns ordering, deadlines and classifications."""
    def __init__(self, clock):
        self.clock = clock
        self.logins = 0
        self.calls = []
        self.expired_status = 401
        self.revoked_status = 401
        self.revoke_status = 200
        self.revoked = set()
        self.renew_chain = None
        self.delay_revoke = 0
        self.rotate = False
        self.revoke_chain = True
        self.revoked_chains = set()
    def __call__(self, path, payload):
        self.calls.append((path, dict(payload)))
        if path == '/oidc-auth/login':
            self.logins += 1
            value = token(str(self.logins), int(self.clock.time()), 300 if self.rotate else 600)
            return 200, {'accessToken': value, 'expiresIn': 300 if self.rotate else 600, 'accessTokenMaxTTL': 600}
        value = payload['accessToken']
        claims = runner.decode_claims(value)
        if path == '/token/revoke':
            self.clock.value += self.delay_revoke
            if self.revoke_status == 200:
                self.revoked.add(value)
                if self.revoke_chain:
                    self.revoked_chains.add(claims['jti'])
            return self.revoke_status, {}
        if value in self.revoked or claims['jti'] in self.revoked_chains:
            return self.revoked_status, {}
        if self.clock.time() > claims['exp']:
            return self.expired_status, {}
        if self.rotate:
            value = token(claims['jti'], int(claims['iat']) + 1, 599)
        if self.renew_chain:
            value = token(self.renew_chain, int(claims['iat']))
        return 200, {'accessToken': value, 'expiresIn': runner.decode_claims(value)['exp'] - self.clock.time(),
                     'accessTokenMaxTTL': 600}


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.api = Provider(self.clock)
    def run_packet(self):
        return runner.run_lifecycle(self.api, lambda: 'fixture-github-jwt', self.clock)
    def test_two_independent_chains_and_expiry_before_self_revoke(self):
        self.assertEqual(self.run_packet(), ('expiry', 'self-revocation'))
        self.assertEqual(self.api.logins, 2)
        self.assertEqual([p for p, _ in self.api.calls], [
            '/oidc-auth/login', '/token/renew', '/token/renew',
            '/oidc-auth/login', '/token/renew', '/token/revoke', '/token/renew'])
        self.assertGreaterEqual(self.clock.time(), 1605)
        self.assertLess(self.clock.time(), 1635)
    def test_expiry_requires_401_not_resource_permission_denial(self):
        self.api.expired_status = 403
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
        self.assertEqual(self.api.logins, 1)
    def test_expired_token_still_accepted_is_failure(self):
        self.api.expired_status = 200
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
    def test_revoke_200_without_subsequent_401_is_failure(self):
        self.api.revoked_status = 200
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
    def test_natural_expiry_cannot_be_counted_as_revocation(self):
        self.api.delay_revoke = 601
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
    def test_failed_revoke_does_not_continue_as_pass(self):
        self.api.revoke_status = 403
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
    def test_renewal_must_not_switch_token_chain(self):
        self.api.renew_chain = 'other-chain'
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
        self.assertEqual(self.clock.time(), 1000)
    def test_rotated_token_is_probed_and_last_expiry_is_observed(self):
        self.api.rotate = True
        self.assertEqual(self.run_packet(), ('expiry', 'self-revocation'))
        self.assertGreaterEqual(self.clock.time(), 1605)
        renewal_tokens = [body['accessToken'] for path, body in self.api.calls if path == '/token/renew']
        self.assertIn(token('1', 1001, 599), renewal_tokens)
        self.assertIn(token('2', 1606, 599), renewal_tokens)
    def test_revoke_must_invalidate_original_and_rotated_credential(self):
        self.api.rotate = True
        self.api.revoke_chain = False
        with self.assertRaises(runner.CanaryFailure):
            self.run_packet()
    def test_protocol_does_not_print_credentials(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.run_packet()
        self.assertEqual(output.getvalue(), '')
    def test_ttl_validation_rejects_bool_nan_oversized_and_future(self):
        for ttl in (True, float('nan'), 601, 0):
            with self.subTest(ttl=ttl), self.assertRaises(runner.CanaryFailure):
                runner.validate_token({'accessToken': token('a'), 'expiresIn': ttl}, 1000)
        with self.assertRaises(runner.CanaryFailure):
            runner.validate_token({'accessToken': token('a', 2000), 'expiresIn': 600}, 1000)
    def test_renewed_max_ttl_cannot_exceed_policy(self):
        original = runner.validate_token({'accessToken': token('a'), 'expiresIn': 600}, 1000)
        with self.assertRaises(runner.CanaryFailure):
            runner.validate_renewal({'accessToken': token('a'), 'expiresIn': 600,
                                     'accessTokenMaxTTL': 601}, original, 1000)


class BoundaryTest(unittest.TestCase):
    def test_wrong_workflow_requires_explicit_provider_denial(self):
        for status in (401, 403):
            self.assertEqual(runner.run_wrong_workflow(lambda p, b: (status, {}), lambda: 'fixture'),
                             'wrong-workflow')
        for status in (200, 201, 302, 404, 429, 500):
            with self.subTest(status=status), self.assertRaises(runner.CanaryFailure):
                runner.run_wrong_workflow(lambda p, b: (status, {}), lambda: 'fixture')
    def test_unexpected_response_body_is_never_read(self):
        class Response:
            status = 403
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                raise AssertionError('must not read error body')
        class Opener:
            def open(self, request, timeout):
                return Response()
        self.assertEqual(runner.request_json(Opener(), None), (403, {}))
    def test_network_exception_details_are_suppressed(self):
        class Opener:
            def open(self, request, timeout):
                raise RuntimeError('fixture-sensitive-detail')
        with self.assertRaises(runner.CanaryFailure) as caught:
            runner.request_json(Opener(), None)
        self.assertNotIn('fixture-sensitive-detail', str(caught.exception))
    def test_oversized_response_is_rejected(self):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                return b'x' * size
        class Opener:
            def open(self, request, timeout):
                return Response()
        with self.assertRaises(runner.CanaryFailure):
            runner.request_json(Opener(), None)
    def test_unknown_api_path_cannot_send_credentials(self):
        with self.assertRaises(runner.CanaryFailure):
            runner.provider_api('/secrets', {'accessToken': 'fixture'})
    def test_redirect_does_not_forward_credentials(self):
        self.assertIsNone(runner.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example'))
    def test_non_main_environment_cannot_request_github_token(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(runner.CanaryFailure):
            runner.github_jwt('lifecycle')
    def test_malformed_claims_do_not_reveal_input(self):
        with self.assertRaises(runner.CanaryFailure) as caught:
            runner.decode_claims('fixture-sensitive-detail')
        self.assertNotIn('fixture-sensitive-detail', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
