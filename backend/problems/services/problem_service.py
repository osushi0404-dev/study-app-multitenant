"""
問題登録・更新のビジネスロジック（サービス層）
イシュー#031対応: 画像アップロード機能の統合
イシュー#035対応: 問題削除時の関連画像・ファイル削除
"""
import logging
import uuid
import os
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

from problems.models import (
    Problem, Choice, MediaAsset, ProblemMediaAsset, Subject
)
from problems.utils import (
    validate_image_file,
    sanitize_filename,
    check_duplicate_filename,
    check_directory_exists,
    calculate_file_checksum,
    get_storage_path,
)


class ProblemService:
    """
    問題の登録・更新を担うサービスクラス
    画像アップロード機能を含む複雑なビジネスロジックを集約
    """

    @staticmethod
    @transaction.atomic
    def create_problem_with_images(
        validated_data: Dict[str, Any],
        question_images: Optional[List[InMemoryUploadedFile]] = None,
        explanation_images: Optional[List[InMemoryUploadedFile]] = None,
        created_by_user=None
    ) -> Problem:
        """
        問題を画像ファイルと共に登録

        Args:
            validated_data: バリデーション済みの問題データ
            question_images: 問題用画像ファイルのリスト（最大5枚）
            explanation_images: 解説用画像ファイルのリスト（最大5枚）
            created_by_user: 作成者ユーザー

        Returns:
            Problem: 作成された問題インスタンス

        Raises:
            ValidationError: バリデーションエラー時
        """

        # 1. 画像枚数のバリデーション
        if question_images and len(question_images) > 5:
            raise ValidationError("問題用画像は最大5枚までです")
        if explanation_images and len(explanation_images) > 5:
            raise ValidationError("解説用画像は最大5枚までです")

        # 2. 選択肢データの抽出（別途処理）
        choices_data = validated_data.pop('choices', [])

        # 3. 科目情報の取得
        subject = validated_data.get('subject')
        if not subject:
            raise ValidationError("科目の指定は必須です")

        # 組織情報の取得
        organization = subject.organization
        if not organization:
            raise ValidationError("科目に組織が紐づいていません")

        # 4. 問題インスタンスの作成
        problem = Problem.objects.create(
            **validated_data,
            organization=organization,
            created_by=created_by_user
        )

        # 5. 選択肢の作成
        for choice_data in choices_data:
            Choice.objects.create(
                problem=problem,
                **choice_data
            )

        # 6. 問題用画像の処理
        if question_images:
            ProblemService._process_images(
                problem=problem,
                images=question_images,
                usage_kind='problem',
                organization=organization,
                subject=subject
            )

        # 7. 解説用画像の処理
        if explanation_images:
            ProblemService._process_images(
                problem=problem,
                images=explanation_images,
                usage_kind='explanation',
                organization=organization,
                subject=subject
            )

        return problem

    @staticmethod
    def _process_images(
        problem: Problem,
        images: List[InMemoryUploadedFile],
        usage_kind: str,
        organization,
        subject: Subject
    ):
        """
        画像ファイルの処理（内部メソッド）

        Args:
            problem: 問題インスタンス
            images: 画像ファイルのリスト
            usage_kind: 用途種別（'problem' or 'explanation'）
            organization: 組織インスタンス
            subject: 科目インスタンス

        処理内容:
            1. 各画像のバリデーション
            2. ファイル名のサニタイズ
            3. 重複チェック
            4. ディレクトリ存在確認
            5. ファイル保存（UUID方式）
            6. MediaAsset作成
            7. ProblemMediaAsset作成（紐づけ）
        """

        for position, image_file in enumerate(images, start=1):
            # 1. 画像バリデーション
            is_valid, error_msg = validate_image_file(image_file)
            if not is_valid:
                raise ValidationError(f"{usage_kind}画像{position}枚目: {error_msg}")

            # 2. ファイル名のサニタイズ
            original_filename = image_file.name
            sanitized_filename = sanitize_filename(original_filename)

            # 3. 重複チェック
            is_unique, error_msg = check_duplicate_filename(
                organization_id=organization.id,
                subject_slug=subject.slug,
                usage_kind=usage_kind,
                original_filename=sanitized_filename
            )
            if not is_unique:
                raise ValidationError(f"{usage_kind}画像{position}枚目: {error_msg}")

            # 4. ディレクトリ存在確認
            directory_path = f"org/{organization.slug}/subjects/{subject.slug}/{usage_kind}"
            dir_exists, error_msg = check_directory_exists(directory_path)
            if not dir_exists:
                raise ValidationError(f"{usage_kind}画像{position}枚目: {error_msg}")

            # 5. UUID方式でファイル保存
            file_uuid = uuid.uuid4()
            file_extension = os.path.splitext(sanitized_filename)[1]
            uuid_filename = f"{file_uuid}{file_extension}"

            storage_key = get_storage_path(
                organization_slug=organization.slug,
                subject_slug=subject.slug,
                usage_kind=usage_kind,
                filename=uuid_filename
            )

            # 物理ファイル保存
            full_path = os.path.join(settings.MEDIA_ROOT, storage_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            # 6. MediaAsset作成
            checksum = calculate_file_checksum(image_file)
            media_asset = MediaAsset.objects.create(
                organization=organization,
                subject=subject,
                usage_kind=usage_kind,
                storage_key=storage_key,
                original_filename=sanitized_filename,
                mime_type=image_file.content_type,
                file_size_bytes=image_file.size,
                checksum_sha256=checksum,
                version=1,
                is_deleted=False
            )

            # 7. ProblemMediaAsset作成（問題との紐づけ）
            ProblemMediaAsset.objects.create(
                organization=organization,
                problem=problem,
                asset=media_asset,
                usage_kind=usage_kind,
                position=position
            )

    @staticmethod
    @transaction.atomic
    def update_problem_with_images(
        problem: Problem,
        validated_data: Dict[str, Any],
        question_images: Optional[List[InMemoryUploadedFile]] = None,
        explanation_images: Optional[List[InMemoryUploadedFile]] = None
    ) -> Problem:
        """
        問題を画像ファイルと共に更新

        Args:
            problem: 更新対象の問題インスタンス
            validated_data: バリデーション済みの問題データ
            question_images: 問題用画像ファイルのリスト（最大5枚）
            explanation_images: 解説用画像ファイルのリスト（最大5枚）

        Returns:
            Problem: 更新された問題インスタンス

        注意:
            今回のイシュー#031では問題編集機能は対象外のため、
            この実装は将来の拡張を見越した準備のみ
        """

        # 問題編集機能は今後実装予定
        # 現時点では基本的な更新のみ対応
        choices_data = validated_data.pop('choices', None)

        # 問題の基本情報更新
        for attr, value in validated_data.items():
            setattr(problem, attr, value)
        problem.save()

        # 選択肢の更新（簡易版）
        if choices_data is not None:
            # 既存の選択肢を削除して新規作成（簡易実装）
            problem.choices.all().delete()
            for choice_data in choices_data:
                Choice.objects.create(
                    problem=problem,
                    **choice_data
                )

        # 画像更新は今後実装予定（イシュー#031対象外）
        # TODO: 画像の追加・削除・並び替え機能

        return problem

    @staticmethod
    @transaction.atomic
    def delete_problem(problem: Problem) -> None:
        """
        問題の削除（論理削除 + 実ファイル即時物理削除）

        Args:
            problem: 削除対象の問題インスタンス

        処理内容:
            1. 関連するProblemMediaAssetを取得
            2. 各画像について他の問題で使用されていないか確認
            3. 他で使用されていない場合のみ実ファイルを物理削除
            4. MediaAssetを論理削除
            5. ProblemMediaAssetを論理削除
            6. Problemを論理削除
        """
        from core.storage_service import StorageService

        # 1. 関連するProblemMediaAssetを取得（削除されていないもの）
        related_links = ProblemMediaAsset.objects.filter(
            problem=problem,
            is_deleted=False
        ).select_related('asset')

        for link in related_links:
            asset = link.asset

            # 2. 他の問題で使用されていないか確認
            # （同じアセットを参照する、削除されていない他のリンクが存在するか）
            other_links_exist = ProblemMediaAsset.objects.filter(
                asset=asset,
                is_deleted=False
            ).exclude(problem=problem).exists()

            if not other_links_exist:
                # 3. 実ファイル即時物理削除
                try:
                    StorageService.delete_file(asset.storage_key)
                except Exception as e:
                    # ファイル削除失敗はログに記録するが処理は続行
                    logger.warning(
                        f"Failed to delete file: {asset.storage_key}, error: {e}"
                    )

                # 4. MediaAsset論理削除
                asset.is_deleted = True
                asset.save(update_fields=['is_deleted'])

        # 5. ProblemMediaAsset論理削除
        related_links.update(is_deleted=True)

        # 6. Problem論理削除
        problem.is_deleted = True
        problem.save(update_fields=['is_deleted'])
