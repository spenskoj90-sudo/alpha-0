from __future__ import annotations

from html import escape

from app.core.email_codes import EMAIL_CODE_TTL_SECONDS
from app.core.email_provider import EmailMessage, EmailProviderUnavailable, EmailTransport

VERIFY_SUBJECT = 'Verify your SENTINEL email'
RESET_SUBJECT = 'Reset your SENTINEL password'


def email_language(accept_language: str | None) -> str:
    preferences: list[tuple[float, int, str]] = []
    for index, item in enumerate((accept_language or 'en')[:256].split(',')):
        parts = item.strip().lower().split(';')
        language = parts[0].split('-')[0]
        try:
            quality = float(parts[1].strip().removeprefix('q=')) if len(parts) > 1 else 1.0
        except ValueError:
            continue
        if language in {'en', 'ru'} and 0 < quality <= 1:
            preferences.append((quality, -index, language))
    return max(preferences)[2] if preferences else 'en'


def action_email(email: str, code: str, *, reset: bool = False, language: str = 'en') -> EmailMessage:
    ru = language == 'ru'
    lang = 'ru' if ru else 'en'
    minutes = EMAIL_CODE_TTL_SECONDS // 60
    subject = ('Восстановление пароля SENTINEL' if reset else 'Подтвердите email в SENTINEL') if ru else (RESET_SUBJECT if reset else VERIFY_SUBJECT)
    heading = ('Восстановите доступ' if reset else 'Подтвердите ваш email') if ru else ('Recover your account' if reset else 'Verify your email')
    instruction = ('Введите этот код в SENTINEL, чтобы установить новый пароль.' if reset else 'Введите этот код в SENTINEL, чтобы подтвердить адрес электронной почты.') if ru else ('Enter this code in SENTINEL to set a new password.' if reset else 'Enter this code in SENTINEL to confirm your email address.')
    label = ('Код восстановления' if reset else 'Код подтверждения') if ru else ('Reset code' if reset else 'Verification code')
    expiry = f'Код действует {minutes} минут и может быть использован один раз.' if ru else f'This code expires in {minutes} minutes and can be used once.'
    copy_hint = 'Нажмите и удерживайте цифры, скопируйте код и вставьте его целиком в приложение.' if ru else 'Press and hold the digits to copy, then paste the whole code into the app.'
    warning = 'Не сообщайте код другим людям. SENTINEL не попросит отправить его в переписке.' if ru else 'Keep this code private. SENTINEL will never ask you to send it in a message.'
    unexpected = 'Если вы не запрашивали это письмо, просто проигнорируйте его.' if ru else 'If you did not request this email, you can safely ignore it.'
    sessions = ('После смены пароля существующие сессии будут завершены. Настроенная MFA останется включённой.' if ru else 'Updating your password ends existing sessions. Configured MFA remains enabled.') if reset else ''
    brand_note = 'ДОВЕРЕННАЯ АНАЛИТИКА' if ru else 'TRUSTED INTELLIGENCE'
    # No credential in subject/preheader, links, images, scripts or attachments.
    html = f'''<!doctype html>
<html lang="{lang}" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>{escape(subject)}</title>
<style>@media (prefers-color-scheme: dark) {{ .email-bg {{ background:#101b22!important; }} .email-card {{ background:#17262f!important;color:#edf4f7!important; }} .email-muted {{ color:#becbd2!important; }} .email-code {{ background:#243b46!important;color:#f2fafb!important; }} }}</style></head>
<body class="email-bg" style="margin:0;padding:0;background:#f1f5f7;">
<div lang="{lang}" dir="ltr" style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{escape(expiry)}</div>
<table lang="{lang}" dir="ltr" role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-card" style="max-width:560px;background:#ffffff;border:1px solid #ccd8de;border-top:4px solid #087b89;border-radius:12px;color:#172b36;font-family:Inter,Arial,Helvetica,sans-serif;">
<tr><td style="padding:28px 24px 12px;"><p style="margin:0;font-family:Onest,Inter,Arial,sans-serif;font-size:20px;font-weight:700;letter-spacing:2px;">SENTINEL</p><p class="email-muted" style="margin:8px 0 0;color:#4d6470;font-size:11px;letter-spacing:1px;">{brand_note}</p></td></tr>
<tr><td style="padding:12px 24px;"><h1 style="margin:0 0 16px;font-size:26px;line-height:1.25;">{heading}</h1><p style="margin:0;font-size:16px;line-height:1.6;">{instruction}</p></td></tr>
<tr><td style="padding:12px 24px;"><p class="email-muted" style="margin:0 0 10px;color:#4d6470;font-size:14px;">{label}</p><div class="email-code" style="padding:18px 8px;background:#edf5f6;border:1px solid #bcd5da;border-radius:8px;text-align:center;color:#13343f;"><span style="font-family:'JetBrains Mono',Consolas,'Courier New',monospace;font-size:32px;font-weight:700;letter-spacing:3px;white-space:nowrap;user-select:all;">{escape(code)}</span></div><p style="margin:12px 0 0;font-size:14px;line-height:1.5;">{expiry}</p><p class="email-muted" style="margin:10px 0 0;color:#4d6470;font-size:14px;line-height:1.5;">{copy_hint}</p></td></tr>
<tr><td style="padding:12px 24px 28px;"><p style="margin:0 0 12px;font-size:14px;line-height:1.6;">{sessions}</p><p style="margin:0 0 12px;font-size:14px;line-height:1.6;">{warning}</p><p class="email-muted" style="margin:0;color:#4d6470;font-size:14px;line-height:1.6;">{unexpected}</p></td></tr>
</table></td></tr></table></body></html>'''
    text = f'SENTINEL\n{heading}\n\n{instruction}\n\n{label}: {code}\n\n{expiry}\n{copy_hint}\n\n{sessions}\n{warning}\n{unexpected}'
    return EmailMessage(email, subject, text, html)


def _send(transport: EmailTransport, message: EmailMessage) -> bool:
    try:
        transport.send(message)
        return True
    except EmailProviderUnavailable:
        return False


def send_verification_email(transport: EmailTransport, email: str, token: str, language: str = 'en') -> bool:
    return _send(transport, action_email(email, token, language=language))


def send_password_reset_email(transport: EmailTransport, email: str, token: str, language: str = 'en') -> bool:
    return _send(transport, action_email(email, token, reset=True, language=language))
