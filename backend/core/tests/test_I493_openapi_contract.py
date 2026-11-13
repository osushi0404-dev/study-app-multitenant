"""API の契約（OpenAPI のスキーマ）のテスト（I493）

- backend/openapi.yaml がシリアライザから作り直したものと同じか（作り直し忘れを CI で止める）
- overview の形（必須・型・null の可否）がスキーマに正しく出ているか
"""
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command

from core.openapi import CONTRACT_PATHS

COMMITTED_SCHEMA = Path(settings.BASE_DIR) / 'openapi.yaml'
REGENERATE_HINT = (
    'backend/openapi.yaml が古い。作り直す: '
    'docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn '
    '→ npm --prefix tools/api-types run generate（docs/runbooks/common-commands.md）'
)
OVERVIEW = '/api/dashboard/overview/'


def generate_schema_text(tmp_path):
    """コードからスキーマを作る（警告が 1 つでもあれば --fail-on-warn で失敗する）"""
    out = tmp_path / 'openapi.yaml'
    call_command('spectacular', '--file', str(out), '--validate', '--fail-on-warn')
    return out.read_text(encoding='utf-8')


def assert_schema_file_matches(committed_path, generated_text):
    """リポジトリのスキーマが、作り直したものと同じでなければ AssertionError"""
    assert committed_path.read_text(encoding='utf-8') == generated_text, REGENERATE_HINT


@pytest.fixture(scope='module')
def schema_text(tmp_path_factory):
    """作る・検証するのは重いので、このファイルの中で 1 回だけ（DB には触らない・テストは読むだけ）"""
    return generate_schema_text(tmp_path_factory.mktemp('openapi'))


@pytest.fixture(scope='module')
def schema(schema_text):
    return yaml.safe_load(schema_text)


def _component(schema, name):
    return schema['components']['schemas'][name]


def _ref(name):
    return f'#/components/schemas/{name}'


class TestSchemaIsUpToDate:
    def test_tc01_committed_schema_matches_generated(self, schema_text):
        assert_schema_file_matches(COMMITTED_SCHEMA, schema_text)

    def test_tc02_stale_schema_is_detected(self, schema_text, tmp_path):
        """失敗の注入: 1 行足した写しでは AssertionError になる（本物のファイルは書き換えない）"""
        stale_path = tmp_path / 'stale.yaml'
        stale_path.write_text(schema_text + '# stale\n', encoding='utf-8')
        with pytest.raises(AssertionError):
            assert_schema_file_matches(stale_path, schema_text)


class TestOverviewShape:
    """TC-03: overview の応答の形が OverviewSerializer と同じ"""

    def test_response_refers_to_dashboard_overview(self, schema):
        content = schema['paths'][OVERVIEW]['get']['responses']['200']['content']
        assert content['application/json']['schema'] == {'$ref': _ref('DashboardOverview')}

    def test_overview_keys(self, schema):
        overview = _component(schema, 'DashboardOverview')
        props = overview['properties']
        assert set(overview['required']) == {
            'has_data', 'today', 'streak', 'totals', 'last_7_days', 'weak_subjects', 'recommendations'}
        assert props['has_data'] == {'type': 'boolean'}
        assert props['today'] == {'$ref': _ref('DashboardToday')}
        assert props['streak'] == {'$ref': _ref('DashboardStreak')}
        assert props['totals'] == {'$ref': _ref('DashboardTotals')}
        assert props['last_7_days'] == {'type': 'array', 'items': {'$ref': _ref('DashboardDay')}}
        assert props['weak_subjects'] == {'type': 'array', 'items': {'$ref': _ref('DashboardWeakSubject')}}
        assert props['recommendations'] == {
            'type': 'array', 'items': {'$ref': _ref('DashboardRecommendation')}}

    @pytest.mark.parametrize('name, required', [
        ('DashboardToday', {'answered_count', 'correct_count', 'accuracy_rate', 'study_seconds'}),
        ('DashboardTotals', {'answered_count', 'correct_count', 'accuracy_rate'}),
    ])
    def test_counts_allow_null_accuracy(self, schema, name, required):
        """Today と Totals は別の部品で、比率は答えが 0 件なら null"""
        component = _component(schema, name)
        assert set(component['required']) == required
        assert component['properties']['accuracy_rate']['type'] == 'number'
        assert component['properties']['accuracy_rate']['nullable'] is True
        assert component['properties']['answered_count'] == {'type': 'integer'}

    def test_weak_subject_accuracy_is_not_nullable(self, schema):
        component = _component(schema, 'DashboardWeakSubject')
        assert set(component['required']) == {'subject_id', 'subject_name', 'answered_count', 'accuracy_rate'}
        assert component['properties']['accuracy_rate']['type'] == 'number'
        assert 'nullable' not in component['properties']['accuracy_rate']

    def test_day_and_streak(self, schema):
        day = _component(schema, 'DashboardDay')
        assert set(day['required']) == {'date', 'study_seconds', 'answered_count', 'correct_count'}
        assert day['properties']['date'] == {'type': 'string', 'format': 'date'}
        streak = _component(schema, 'DashboardStreak')
        assert streak['required'] == ['current_days']
        assert streak['properties']['current_days'] == {'type': 'integer'}

    def test_recommendation_kind_enum(self, schema):
        recommendation = _component(schema, 'DashboardRecommendation')
        assert set(recommendation['required']) == {'kind', 'subject_id', 'subject_name', 'reason'}
        assert recommendation['properties']['kind'] == {'$ref': _ref('DashboardRecommendationKindEnum')}
        assert _component(schema, 'DashboardRecommendationKindEnum')['enum'] == [
            'weak_subject', 'unstudied_subject']

    def test_subject_id_query_is_optional_integer(self, schema):
        params = schema['paths'][OVERVIEW]['get']['parameters']
        subject_id = next(p for p in params if p['name'] == 'subject_id')
        assert subject_id['in'] == 'query'
        assert subject_id['schema'] == {'type': 'integer'}
        assert not subject_id.get('required', False)


def test_tc04_schema_has_only_contract_paths(schema):
    """一覧（CONTRACT_PATHS）に無い API はスキーマに入らない"""
    assert set(schema['paths']) == set(CONTRACT_PATHS)
