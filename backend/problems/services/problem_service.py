"""
問題登録・更新のビジネスロジック（サービス層）
イシュー#031対応: 画像アップロード機能の統合
イシュー#035対応: 問題削除時の関連画像の削除
I587: 画像の中身は DB（MediaAssetContent）に保存する。ファイルの置き場は使わない
"""
import hashlib
import os
import uuid
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.exceptions import ValidationError
from problems.models import (
    Problem, Choice, MediaAsset, MediaAssetContent, ProblemMediaAsset, Subject
)
from problems.utils import (
    validate_image_file,
    detect_mime,
    sanitize_filename,
    check_duplicate_filename,
    get_storage_path,
)


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
        1枚の画像ファイルを検証し、MediaAsset と中身（MediaAssetContent）を作って返す（内部メソッド）。

        作成・編集・images/upload の全部から使う共通の流れ（C7）。呼び出し側のトランザクションの中で、
        行と中身を一緒に作る（片方だけ残らない・I587）。
        ProblemMediaAsset の作成・position 採番は呼び出し側の責務。

        処理内容:
            1. 画像バリデーション（サイズ/MIME/拡張子整合/ピクセル/ファイル名安全）
            2. ファイル名のサニタイズ
            3. 重複チェック
            4. 識別用のキーの作成（UUID方式）
            5. MediaAsset と中身の作成（MIME は中身から判定した値・送り手の content_type は使わない）
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

        # 4. 識別用のキー（UUID方式・ファイルの置き場ではない）
        file_extension = os.path.splitext(sanitized_filename)[1]
        storage_key = get_storage_path(
            organization_slug=organization.slug,
            subject_slug=subject.slug,
            usage_kind=usage_kind,
            filename=f"{uuid.uuid4()}{file_extension}"
        )

        # 5. MediaAsset と中身の作成
        image_file.seek(0)
        data = image_file.read()
        asset = MediaAsset.objects.create(
            organization=organization,
            subject=subject,
            usage_kind=usage_kind,
            storage_key=storage_key,
            original_filename=sanitized_filename,
            mime_type=detect_mime(data),  # 検査（validate_image_file）を通った中身から判定した値
            file_size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            version=1,
            is_deleted=False
        )
        MediaAssetContent.objects.create(asset=asset, data=data)
        return asset

    @staticmethod
    def _discard_asset(asset: MediaAsset) -> None:
        """画像を論理削除し、中身を DB から消す（呼び出し側のトランザクションの中で・I587）"""
        asset.is_deleted = True
        asset.save(update_fields=['is_deleted'])
        MediaAssetContent.objects.filter(asset=asset).delete()

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

        画像の保存・紐づけ・削除（中身の削除を含む）はどれも DB の操作で、
        update_problem_with_images のトランザクションの中で一緒に取り消せる（I587）。

        Args:
            order: None=当該種別は無変更 / []=全削除 / 要素は existing|new。
        """
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
        seen_new_keys = set()
        for entry in order:
            if not isinstance(entry, dict):
                raise ValidationError(
                    "order 要素は existing / new のいずれかを指定してください")
            has_existing = 'existing' in entry
            has_new = 'new' in entry
            # existing / new の同時指定は不正（孤児アセット生成・あいまいさを防ぐ）
            if has_existing and has_new:
                raise ValidationError(
                    "order 要素は existing と new を同時に指定できません")
            if has_existing:
                aid = str(entry['existing'])
                if aid not in current_assets:
                    raise ValidationError(
                        "指定された既存画像は本問題に紐づいていません")
                # 同一既存アセットの重複指定は unique 制約違反（500）になるため事前に弾く
                if aid in keep_asset_ids:
                    raise ValidationError("同じ既存画像を重複して指定できません")
                keep_asset_ids.add(aid)
            elif has_new:
                new_key = entry['new']
                if new_key not in files:
                    raise ValidationError(
                        f"新規画像ファイル {new_key} が見つかりません")
                # 同一新規キーの重複指定も unique 制約違反になるため弾く
                if new_key in seen_new_keys:
                    raise ValidationError("同じ新規画像を重複して指定できません")
                seen_new_keys.add(new_key)
            else:
                raise ValidationError(
                    "order 要素は existing / new のいずれかを指定してください")

        # 4. 新しい画像を保存
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

        # 6. 外した画像の論理削除と中身の削除
        for aid, link in current_assets.items():
            if aid in keep_asset_ids:
                continue
            asset = link.asset
            # 共有判定: 当該アセットを参照する有効リンクが他に残っているか。
            # 手順5で本問題の (problem, usage_kind) リンクは全削除済みのため、ここで
            # 残るのは「他問題」または「本問題の別 usage_kind」のリンク＝いずれも共有。
            # exclude(problem) を付けると本問題の別 usage_kind 共有を見落とし、共有画像を
            # 誤って消してしまうため付けない（code-review Medium 対応）。
            shared = ProblemMediaAsset.objects.filter(
                asset=asset, is_deleted=False
            ).exists()
            if shared:
                continue  # 共有されている場合は紐づけ解除のみ（中身は消さない）
            ProblemService._discard_asset(asset)

    @staticmethod
    @transaction.atomic
    def delete_problem(problem: Problem) -> None:
        """
        問題の削除（論理削除 + ほかの問題が使っていない画像の中身の削除）

        Args:
            problem: 削除対象の問題インスタンス

        処理内容:
            1. 関連するProblemMediaAssetを取得
            2. 各画像について他の問題で使用されていないか確認
            3. 他で使用されていない場合のみ MediaAsset を論理削除し、中身を消す
            4. ProblemMediaAssetを論理削除
            5. Problemを論理削除
        """
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
                # 3. MediaAsset の論理削除と中身の削除
                ProblemService._discard_asset(asset)

        # 4. ProblemMediaAsset論理削除
        related_links.update(is_deleted=True)

        # 5. Problem論理削除
        problem.is_deleted = True
        problem.save(update_fields=['is_deleted'])
