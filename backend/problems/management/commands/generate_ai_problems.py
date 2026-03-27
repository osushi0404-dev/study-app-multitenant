"""
AI問題生成管理コマンド
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from problems.models import Problem, Subject
from problems.ai_generator import AIQuestionGenerator


class Command(BaseCommand):
    help = 'AIを使用して問題を自動生成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--subject',
            type=str,
            help='問題を生成する科目名',
            required=True
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='生成する問題数 (デフォルト: 5)'
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            choices=['easy', 'medium', 'hard'],
            help='特定の難易度のみ生成'
        )
        parser.add_argument(
            '--problem-type',
            type=str,
            choices=['multiple_choice', 'essay', 'true_false'],
            default='multiple_choice',
            help='問題形式 (デフォルト: multiple_choice)'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='生成した問題をデータベースに保存'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='生成した問題をJSONファイルに出力'
        )

    def handle(self, *args, **options):
        subject_name = options['subject']
        count = options['count']
        difficulty = options['difficulty']
        problem_type = options['problem_type']
        save_to_db = options['save']
        output_file = options['output']

        try:
            # 科目の取得
            subject = Subject.objects.get(name=subject_name)
        except Subject.DoesNotExist:
            raise CommandError(f'科目 "{subject_name}" が見つかりません。')

        # AI生成器の初期化
        generator = AIQuestionGenerator()

        self.stdout.write(
            self.style.SUCCESS(f'科目 "{subject.name}" の問題を{count}個生成開始...')
        )

        generated_problems = []

        if difficulty:
            # 特定の難易度のみ生成
            for i in range(count):
                self.stdout.write(f'問題 {i+1}/{count} を生成中...')

                try:
                    problem_data = generator.generate_problem(
                        subject=subject,
                        difficulty=difficulty,
                        problem_type=problem_type
                    )
                    generated_problems.append(problem_data)

                    self.stdout.write(
                        self.style.SUCCESS(f'✓ 問題 {i+1} 生成完了')
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ 問題 {i+1} 生成失敗: {str(e)}')
                    )
        else:
            # 難易度分布による一括生成
            try:
                generated_problems = generator.generate_batch_problems(
                    subject=subject,
                    count=count
                )

                self.stdout.write(
                    self.style.SUCCESS(f'✓ {len(generated_problems)}個の問題を一括生成完了')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ 一括生成失敗: {str(e)}')
                )
                return

        # データベースに保存
        if save_to_db and generated_problems:
            self.stdout.write('データベースに保存中...')
            saved_count = 0

            for problem_data in generated_problems:
                try:
                    # Problemインスタンスの作成
                    problem = Problem(
                        title=problem_data['title'],
                        description=problem_data['description'],
                        problem_type=problem_data['problem_type'],
                        difficulty=problem_data['difficulty'],
                        subject=problem_data['subject'],
                        estimated_time_minutes=problem_data.get('estimated_time_minutes', 5),
                        created_at=timezone.now(),
                        updated_at=timezone.now()
                    )

                    # 問題形式別の追加データ
                    if problem_data['problem_type'] == 'multiple_choice':
                        problem.choices = problem_data.get('choices', [])
                        problem.correct_answer = problem_data.get('correct_answer', '')
                        problem.explanation = problem_data.get('explanation', '')

                    # メタデータの保存
                    problem.metadata = {
                        'ai_generated': problem_data.get('ai_generated', False),
                        'keywords': problem_data.get('keywords', []),
                        'learning_objectives': problem_data.get('learning_objectives', []),
                        'ai_metadata': problem_data.get('ai_metadata', {})
                    }

                    problem.save()
                    saved_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ 問題保存失敗: {str(e)}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'✓ {saved_count}個の問題をデータベースに保存完了')
            )

        # JSONファイルに出力
        if output_file and generated_problems:
            try:
                # JSON出力用にデータを整形
                output_data = []
                for problem_data in generated_problems:
                    # Subjectオブジェクトを文字列に変換
                    clean_data = problem_data.copy()
                    if 'subject' in clean_data:
                        clean_data['subject'] = clean_data['subject'].name
                    output_data.append(clean_data)

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                self.stdout.write(
                    self.style.SUCCESS(f'✓ 問題データを {output_file} に出力完了')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ ファイル出力失敗: {str(e)}')
                )

        # サマリー表示
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('生成サマリー:'))
        self.stdout.write(f'- 科目: {subject.name}')
        self.stdout.write(f'- 生成数: {len(generated_problems)}個')
        if difficulty:
            self.stdout.write(f'- 難易度: {difficulty}')
        self.stdout.write(f'- 問題形式: {problem_type}')
        if save_to_db:
            self.stdout.write('- データベース保存: 完了')
        if output_file:
            self.stdout.write(f'- ファイル出力: {output_file}')
        self.stdout.write('='*50)
