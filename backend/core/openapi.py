"""API の契約（OpenAPI のスキーマ）に入れるパスの一覧（I493）

ここに足したパスだけが backend/openapi.yaml と画面の型（frontend/src/types/api/schema.d.ts）に入る。
足すときは、警告 0（--fail-on-warn）で作れるように、ビューとシリアライザに注釈を付ける。
"""
CONTRACT_PATHS = frozenset({
    '/api/dashboard/overview/',
    '/api/dashboard/analytics/',  # I488: 統計画面
    '/api/settings/',  # I487: 設定画面・通知の項目名を裏側にそろえるため
    '/api/user/subjects/',  # I494: 学ぶ科目の取得・置き換え
    '/api/user/subjects/available/',  # I494: 設定画面の「学ぶ科目」のカード
    # I619: パスキーの一覧・名前・削除・登録・ログイン・本人確認
    '/api/auth/passkeys/',
    '/api/auth/passkeys/{id}/',
    '/api/auth/passkeys/register/options/',
    '/api/auth/passkeys/register/',
    '/api/auth/passkeys/login/options/',
    '/api/auth/passkeys/login/',
    '/api/auth/passkeys/reauth/options/',
    '/api/auth/passkeys/reauth/',
})


def only_contract_paths(endpoints, **kwargs):
    """drf-spectacular の PREPROCESSING_HOOKS。endpoints は (path, path_regex, method, callback) の並び

    ここに渡る path の主キーは `{pk}` で、できあがるスキーマでは `{id}` になる（SCHEMA_COERCE_PATH_PK）。
    CONTRACT_PATHS はスキーマの形（`{id}`）で書くので、同じ置き換えをしてから比べる（I619）
    """
    return [endpoint for endpoint in endpoints if endpoint[0].replace('{pk}', '{id}') in CONTRACT_PATHS]
