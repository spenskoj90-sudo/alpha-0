import pytest
from app.core.federated_auth import provider_status

@pytest.mark.parametrize('provider,client', [('google','<google-web-oauth-client-id>'),('google','arbitrary'),('telegram','<botfather-client-id>'),('vk','0'),('vk','<application-id>')])
def test_enabled_flag_does_not_activate_placeholder_or_invalid_public_id(monkeypatch, provider, client):
    monkeypatch.setenv(f'SENTINEL_{provider.upper()}_AUTH_ENABLED','true')
    monkeypatch.setenv(f'SENTINEL_{provider.upper()}_WEB_CLIENT_ID' if provider=='google' else f'SENTINEL_{provider.upper()}_CLIENT_ID', client)
    monkeypatch.setenv('SENTINEL_TELEGRAM_CLIENT_SECRET','test-secret')
    monkeypatch.setenv('SENTINEL_TELEGRAM_REDIRECT_URIS','com.alpha0.app.physicaltest.auth://callback')
    monkeypatch.setenv('SENTINEL_VK_REDIRECT_URIS','vk123://vk.ru/blank.html')
    assert not provider_status(provider).enabled

@pytest.mark.parametrize('secret,redirects', [('CHANGEME','com.alpha0.app.physicaltest.auth://callback'),('REPLACEME','com.alpha0.app.physicaltest.auth://callback'),('change-me-owner-secret','com.alpha0.app.physicaltest.auth://callback'),('CHANGE_ME_OWNER_MANAGED_SECRET','com.alpha0.app.physicaltest.auth://callback'),('test-secret','com.alpha0.app.physicaltest.auth://callback,https://example.test/callback?next=untrusted')])
def test_telegram_placeholder_secret_or_partially_invalid_callbacks_fail_closed(monkeypatch, secret, redirects):
    monkeypatch.setenv('SENTINEL_TELEGRAM_AUTH_ENABLED','true')
    monkeypatch.setenv('SENTINEL_TELEGRAM_CLIENT_ID','123')
    monkeypatch.setenv('SENTINEL_TELEGRAM_CLIENT_SECRET',secret)
    monkeypatch.setenv('SENTINEL_TELEGRAM_REDIRECT_URIS',redirects)
    assert not provider_status('telegram').enabled


def test_vk_manifest_callback_must_match_public_client_id(monkeypatch):
    monkeypatch.setenv('SENTINEL_VK_AUTH_ENABLED','true')
    monkeypatch.setenv('SENTINEL_VK_CLIENT_ID','123')
    monkeypatch.setenv('SENTINEL_VK_REDIRECT_URIS','vk456://vk.ru/blank.html')
    assert not provider_status('vk').enabled
    monkeypatch.setenv('SENTINEL_VK_REDIRECT_URIS','vk123://vk.ru/blank.html')
    assert provider_status('vk').enabled
