"""Manual NoAccess token-lifecycle canary; never prints credentials/responses.

Local claim parsing is a guard, not signature verification. GitHub's runner
supplies its JWT over TLS and Infisical verifies it during the exchange.
"""
import base64
from dataclasses import dataclass
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IDENTITY = 'dcf17c97-db32-4b0f-b8e5-4eab29b5e183'
AUDIENCE = 'https://github.com/spenskoj90-sudo'
WORKFLOW = 'spenskoj90-sudo/alpha-0/.github/workflows/infisical-oidc-canary.yml@refs/heads/main'
NEGATIVE_WORKFLOW = 'spenskoj90-sudo/alpha-0/.github/workflows/infisical-oidc-negative.yml@refs/heads/main'
MAX_BODY = 65536


class CanaryFailure(Exception):
    """Only fixed non-secret diagnostics may reach this exception."""


def require(condition, reason):
    if not condition:
        raise CanaryFailure(reason)


def decode_claims(value):
    try:
        require(isinstance(value, str) and 0 < len(value) <= MAX_BODY, 'invalid token size')
        pieces = value.split('.')
        require(len(pieces) == 3, 'invalid token structure')
        result = json.loads(base64.urlsafe_b64decode(pieces[1] + '=' * (-len(pieces[1]) % 4)))
        require(isinstance(result, dict), 'invalid token claims')
        return result
    except CanaryFailure:
        raise
    except Exception:
        raise CanaryFailure('invalid token claims') from None


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True, repr=False)
class Token:
    value: str
    iat: float
    exp: float
    chain: str


def validate_token(reply, now):
    require(isinstance(reply, dict), 'invalid token response')
    ttl = reply.get('expiresIn')
    require(finite_number(ttl) and 0 < ttl <= 600, 'token TTL outside policy')
    value = reply.get('accessToken')
    claims = decode_claims(value)
    iat, exp = claims.get('iat'), claims.get('exp')
    chain = claims.get('jti') or claims.get('identityAccessTokenId')
    require(finite_number(iat) and finite_number(exp), 'missing token timestamps')
    require(0 < exp - iat <= 600 and iat <= now + 30 and now < exp <= now + 630,
            'token lifetime outside policy')
    require(claims.get('identityId') == IDENTITY, 'unexpected token identity')
    require(isinstance(chain, str) and 0 < len(chain) <= 256, 'missing token chain')
    return Token(value, iat, exp, chain)


def validate_renewal(reply, original, now):
    renewed = validate_token(reply, now)
    maximum = reply.get('accessTokenMaxTTL')
    require(finite_number(maximum) and 0 < maximum <= 600, 'renewal maxTTL outside policy')
    require(renewed.chain == original.chain and renewed.exp <= original.iat + 600,
            'renewal changed chain or extended absolute lifetime')
    return renewed


def run_lifecycle(api, github_jwt, clock=time):
    def login():
        status, reply = api('/oidc-auth/login', {'identityId': IDENTITY, 'jwt': github_jwt()})
        require(status == 200, 'lifecycle login rejected')
        result = validate_token(reply, clock.time())
        status, reply = api('/token/renew', {'accessToken': result.value})
        require(status == 200, 'authenticated renewal baseline unavailable')
        renewed = validate_renewal(reply, result, clock.time())
        return tuple({item.value: item for item in (result, renewed)}.values())

    expiry = login()
    # A monotonic deadline prevents a backwards wall-clock jump extending the run.
    last_expiry = max(item.exp for item in expiry)
    wait = last_expiry + 5 - clock.time()
    require(0 < wait <= 635, 'expiry observation window outside policy')
    deadline = clock.monotonic() + wait
    while clock.monotonic() < deadline:
        clock.sleep(min(15, deadline - clock.monotonic()))
    require(clock.time() >= last_expiry + 5, 'clock skew prevents expiry evidence')
    for item in expiry:
        status, _ = api('/token/renew', {'accessToken': item.value})
        require(status == 401, 'expired token renewal was not explicitly unauthorized')

    revoke = login()
    require(revoke[0].chain != expiry[0].chain, 'expiry and revoke share a token chain')
    earliest_expiry = min(item.exp for item in revoke)
    started = clock.monotonic()
    status, _ = api('/token/revoke', {'accessToken': revoke[-1].value})
    require(status == 200, 'self-revocation request rejected')
    require(clock.time() + 30 < earliest_expiry, 'revocation window overlaps natural expiry')
    for item in revoke:
        status, _ = api('/token/renew', {'accessToken': item.value})
        require(clock.monotonic() - started <= 60 and clock.time() + 30 < earliest_expiry,
                'revocation observation exceeded pre-expiry window')
        require(status == 401, 'revoked token renewal was not explicitly unauthorized')
    return ('expiry', 'self-revocation')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(opener, request):
    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            # No unexpected or error body is read, even if access is misconfigured.
            if status != 200:
                return status, {}
            raw = response.read(MAX_BODY + 1)
            require(len(raw) <= MAX_BODY, 'provider response exceeds bound')
            result = json.loads(raw)
            require(isinstance(result, dict), 'invalid provider JSON')
            return status, result
    except urllib.error.HTTPError as error:
        error.close()
        return error.code, {}
    except CanaryFailure:
        raise
    except Exception:
        raise CanaryFailure('bounded HTTPS request failed') from None


def provider_api(path, payload):
    require(path in ('/oidc-auth/login', '/token/renew', '/token/revoke'), 'API path outside canary')
    request = urllib.request.Request('https://app.infisical.com/api/v1/auth' + path,
        data=json.dumps(payload).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
    return request_json(urllib.request.build_opener(NoRedirect), request)


def github_jwt(mode):
    expected_workflow = WORKFLOW if mode == 'lifecycle' else NEGATIVE_WORKFLOW
    require(os.environ.get('GITHUB_REPOSITORY') == 'spenskoj90-sudo/alpha-0'
            and os.environ.get('GITHUB_REF') == 'refs/heads/main'
            and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and os.environ.get('GITHUB_WORKFLOW_REF') == expected_workflow,
            'runner context outside protected manual workflow')
    url = os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL', '')
    credential = os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN', '')
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == 'https' and parsed.hostname
            and parsed.hostname.endswith('.actions.githubusercontent.com')
            and not parsed.username and not parsed.password and parsed.port in (None, 443)
            and not parsed.fragment and credential, 'OIDC runner endpoint unavailable')
    url += ('&' if '?' in url else '?') + urllib.parse.urlencode({'audience': AUDIENCE})
    status, reply = request_json(urllib.request.build_opener(NoRedirect),
        urllib.request.Request(url, headers={'Authorization': 'Bearer ' + credential}))
    require(status == 200, 'GitHub OIDC acquisition rejected')
    value = reply.get('value')
    claims = decode_claims(value)
    expected = {'iss': 'https://token.actions.githubusercontent.com', 'aud': AUDIENCE,
        'sub': 'repo:spenskoj90-sudo@314939603/alpha-0@1328718401:ref:refs/heads/main',
        'repository_id': '1328718401', 'repository_owner_id': '314939603',
        'ref': 'refs/heads/main', 'event_name': 'workflow_dispatch',
        'workflow_ref': expected_workflow}
    require(all(str(claims.get(key)) == val for key, val in expected.items()),
            'unexpected GitHub workload claims')
    return value


def run_wrong_workflow(api, get_jwt):
    status, _ = api('/oidc-auth/login', {'identityId': IDENTITY, 'jwt': get_jwt()})
    require(status in (401, 403), 'wrong-workflow login not explicitly denied')
    return 'wrong-workflow'


def main():
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in ('lifecycle', 'deny-workflow'), 'invalid canary mode')
        mode = sys.argv[1]
        if mode == 'lifecycle':
            run_lifecycle(provider_api, lambda: github_jwt(mode))
            print('PASS: token expiry and pre-expiry self-revocation verified; no credentials logged')
        else:
            run_wrong_workflow(provider_api, lambda: github_jwt(mode))
            print('PASS: provider explicitly denied wrong-workflow OIDC context; no credentials logged')
        return 0
    except CanaryFailure as error:
        print('FAIL CLOSED: ' + str(error))
        return 1
    except Exception:
        print('FAIL CLOSED: unexpected canary failure (details suppressed)')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
