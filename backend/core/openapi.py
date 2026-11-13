"""API の契約（OpenAPI のスキーマ）に入れるパスの一覧（I493）

ここに足したパスだけが backend/openapi.yaml と画面の型（frontend/src/types/api/schema.d.ts）に入る。
足すときは、警告 0（--fail-on-warn）で作れるように、ビューとシリアライザに注釈を付ける。
"""
CONTRACT_PATHS = frozenset({
    '/api/dashboard/overview/',
})


def only_contract_paths(endpoints, **kwargs):
    """drf-spectacular の PREPROCESSING_HOOKS。endpoints は (path, path_regex, method, callback) の並び"""
    return [endpoint for endpoint in endpoints if endpoint[0] in CONTRACT_PATHS]
