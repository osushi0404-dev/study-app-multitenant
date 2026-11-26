"""パスキー（WebAuthn）の設定の誤りを止めるシステムチェック（I619）

本番（DEBUG=False）で、平文（http）の origin・空の origin・origin の host と合わない RP ID を Error にする。
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def check_webauthn_settings(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    origins = list(settings.WEBAUTHN_ALLOWED_ORIGINS)
    rp_id = settings.WEBAUTHN_RP_ID
    if not origins:
        return [Error('WEBAUTHN_ALLOWED_ORIGINS が空です', id='accounts.E001',
                      hint='本番の画面の origin（https://…）を設定してください')]
    errors = []
    insecure = [origin for origin in origins if not origin.startswith('https://')]
    if insecure:
        errors.append(Error(f'https でない origin があります: {insecure}', id='accounts.E002'))
    mismatched = [origin for origin in origins
                  if not _rp_id_matches(rp_id, urlsplit(origin).hostname or '')]
    if mismatched:
        errors.append(Error(f'WEBAUTHN_RP_ID（{rp_id}）が origin の host と合いません: {mismatched}',
                            id='accounts.E003', hint='RP ID は host と同じか、その親のドメインにします'))
    # 登録用リンク（I620）はパスキーを許す画面で開かないと登録できない
    base = settings.REGISTRATION_LINK_BASE_URL
    if base not in origins:
        errors.append(Error(
            f'REGISTRATION_LINK_BASE_URL（{base}）が WEBAUTHN_ALLOWED_ORIGINS にありません',
            id='accounts.E004', hint='登録用リンクの土台は、パスキーを許す画面の origin にします'))
    return errors


def _rp_id_matches(rp_id: str, host: str) -> bool:
    return bool(rp_id) and (host == rp_id or host.endswith('.' + rp_id))
