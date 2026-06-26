"""
Redis キャッシュサービス

アプリケーション全体でのキャッシュ管理を統一し、
パフォーマンスを向上させるためのサービスクラス
"""

import json
import hashlib
from typing import Any, Optional, List, Dict

from django.core.cache import caches
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model

User = get_user_model()


class CacheService:
    """統一キャッシュサービス"""

    def __init__(self):
        self.default_cache = caches['default']
        self.sessions_cache = caches['sessions']
        self.problems_cache = caches['problems']
        self.analytics_cache = caches['analytics']
        self.timeouts = settings.CACHE_TIMEOUTS

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """キャッシュキーを生成"""
        key_parts = [prefix]

        # 引数を追加
        for arg in args:
            if isinstance(arg, (int, str)):
                key_parts.append(str(arg))
            elif hasattr(arg, 'id'):
                key_parts.append(f"{arg.__class__.__name__}_{arg.id}")

        # キーワード引数を追加
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}_{v}")

        # ハッシュ化してキーを短縮
        key_string = "_".join(key_parts)
        if len(key_string) > 200:  # Redis key length limit
            key_hash = hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()
            return f"{prefix}_{key_hash}"

        return key_string

    def _serialize_data(self, data: Any) -> str:
        """データをシリアライズ"""
        return json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False)

    def _deserialize_data(self, data: str) -> Any:
        """データをデシリアライズ"""
        if data is None:
            return None
        return json.loads(data)

    # ユーザープロファイル関連
    def get_user_profile_cache(self, user_id: int) -> Optional[Dict]:
        """ユーザープロファイルキャッシュを取得"""
        key = self._generate_key('user_profile', user_id)
        return self.default_cache.get(key)

    def set_user_profile_cache(self, user_id: int, profile_data: Dict):
        """ユーザープロファイルキャッシュを設定"""
        key = self._generate_key('user_profile', user_id)
        timeout = self.timeouts['user_profile']
        self.default_cache.set(key, profile_data, timeout)

    def invalidate_user_profile_cache(self, user_id: int):
        """ユーザープロファイルキャッシュを無効化"""
        key = self._generate_key('user_profile', user_id)
        self.default_cache.delete(key)

    # 問題関連
    def get_problems_cache(
        self, subject_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Optional[List]:
        """問題リストキャッシュを取得"""
        key = self._generate_key(
            'problems', subject_id=subject_id,
            difficulty=difficulty, user_id=user_id,
        )
        return self.problems_cache.get(key)

    def set_problems_cache(
        self, problems_data: List,
        subject_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        """問題リストキャッシュを設定"""
        key = self._generate_key(
            'problems', subject_id=subject_id,
            difficulty=difficulty, user_id=user_id,
        )
        timeout = self.timeouts['problem_list']
        self.problems_cache.set(key, problems_data, timeout)

    def invalidate_problems_cache(self, subject_id: Optional[int] = None):
        """問題関連キャッシュを無効化（イシュー#073）

        問題の追加・編集・削除は「全件リスト / 科目別 / 難易度別 / 同組織の全ユーザ別」の
        すべてのキャッシュ変種に波及するため、problems キャッシュ名前空間を一括クリアする。
        `subject_id` は後方互換のため受け取るが、無効化範囲は常に全 problems キャッシュ。

        注意: django-redis の delete_pattern は KEY_PREFIX（learning_app_problems:）を
        自動付与するため、パターンに KEY_PREFIX を含めずキー本体（problems_*）のみを渡す。
        旧実装は KEY_PREFIX を手書きして二重付与となり、かつ subject_id 限定パターンが
        実キー（problems_difficulty_*_subject_id_*_user_id_*）と構造的に不一致だったため、
        無効化が無言で機能せず編集結果が一覧/参照に反映されなかった。
        """
        self._delete_by_pattern(self.problems_cache, "problems_*")

    # 科目関連
    def get_subjects_cache(self, cache_key: str = 'subjects_all') -> Optional[List]:
        """科目リストキャッシュを取得"""
        key = self._generate_key(cache_key)
        return self.default_cache.get(key)

    def set_subjects_cache(self, subjects_data: List, cache_key: str = 'subjects_all'):
        """科目リストキャッシュを設定"""
        key = self._generate_key(cache_key)
        timeout = self.timeouts['subject_list']
        self.default_cache.set(key, subjects_data, timeout)

    def invalidate_subjects_cache(self, cache_key: str = 'subjects_all'):
        """科目キャッシュを無効化"""
        key = self._generate_key(cache_key)
        self.default_cache.delete(key)

    # 分析データ関連
    def get_analytics_cache(
        self, user_id: int, analytics_type: str,
        period: str = 'daily',
    ) -> Optional[Dict]:
        """分析データキャッシュを取得"""
        key = self._generate_key('analytics', user_id, analytics_type, period)
        return self.analytics_cache.get(key)

    def set_analytics_cache(
        self, user_id: int, analytics_type: str,
        analytics_data: Dict, period: str = 'daily',
    ):
        """分析データキャッシュを設定"""
        key = self._generate_key('analytics', user_id, analytics_type, period)

        if period == 'daily':
            timeout = self.timeouts['analytics_daily']
        else:
            timeout = self.timeouts['analytics_weekly']

        self.analytics_cache.set(key, analytics_data, timeout)

    def invalidate_analytics_cache(self, user_id: int, analytics_type: Optional[str] = None):
        """分析データキャッシュを無効化"""
        if analytics_type:
            pattern = f"learning_app_analytics:analytics_{user_id}_{analytics_type}_*"
        else:
            pattern = f"learning_app_analytics:analytics_{user_id}_*"

        self._delete_by_pattern(self.analytics_cache, pattern)

    # 間隔反復学習関連
    def get_spaced_repetition_cache(self, user_id: int, cache_type: str) -> Optional[Any]:
        """間隔反復学習キャッシュを取得"""
        key = self._generate_key('spaced_repetition', user_id, cache_type)
        return self.default_cache.get(key)

    def set_spaced_repetition_cache(self, user_id: int, cache_type: str, data: Any):
        """間隔反復学習キャッシュを設定"""
        key = self._generate_key('spaced_repetition', user_id, cache_type)
        timeout = self.timeouts['spaced_repetition']
        self.default_cache.set(key, data, timeout)

    def invalidate_spaced_repetition_cache(self, user_id: int):
        """間隔反復学習キャッシュを無効化"""
        pattern = f"learning_app:spaced_repetition_{user_id}_*"
        self._delete_by_pattern(self.default_cache, pattern)

    # 間違いパターン関連
    def get_mistake_patterns_cache(self, user_id: int) -> Optional[Dict]:
        """間違いパターンキャッシュを取得"""
        key = self._generate_key('mistake_patterns', user_id)
        return self.default_cache.get(key)

    def set_mistake_patterns_cache(self, user_id: int, patterns_data: Dict):
        """間違いパターンキャッシュを設定"""
        key = self._generate_key('mistake_patterns', user_id)
        timeout = self.timeouts['mistake_patterns']
        self.default_cache.set(key, patterns_data, timeout)

    def invalidate_mistake_patterns_cache(self, user_id: int):
        """間違いパターンキャッシュを無効化"""
        key = self._generate_key('mistake_patterns', user_id)
        self.default_cache.delete(key)

    # 学習提案関連
    def get_learning_suggestions_cache(self, user_id: int) -> Optional[List]:
        """学習提案キャッシュを取得"""
        key = self._generate_key('learning_suggestions', user_id)
        return self.default_cache.get(key)

    def set_learning_suggestions_cache(self, user_id: int, suggestions_data: List):
        """学習提案キャッシュを設定"""
        key = self._generate_key('learning_suggestions', user_id)
        timeout = self.timeouts['learning_suggestions']
        self.default_cache.set(key, suggestions_data, timeout)

    def invalidate_learning_suggestions_cache(self, user_id: int):
        """学習提案キャッシュを無効化"""
        key = self._generate_key('learning_suggestions', user_id)
        self.default_cache.delete(key)

    # 適応的学習関連
    def get_proficiency_cache(self, user_id: int, subject_id: Optional[int] = None) -> Optional[Dict]:
        """習熟度キャッシュを取得"""
        key = self._generate_key('proficiency', user_id, subject_id or 'all')
        return self.default_cache.get(key)

    def set_proficiency_cache(
        self, user_id: int, proficiency_data: Dict,
        subject_id: Optional[int] = None,
    ):
        """習熟度キャッシュを設定"""
        key = self._generate_key('proficiency', user_id, subject_id or 'all')
        timeout = self.timeouts['spaced_repetition']  # 5分間
        self.default_cache.set(key, proficiency_data, timeout)

    def invalidate_proficiency_cache(self, user_id: int):
        """習熟度キャッシュを無効化"""
        pattern = f"learning_app:proficiency_{user_id}_*"
        self._delete_by_pattern(self.default_cache, pattern)

    # 統計関連
    def get_statistics_cache(self, user_id: int, stats_type: str) -> Optional[Dict]:
        """統計キャッシュを取得"""
        key = self._generate_key('statistics', user_id, stats_type)
        return self.analytics_cache.get(key)

    def set_statistics_cache(self, user_id: int, stats_type: str, stats_data: Dict):
        """統計キャッシュを設定"""
        key = self._generate_key('statistics', user_id, stats_type)
        timeout = self.timeouts['analytics_daily']
        self.analytics_cache.set(key, stats_data, timeout)

    def invalidate_statistics_cache(self, user_id: int):
        """統計キャッシュを無効化"""
        pattern = f"learning_app_analytics:statistics_{user_id}_*"
        self._delete_by_pattern(self.analytics_cache, pattern)

    # ユーティリティメソッド
    def _delete_by_pattern(self, cache, pattern: str):
        """パターンマッチでキャッシュを削除

        重要（イシュー#073）: django-redis の delete_pattern は KEY_PREFIX とバージョンを
        自動付与する。そのため `pattern` には KEY_PREFIX（例: ``learning_app_problems:``）を
        含めず、キー本体部分（例: ``"problems_*"``）のみを渡すこと。プレフィックスを手書きすると
        二重付与となり、どのキーにもマッチせず無効化が無言で失敗する。
        （analytics / spaced_repetition 等の他 invalidate_* は現状この罠を踏んでいるため、
        系統的是正は別イシューで対応する。）
        """
        try:
            # django-redisの場合
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
            else:
                # フォールバック: 全キーを取得して削除
                keys = cache._cache.get_client().keys(pattern)
                if keys:
                    cache._cache.get_client().delete(*keys)
        except Exception as e:
            # ログエラーだが、アプリケーションは継続
            print(f"キャッシュ削除エラー: {e}")

    def delete_pattern(self, pattern: str):
        """パターンに一致するキャッシュを削除（外部から使用可能）"""
        self._delete_by_pattern(self.default_cache, pattern)

    def clear_user_cache(self, user_id: int):
        """ユーザー関連の全キャッシュを削除"""
        self.invalidate_user_profile_cache(user_id)
        self.invalidate_analytics_cache(user_id)
        self.invalidate_spaced_repetition_cache(user_id)
        self.invalidate_mistake_patterns_cache(user_id)
        self.invalidate_learning_suggestions_cache(user_id)
        self.invalidate_proficiency_cache(user_id)
        self.invalidate_statistics_cache(user_id)

    def clear_all_cache(self):
        """全キャッシュを削除"""
        self.default_cache.clear()
        self.problems_cache.clear()
        self.analytics_cache.clear()

    def get_cache_stats(self) -> Dict:
        """キャッシュ統計を取得"""
        try:
            redis_client = self.default_cache._cache.get_client()
            info = redis_client.info()

            return {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            return {'error': f'キャッシュ統計取得エラー: {e}'}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """ヒット率を計算"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# シングルトンインスタンス
cache_service = CacheService()


def cache_key_for_user_problems(
    user_id: int, subject_id: Optional[int] = None,
    difficulty: Optional[str] = None,
) -> str:
    """ユーザー問題用のキャッシュキーを生成"""
    return cache_service._generate_key(
        'user_problems', user_id,
        subject_id=subject_id, difficulty=difficulty,
    )


def cache_key_for_user_analytics(user_id: int, period: str = 'daily') -> str:
    """ユーザー分析用のキャッシュキーを生成"""
    return cache_service._generate_key('user_analytics', user_id, period)


def invalidate_user_dependent_caches(user_id: int):
    """ユーザーの学習データ更新時に関連キャッシュを無効化"""
    cache_service.invalidate_analytics_cache(user_id)
    cache_service.invalidate_spaced_repetition_cache(user_id)
    cache_service.invalidate_mistake_patterns_cache(user_id)
    cache_service.invalidate_learning_suggestions_cache(user_id)
    cache_service.invalidate_proficiency_cache(user_id)
    cache_service.invalidate_statistics_cache(user_id)


def invalidate_problem_dependent_caches(subject_id: Optional[int] = None):
    """問題データ更新時に関連キャッシュを無効化"""
    cache_service.invalidate_problems_cache(subject_id)
    if subject_id is None:
        # 全問題に影響する場合は、全ユーザーの分析も無効化
        cache_service.clear_all_cache()
