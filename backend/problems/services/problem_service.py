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

logger = logging.getLogger(__name__)

# usage_kind ごとの画像枚数上限（作成・更新で共用・マジックナンバー排除）
MAX_IMAGES_PER_KIND = 5


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
        if question_images and len(question_images) > MAX_IMAGES_PER_KIND:
            raise ValidationError(f"問題用画像は最大{MAX_IMAGES_PER_KIND}枚までです")
        if explanation_images and len(explanation_images) > MAX_IMAGES_PER_KIND:
            raise ValidationError(f"解説用画像は最大{MAX_IMAGES_PER_KIND}枚までです")

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
    def _save_image_as_asset(
        image_file: InMemoryUploadedFile,
        usage_kind: str,
        organization,
        subject: Subject
    ) -> MediaAsset:
        """
        1枚の画像ファイルを検証・保存し MediaAsset を作成して返す（内部メソッド）。

        作成フロー・編集フローの双方から再利用する共有パイプライン（C7）。
        ProblemMediaAsset の作成・position 採番は呼び出し側の責務。

        処理内容:
            1. 画像バリデーション（サイズ/MIME/拡張子整合/ピクセル/ファイル名安全）
            2. ファイル名のサニタイズ
            3. 重複チェック
            4. ディレクトリ存在確認
            5. ファイル保存（UUID方式）
            6. MediaAsset作成
        """
        # 1. 画像バリデーション
        is_valid, error_msg = validate_image_file(image_file)
        if not is_valid:
            raise ValidationError(f"{usage_kind}画像: {error_msg}")

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
            raise ValidationError(f"{usage_kind}画像: {error_msg}")

        # 4. ディレクトリ存在確認
        directory_path = f"org/{organization.slug}/subjects/{subject.slug}/{usage_kind}"
        dir_exists, error_msg = check_directory_exists(directory_path)
        if not dir_exists:
            raise ValidationError(f"{usage_kind}画像: {error_msg}")

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
        return MediaAsset.objects.create(
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

    @staticmethod
    def _process_images(
        problem: Problem,
        images: List[InMemoryUploadedFile],
        usage_kind: str,
        organization,
        subject: Subject
    ):
        """
        画像ファイルのリストを保存し問題に紐づける（作成フロー用・内部メソッド）。

        各画像を _save_image_as_asset で保存し、position を 1 始まりで採番して
        ProblemMediaAsset を作成する。
        """
        for position, image_file in enumerate(images, start=1):
            media_asset = ProblemService._save_image_as_asset(
                image_file=image_file,
                usage_kind=usage_kind,
                organization=organization,
                subject=subject
            )
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
        question_files: Optional[Dict[str, InMemoryUploadedFile]] = None,
        explanation_files: Optional[Dict[str, InMemoryUploadedFile]] = None,
        question_order: Optional[List[Dict[str, Any]]] = None,
        explanation_order: Optional[List[Dict[str, Any]]] = None,
    ) -> Problem:
        """
        問題を画像差分と共に更新（イシュー#073）。

        基本情報・選択肢を更新し、usage_kind ごとに `*_order` 配列に基づく
        画像の追加・削除・並び替えを `@transaction.atomic` 配下で一括処理する。

        Args:
            problem: 更新対象の問題インスタンス
            validated_data: バリデーション済みの問題データ
            question_files: 問題用の新規ファイル {field_key: UploadedFile}
            explanation_files: 解説用の新規ファイル {field_key: UploadedFile}
            question_order: 問題用画像の最終並び順（None=無変更 / []=全削除）
                各要素は {"existing": "<MediaAsset UUID>"} または {"new": "<field_key>"}
            explanation_order: 解説用画像の最終並び順（仕様は question_order に同じ）

        Returns:
            Problem: 更新された問題インスタンス

        Raises:
            ValidationError: 枚数上限超過・不正 order・非自問題アセット混入・
                             新規ファイル検証失敗時（全体ロールバック）
        """
        # 画像保存に使う org/subject は問題の永続化済み subject を権威とする（SEC-1）。
        # 投稿された validated_data['subject'] を信頼して org を導出しない。
        authoritative_subject = problem.subject
        organization = authoritative_subject.organization

        # 1. 基本情報の更新
        choices_data = validated_data.pop('choices', None)
        for attr, value in validated_data.items():
            setattr(problem, attr, value)
        problem.save()

        # 2. 選択肢の更新
        if choices_data is not None:
            problem.choices.all().delete()
            for choice_data in choices_data:
                Choice.objects.create(problem=problem, **choice_data)

        # 3. 画像差分の反映（usage_kind ごと）
        ProblemService._reconcile_images(
            problem, 'problem', question_order, question_files or {},
            organization, authoritative_subject)
        ProblemService._reconcile_images(
            problem, 'explanation', explanation_order, explanation_files or {},
            organization, authoritative_subject)

        return problem

    @staticmethod
    def _reconcile_images(
        problem: Problem,
        usage_kind: str,
        order: Optional[List[Dict[str, Any]]],
        files: Dict[str, InMemoryUploadedFile],
        organization,
        subject: Subject,
    ):
        """
        usage_kind ごとの画像差分（追加・削除・並び替え）を反映する（内部メソッド）。

        順序原則（物理削除は最後）: 物理ファイル削除は非可逆でロールバック対象外のため、
        「新規ファイル保存 → link 再構築 → ★最後に物理削除」の順で実行し、途中失敗時に
        残すべきファイルが消えないようにする。

        Args:
            order: None=当該種別は無変更 / []=全削除 / 要素は existing|new。
        """
        from core.storage_service import StorageService

        # order 非送信（None）の種別は一切変更しない
        if order is None:
            return
        if not isinstance(order, list):
            raise ValidationError(f"{usage_kind}画像の順序指定（order）が不正です")
        if len(order) > MAX_IMAGES_PER_KIND:
            raise ValidationError(
                f"{usage_kind}画像は最大{MAX_IMAGES_PER_KIND}枚までです")

        # 現在の有効 link
        current = list(
            ProblemMediaAsset.objects.filter(
                problem=problem, usage_kind=usage_kind, is_deleted=False
            ).select_related('asset')
        )
        current_assets = {str(link.asset_id): link for link in current}

        # order を検証しながら「残すアセット」を決定
        keep_asset_ids = set()
        for entry in order:
            if not isinstance(entry, dict):
                raise ValidationError(
                    "order 要素は existing / new のいずれかを指定してください")
            if 'existing' in entry:
                aid = str(entry['existing'])
                if aid not in current_assets:
                    raise ValidationError(
                        "指定された既存画像は本問題に紐づいていません")
                keep_asset_ids.add(aid)
            elif 'new' in entry:
                if entry['new'] not in files:
                    raise ValidationError(
                        f"新規画像ファイル {entry['new']} が見つかりません")
            else:
                raise ValidationError(
                    "order 要素は existing / new のいずれかを指定してください")

        # 4. 新規ファイルを先に保存（物理削除の前 = 失敗時に削除へ到達させない）
        new_assets: Dict[str, MediaAsset] = {}
        for entry in order:
            if 'new' in entry:
                new_assets[entry['new']] = ProblemService._save_image_as_asset(
                    image_file=files[entry['new']],
                    usage_kind=usage_kind,
                    organization=organization,
                    subject=subject,
                )

        # 5. link 再構築（position UNIQUE 衝突回避のため delete→recreate）
        for link in current:
            link.delete()
        for position, entry in enumerate(order, start=1):
            asset = (
                current_assets[str(entry['existing'])].asset
                if 'existing' in entry else new_assets[entry['new']]
            )
            ProblemMediaAsset.objects.create(
                organization=organization,
                problem=problem,
                asset=asset,
                usage_kind=usage_kind,
                position=position,
            )

        # 6. 最後に削除対象アセットの論理削除＋物理削除（ここまで全成功時のみ）
        for aid, link in current_assets.items():
            if aid in keep_asset_ids:
                continue
            asset = link.asset
            shared = ProblemMediaAsset.objects.filter(
                asset=asset, is_deleted=False
            ).exclude(problem=problem).exists()
            if shared:
                continue  # 共有されている場合は紐づけ解除のみ（物理削除しない）
            asset.is_deleted = True
            asset.save(update_fields=['is_deleted'])
            try:
                StorageService.delete_file(asset.storage_key)
            except Exception as e:
                # 物理削除失敗はログのみで続行（DB整合優先・delete_problem 踏襲）
                logger.warning(
                    "media physical delete failed",
                    extra={
                        "problem_id": problem.id,
                        "organization_id": getattr(organization, 'id', None),
                        "asset_id": str(asset.id),
                        "storage_key": asset.storage_key,
                        "error": str(e),
                    },
                )

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
