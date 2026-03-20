"""
汎用的な問題データインポートコマンド

マークダウン形式で記述された問題データをパースし、データベースに登録します。
詳細設計書: docs/detailed_design/backend/problem_data_management/
"""
import re
import os
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from problems.models import Subject, Problem, Choice

User = get_user_model()


@dataclass
class ParsedChoice:
    """パースされた選択肢データ"""
    choice_id: str  # A, B, C, D...
    text: str
    is_correct: bool
    order: int

    def __post_init__(self):
        """バリデーション"""
        if not self.choice_id or len(self.choice_id) != 1:
            raise ValueError(f"choice_idは1文字のアルファベット: {self.choice_id}")
        if not self.choice_id.isupper():
            raise ValueError(f"choice_idは大文字: {self.choice_id}")
        if not self.text or not self.text.strip():
            raise ValueError("選択肢テキストが空")
        if self.order < 1:
            raise ValueError(f"orderは1以上: {self.order}")


@dataclass
class ParsedProblem:
    """パースされた問題データ"""
    question: str
    choices: List[ParsedChoice]
    explanation: str = ""
    metadata: Dict[str, str] = None

    def __post_init__(self):
        """バリデーション"""
        if self.metadata is None:
            self.metadata = {}
        if not self.question or not self.question.strip():
            raise ValueError("問題文が空")
        if len(self.question) < 10:
            raise ValueError(f"問題文が短すぎます（10文字以上必要）: {len(self.question)}文字")
        if len(self.question) > 10000:
            raise ValueError(f"問題文が長すぎます（10000文字以下）: {len(self.question)}文字")
        if not self.choices:
            raise ValueError("選択肢が存在しない")
        if len(self.choices) < 2:
            raise ValueError("選択肢は2個以上必要")
        if not any(c.is_correct for c in self.choices):
            raise ValueError("正解が設定されていません")

    @property
    def correct_choices(self) -> List[ParsedChoice]:
        """正解の選択肢を取得"""
        return [c for c in self.choices if c.is_correct]

    @property
    def is_multiple_choice(self) -> bool:
        """複数正解問題か"""
        return len(self.correct_choices) > 1


class MarkdownParserService:
    """
    マークダウンパーサーサービス
    詳細仕様: docs/detailed_design/backend/problem_data_management/02_markdown_parser.md
    """

    # 正規表現パターン（事前コンパイル）
    PROBLEM_HEADER_PATTERN = re.compile(r'^###\s+Q(\d+)', re.MULTILINE)
    FIELD_PATTERN = re.compile(r'^\*\*(.+?)\*\*\s*[：:]\s*(.+)$', re.MULTILINE)
    CHOICE_PATTERN = re.compile(r'^[-*]\s+([A-Z])\.\s+(.+)$')

    @classmethod
    def parse(cls, markdown_content: str) -> List[ParsedProblem]:
        """
        マークダウンコンテンツをパース

        Args:
            markdown_content: マークダウンテキスト

        Returns:
            ParsedProblem のリスト

        Raises:
            ValueError: マークダウンが空の場合
        """
        if not markdown_content or not markdown_content.strip():
            raise ValueError("マークダウンコンテンツが空です")

        problems = []
        problem_sections = cls._split_by_problems(markdown_content)

        for idx, section in enumerate(problem_sections, start=1):
            try:
                parsed = cls._parse_problem_section(section)
                if parsed:
                    problems.append(parsed)
            except Exception as e:
                print(f"警告: 問題 {idx} のパース中にエラー: {e}")
                continue

        return problems

    @classmethod
    def _split_by_problems(cls, content: str) -> List[str]:
        """
        マークダウンを問題単位で分割

        Args:
            content: マークダウンテキスト

        Returns:
            問題ごとのセクションリスト
        """
        parts = cls.PROBLEM_HEADER_PATTERN.split(content)

        sections = []
        # 最初の要素は問題ヘッダー前のテキスト（無視）
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                problem_content = parts[i + 1]
                sections.append(problem_content)

        return sections

    @classmethod
    def _parse_problem_section(cls, section: str) -> Optional[ParsedProblem]:
        """
        問題セクションをパース

        Args:
            section: 問題セクションのテキスト

        Returns:
            ParsedProblem または None（失敗時）
        """
        # フィールド抽出（**キー**：値 形式）
        fields = cls._extract_fields(section)

        # 必須フィールドチェック
        if '問題文' not in fields:
            print("警告: 問題文フィールドが見つかりません")
            return None

        if '正解' not in fields:
            print("警告: 正解フィールドが見つかりません")
            return None

        # 問題文抽出
        question = fields['問題文'].strip()
        if not question:
            print("警告: 問題文が空です")
            return None

        # 選択肢パース
        choices = cls._parse_choices(section, fields['正解'])
        if not choices:
            print("警告: 選択肢のパースに失敗")
            return None

        # 正解チェック
        if not any(c.is_correct for c in choices):
            print("警告: 正解フラグが見つかりません")
            return None

        # 解説抽出
        explanation = fields.get('解説', '').strip() or ""

        # メタ情報抽出
        metadata = {}
        for key, value in fields.items():
            if key not in ['問題文', '選択肢', '正解', '解説']:
                metadata[key] = value

        try:
            return ParsedProblem(
                question=question,
                choices=choices,
                explanation=explanation,
                metadata=metadata,
            )
        except ValueError as e:
            print(f"警告: ParsedProblem作成失敗: {e}")
            return None

    @classmethod
    def _extract_fields(cls, content: str) -> Dict[str, str]:
        """
        **キー**：値 形式のフィールドを抽出

        Args:
            content: 問題セクションのテキスト

        Returns:
            {'問題文': '...', '選択肢': '...', '正解': '...', ...}
        """
        fields = {}

        for line in content.split('\n'):
            match = cls.FIELD_PATTERN.match(line.strip())
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                fields[key] = value

        return fields

    @classmethod
    def _parse_choices(cls, content: str, correct_answer: str) -> List[ParsedChoice]:
        """
        選択肢をパース（正解情報を別途受け取る）

        Args:
            content: 問題全体のテキスト
            correct_answer: 正解（例: "B" または "A,C"）

        Returns:
            ParsedChoice のリスト
        """
        choices = []
        correct_ids = set(c.strip() for c in correct_answer.split(','))

        # 選択肢行を抽出
        in_choices = False
        for line in content.split('\n'):
            # **選択肢**：の行を検出
            if '**選択肢**' in line:
                in_choices = True
                continue

            # 次のフィールドまたは水平線で終了
            if in_choices and (line.strip().startswith('**') or line.strip() == '---'):
                break

            if in_choices:
                match = cls.CHOICE_PATTERN.match(line.strip())
                if match:
                    choice_id = match.group(1)
                    choice_text = match.group(2).strip()

                    # 正解判定
                    is_correct = choice_id in correct_ids

                    # 順序計算
                    order = ord(choice_id) - ord('A') + 1

                    try:
                        choices.append(ParsedChoice(
                            choice_id=choice_id,
                            text=choice_text,
                            is_correct=is_correct,
                            order=order,
                        ))
                    except ValueError as e:
                        print(f"警告: 選択肢作成失敗: {e}")
                        continue

        return choices


class Command(BaseCommand):
    help = '汎用的な問題データインポートコマンド（全科目対応）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='マークダウンファイルのパス'
        )
        parser.add_argument(
            '--subject-id',
            type=int,
            required=True,
            help='科目ID'
        )
        parser.add_argument(
            '--created-by',
            type=str,
            default=None,
            help='作成者のメールアドレス（省略時は管理者ユーザー）'
        )
        parser.add_argument(
            '--difficulty',
            type=int,
            default=1,
            choices=[1, 2, 3],
            help='デフォルト難易度（1: 初級, 2: 中級, 3: 上級）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='テスト実行モード（実際には登録しない）'
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='重複問題をスキップ'
        )

    def handle(self, *args, **options):
        """メイン処理"""
        file_path = options['file']
        subject_id = options['subject_id']
        created_by_email = options.get('created_by')
        default_difficulty = options['difficulty']
        dry_run = options['dry_run']
        skip_duplicates = options['skip_duplicates']

        self.stdout.write(self.style.WARNING('=== 問題データインポート開始 ===\n'))

        # ファイル存在確認
        if not os.path.exists(file_path):
            raise CommandError(f'ファイルが見つかりません: {file_path}')

        # 科目確認
        try:
            subject = Subject.objects.get(id=subject_id)
            self.stdout.write(f'科目: {subject.name} (ID: {subject.id})')
        except Subject.DoesNotExist:
            raise CommandError(f'科目ID {subject_id} が見つかりません')

        # 作成者ユーザー確認
        if created_by_email:
            try:
                user = User.objects.get(email=created_by_email)
            except User.DoesNotExist:
                raise CommandError(f'ユーザーが見つかりません: {created_by_email}')
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            if not user:
                raise CommandError('ユーザーが存在しません')

        self.stdout.write(f'作成者: {user.email} (ID: {user.id})')
        self.stdout.write(f'デフォルト難易度: {default_difficulty}')
        self.stdout.write(f'モード: {"ドライラン（登録しない）" if dry_run else "本番登録"}\n')

        # ファイル読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.stdout.write(f'ファイルサイズ: {len(content)} bytes\n')

        # パース処理
        self.stdout.write('パース処理中...\n')
        try:
            parsed_problems = MarkdownParserService.parse(content)
        except Exception as e:
            raise CommandError(f'パースエラー: {e}')

        self.stdout.write(self.style.SUCCESS(f'パース完了: {len(parsed_problems)}問\n'))

        if len(parsed_problems) == 0:
            self.stdout.write(self.style.WARNING('登録する問題がありません'))
            return

        # ドライランの場合はここで終了
        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライラン完了 ==='))
            self.stdout.write(f'パースされた問題: {len(parsed_problems)}問')
            self.stdout.write('\n最初の3問:')
            for i, p in enumerate(parsed_problems[:3], start=1):
                self.stdout.write(f'{i}. {p.question[:60]}...')
                self.stdout.write(f'   選択肢数: {len(p.choices)}, 正解数: {len(p.correct_choices)}')
            return

        # DB登録処理
        self.stdout.write('DB登録処理中...\n')
        success_count = 0
        skip_count = 0
        error_count = 0

        for idx, parsed_problem in enumerate(parsed_problems, start=1):
            try:
                with transaction.atomic():
                    # 重複チェック
                    if skip_duplicates:
                        question_hash = self._generate_question_hash(parsed_problem.question)
                        if Problem.objects.filter(
                            subject=subject,
                            question=parsed_problem.question
                        ).exists():
                            self.stdout.write(f'スキップ（重複）: 問題 {idx}')
                            skip_count += 1
                            continue

                    # 問題タイプ判定
                    problem_type = 'multiple' if parsed_problem.is_multiple_choice else 'single'

                    # 問題作成
                    problem = Problem.objects.create(
                        subject=subject,
                        created_by=user,
                        question=parsed_problem.question,
                        problem_type=problem_type,
                        difficulty=default_difficulty,
                        explanation=parsed_problem.explanation,
                        points=10,
                        is_ai_generated=False
                    )

                    # 選択肢作成
                    for choice_data in parsed_problem.choices:
                        Choice.objects.create(
                            problem=problem,
                            text=choice_data.text,
                            is_correct=choice_data.is_correct,
                            order=choice_data.order
                        )

                    success_count += 1
                    if success_count % 10 == 0:
                        self.stdout.write(f'進捗: {success_count}問完了...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'エラー: 問題 {idx} - {str(e)}'))
                error_count += 1
                continue

        # 結果表示
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✅ 成功: {success_count}問'))
        if skip_count > 0:
            self.stdout.write(self.style.WARNING(f'⏭️  スキップ: {skip_count}問'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ エラー: {error_count}問'))
        self.stdout.write('=' * 50)

    def _generate_question_hash(self, question: str) -> str:
        """問題文のハッシュを生成（重複チェック用）"""
        return hashlib.md5(question.encode('utf-8')).hexdigest()
