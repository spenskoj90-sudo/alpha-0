from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
import re

from fastapi.testclient import TestClient
import pytest

from app import main as main_module
from app.core.account_notifications import action_email, email_language
from app.core.auth import verify_password
from app.core.email_provider import TestEmailTransport
from app.core.user_store import UserAccountStore
from app.main import app


def account():
    accounts = UserAccountStore(None)
    accounts.register('a@example.com', 'Correct-test-password-123')
    accounts.register('b@example.com', 'Correct-test-password-456')
    return accounts


def test_code_is_padded_salted_scoped_expiring_single_use(monkeypatch):
    accounts = account()
    monkeypatch.setattr('app.core.user_store.secrets.randbelow', lambda _: 123)
    code = accounts.issue_action_code(' A@example.com ', 'EMAIL_VERIFY')
    assert code == '00000123'
    action = next(iter(accounts._action_tokens.values()))
    assert code not in accounts._action_tokens and code not in action.values()
    assert verify_password(code, action['code_hash'])
    assert 898 < (action['expires_at'] - datetime.now(UTC)).total_seconds() <= 900
    assert not accounts.confirm_email(code)
    assert not accounts.confirm_email(code, 'b@example.com')
    assert accounts.reset_password(code, 'Correct-new-password-123', object(), 'a@example.com') is None
    assert accounts.confirm_email('0000 0123', ' A@example.com ')
    assert not accounts.confirm_email(code, 'a@example.com')


def test_five_attempts_invalidate_only_challenge_and_resends_have_durable_budget():
    accounts = account()
    code = accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY')
    wrong = '11111111' if code != '11111111' else '22222222'
    for _ in range(5):
        assert not accounts.confirm_email(wrong, 'a@example.com')
    assert not accounts.confirm_email(code, 'a@example.com')
    assert accounts.authenticate('a@example.com', 'Correct-test-password-123')
    for _ in range(2):
        assert accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY')
    assert accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY') is None
    assert accounts.issue_action_code('a@example.com', 'PASSWORD_RESET')
    for action in accounts._action_tokens.values():
        action['created_at'] -= timedelta(hours=2)
    assert accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY')


def test_replacement_and_expiry_reject_old_code_and_opaque_compatibility_survives(monkeypatch):
    accounts = account()
    values = iter([123, 456])
    monkeypatch.setattr('app.core.user_store.secrets.randbelow', lambda _: next(values))
    old = accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY')
    new = accounts.issue_action_code('a@example.com', 'EMAIL_VERIFY')
    assert old != new
    assert not accounts.confirm_email(old, 'a@example.com')
    for action in accounts._action_tokens.values():
        action['expires_at'] = datetime.now(UTC) - timedelta(seconds=1)
    assert not accounts.confirm_email(new, 'a@example.com')
    opaque = accounts.issue_action_token('a@example.com', 'EMAIL_VERIFY', 86400)
    assert accounts.confirm_email(opaque)
    assert not accounts.confirm_email(opaque)


def test_api_requires_email_accepts_whitespace_and_localizes_without_returning_code(monkeypatch):
    accounts = account()
    transport = TestEmailTransport()
    monkeypatch.setattr(main_module, 'user_store', accounts)
    monkeypatch.setattr(main_module, 'email_transport', transport)
    client = TestClient(app)
    request = client.post('/v1/auth/email-verification/request', json={'email': 'a@example.com'}, headers={'accept-language': 'ru-RU, en;q=0.5'})
    assert request.status_code == 202 and request.json() == {'status': 'ACCEPTED'}
    mail = transport.snapshot()[-1]
    assert mail.subject == 'Подтвердите email в SENTINEL'
    code = re.search(r'Код подтверждения: ([0-9]{8})', mail.text).group(1)
    assert code not in mail.subject and code not in repr(mail)
    assert client.post('/v1/auth/email-verification/confirm', json={'token': code}).status_code == 422
    assert client.post('/v1/auth/email-verification/confirm', json={'token': code, 'email': 'b@example.com'}).status_code == 400
    assert client.post('/v1/auth/email-verification/confirm', json={'token': code[:4] + ' ' + code[4:], 'email': 'a@example.com'}).status_code == 200
    opaque = accounts.issue_action_token('b@example.com', 'EMAIL_VERIFY', 86400)
    assert client.post('/v1/auth/email-verification/confirm', json={'token': opaque}).status_code == 200


@pytest.mark.parametrize('reset', [False, True])
@pytest.mark.parametrize('language', ['en', 'ru'])
def test_email_is_accessible_plaintext_html_and_code_is_one_copyable_text_node(reset, language):
    message = action_email('a@example.com', '00001234', reset=reset, language=language)
    html = message.html
    assert '<html lang="' + language + '" dir="ltr">' in html
    assert '<h1 ' in html and '<title>' in html
    assert '<script' not in html and '<img' not in html and 'href=' not in html
    assert '00001234' in html and '00001234' in message.text and '00001234' not in message.subject
    assert ('15 минут' if language == 'ru' else '15 minutes') in message.text
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(); self.nodes = []; self.tables = []
        def handle_data(self, data): self.nodes.append(data)
        def handle_starttag(self, tag, attrs):
            if tag == 'table': self.tables.append(dict(attrs))
    parser = Parser(); parser.feed(html)
    assert parser.nodes.count('00001234') == 1
    assert all(t.get('role') == 'presentation' for t in parser.tables)
    assert '&lt;script&gt;' in action_email('a@example.com', '<script>').html


def test_language_selection_is_bounded_and_respects_quality():
    assert email_language('ru-RU, en;q=0.5') == 'ru'
    assert email_language('ru;q=0.1,en;q=0.9') == 'en'
    assert email_language('ru;q=0,en;q=1') == 'en'
    assert email_language('ru;q=bad') == 'en'
    assert email_language(None) == 'en'
