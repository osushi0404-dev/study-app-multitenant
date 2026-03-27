"""
エラーを自動検知してClaude Code APIを呼び出し、自動修正を試みるコマンド
使用例: python manage.py watch_errors
"""
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'エラーを自動検知してClaude Codeで自動修正'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='監視間隔（秒、デフォルト: 5）'
        )
        parser.add_argument(
            '--auto-fix',
            action='store_true',
            help='自動修正を有効にする'
        )

    def handle(self, *args, **options):
        log_file = Path(settings.BASE_DIR) / 'logs' / 'errors.jsonl'
        interval = options['interval']
        auto_fix = options['auto_fix']

        if not log_file.exists():
            self.stdout.write(self.style.ERROR(f'エラーログファイルが見つかりません: {log_file}'))
            return

        self.stdout.write(f'🔍 エラー監視開始（間隔: {interval}秒）')
        if auto_fix:
            self.stdout.write('🤖 自動修正モード有効')

        # 最後に処理したファイル位置を記憶
        last_position = self._get_last_position(log_file)

        try:
            while True:
                new_errors = self._check_new_errors(log_file, last_position)

                if new_errors:
                    for error in new_errors:
                        self._handle_error(error, auto_fix)

                    # ファイル位置を更新
                    last_position = log_file.stat().st_size
                    self._save_last_position(last_position)

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('\n👋 監視を停止しました')

    def _get_last_position(self, log_file):
        """最後に読み取った位置を取得"""
        position_file = log_file.parent / '.watch_position'
        if position_file.exists():
            try:
                return int(position_file.read_text())
            except Exception:
                pass
        return 0

    def _save_last_position(self, position):
        """最後に読み取った位置を保存"""
        position_file = Path(settings.BASE_DIR) / 'logs' / '.watch_position'
        position_file.write_text(str(position))

    def _check_new_errors(self, log_file, last_position):
        """新しいエラーをチェック"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(last_position)
                new_lines = f.readlines()

            errors = []
            for line in new_lines:
                try:
                    log_entry = json.loads(line.strip())
                    if log_entry.get('level') in ['ERROR', 'CRITICAL']:
                        errors.append(log_entry)
                except json.JSONDecodeError:
                    continue

            return errors
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ログファイル読み取りエラー: {e}'))
            return []

    def _handle_error(self, error, auto_fix):
        """エラーを処理"""
        request_id = error.get('request_id', 'unknown')
        timestamp = error.get('timestamp', datetime.now().isoformat())

        self.stdout.write(f'\n🚨 エラー検知: {timestamp}')
        self.stdout.write(f'   Request ID: {request_id}')
        self.stdout.write(f'   メッセージ: {error.get("message", "Unknown error")}')

        # エラー詳細を取得
        error_analysis = self._analyze_error(request_id)

        if auto_fix:
            self._attempt_auto_fix(error_analysis)
        else:
            self.stdout.write('💡 自動修正コマンド:')
            self.stdout.write(f'   python manage.py auto_fix_error --request-id={request_id}')

    def _analyze_error(self, request_id):
        """エラーを詳細解析"""
        try:
            result = subprocess.run([
                'python', 'manage.py', 'analyze_logs',
                '--request-id', request_id,
                '--format', 'claude'
            ], capture_output=True, text=True)

            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'エラー解析失敗: {e}'))
            return None

    def _attempt_auto_fix(self, error_analysis):
        """自動修正を試行"""
        if not error_analysis:
            self.stdout.write('❌ 解析データが不足しています')
            return

        self.stdout.write('🔧 Claude Code APIに修正を依頼中...')

        # Claude Code APIを呼び出す（実装例）
        fix_result = self._call_claude_api(error_analysis)

        if fix_result:
            self.stdout.write('✅ 修正が完了しました')
            self.stdout.write('📋 変更内容を確認してください')
        else:
            self.stdout.write('❌ 自動修正に失敗しました')

    def _call_claude_api(self, error_analysis):
        """Claude Code APIを呼び出す（擬似実装）"""
        # 実際にはClaude Code APIを呼び出す
        # ここでは擬似的な処理

        prompt = f"""
以下のエラー情報を分析して、自動修正してください：

{error_analysis}

エラー箇所のファイルを特定し、修正案を提示してください。
可能であれば直接ファイルを修正してください。
"""

        # TODO: 実際のClaude Code API呼び出しを実装
        self.stdout.write('🤖 Claude Code API呼び出し（未実装）')
        self.stdout.write(f'プロンプト長: {len(prompt)} 文字')

        return False  # 現在は未実装のためFalse
