"""
共通ミックスインモジュール

DRFのViewSetで使用する共通機能を提供
"""
from typing import Any, Dict, List


class MultipartFormDataMixin:
    """
    multipart/form-dataのQueryDict変換を行うミックスイン

    DRFベストプラクティス:
        - リクエスト形式の処理はView層の責務
        - シリアライザーはビジネスロジック変換に専念

    使用方法:
        class MyViewSet(MultipartFormDataMixin, viewsets.ModelViewSet):
            multipart_list_fields = ['choices', 'tags']  # リストとして保持するフィールド
            ...

    Note:
        - get_serializerをオーバーライドするため、create/update両方で自動適用
        - multipart_list_fieldsで指定したフィールドはリストとして保持
        - その他のフィールドは単一値に変換
    """

    # リストとして保持するフィールド名（サブクラスでオーバーライド可能）
    multipart_list_fields: List[str] = []

    def get_serializer(self, *args: Any, **kwargs: Any) -> Any:
        """
        データをdict形式に変換してからシリアライザーに渡す

        QueryDictはimmutableのため、シリアライザーで直接変更できない。
        このメソッドでdictに変換することで、シリアライザーは
        リクエスト形式を意識せずにデータ変換に専念できる。
        """
        if 'data' in kwargs and hasattr(kwargs['data'], 'getlist'):
            kwargs['data'] = self._convert_querydict_to_dict(kwargs['data'])
        return super().get_serializer(*args, **kwargs)

    def _convert_querydict_to_dict(self, querydict: Any) -> Dict[str, Any]:
        """
        QueryDictを通常のdictに変換

        Args:
            querydict: Django QueryDictオブジェクト

        Returns:
            Dict[str, Any]: 変換後のdict
                - multipart_list_fieldsに指定されたキーはリストとして保持
                - その他のキーは単一値（値が1つの場合）またはリスト
        """
        data: Dict[str, Any] = {}
        list_fields = getattr(self, 'multipart_list_fields', [])

        for key in querydict.keys():
            values = querydict.getlist(key)

            if key in list_fields:
                # 明示的にリストとして指定されたフィールド
                data[key] = values
            else:
                # 単一値の場合は値のみ、複数値の場合はリスト
                data[key] = values[0] if len(values) == 1 else values

        return data
