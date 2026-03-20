"""
エラーログを解析してClaude Codeが理解しやすい形式で出力するコマンド
使用例:
    python manage.py analyze_logs --request-id=xxx
    python manage.py analyze_logs --last-errors=5
    python manage.py analyze_logs --time-range=10m
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'エラーログを解析してClaude Code用に整形して出力'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--request-id',
            type=str,
            help='特定のリクエストIDのログを抽出'
        )
        parser.add_argument(
            '--last-errors',
            type=int,
            default=10,
            help='直近のエラーログを指定件数分表示（デフォルト: 10）'
        )
        parser.add_argument(
            '--time-range',
            type=str,
            help='時間範囲を指定（例: 10m, 1h, 1d）'
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='特定のユーザーIDのログを抽出'
        )
        parser.add_argument(
            '--operation',
            type=str,
            help='特定の操作名のログを抽出'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'human', 'claude'],
            default='claude',
            help='出力形式（デフォルト: claude）'
        )
    
    def handle(self, *args, **options):
        # ログファイルのパス
        log_dir = Path(settings.BASE_DIR) / 'logs'
        json_log_file = log_dir / 'django_detailed.jsonl'
        error_log_file = log_dir / 'errors.jsonl'
        
        # ログファイルの存在確認
        if not json_log_file.exists() and not error_log_file.exists():
            self.stdout.write(self.style.ERROR('ログファイルが見つかりません'))
            return
        
        # ログの読み込み
        logs = self.load_logs([json_log_file, error_log_file])
        
        # フィルタリング
        filtered_logs = self.filter_logs(logs, options)
        
        if not filtered_logs:
            self.stdout.write(self.style.WARNING('該当するログが見つかりませんでした'))
            return
        
        # 出力
        if options['format'] == 'json':
            self.output_json(filtered_logs)
        elif options['format'] == 'human':
            self.output_human(filtered_logs)
        else:
            self.output_for_claude(filtered_logs)
    
    def load_logs(self, log_files: List[Path]) -> List[Dict[str, Any]]:
        """ログファイルを読み込んでパース"""
        logs = []
        
        for log_file in log_files:
            if not log_file.exists():
                continue
                
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # タイムスタンプでソート
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return logs
    
    def filter_logs(self, logs: List[Dict], options: Dict) -> List[Dict]:
        """指定された条件でログをフィルタリング"""
        filtered = logs
        
        # リクエストIDでフィルタ
        if options['request_id']:
            filtered = [log for log in filtered if log.get('request_id') == options['request_id']]
        
        # ユーザーIDでフィルタ
        if options['user_id']:
            filtered = [log for log in filtered if str(log.get('user_id')) == options['user_id']]
        
        # 操作名でフィルタ
        if options['operation']:
            filtered = [log for log in filtered if options['operation'] in str(log.get('operation', ''))]
        
        # 時間範囲でフィルタ
        if options['time_range']:
            cutoff_time = self.parse_time_range(options['time_range'])
            filtered = [
                log for log in filtered
                if self.parse_timestamp(log.get('timestamp', '')) >= cutoff_time
            ]
        
        # エラーのみを抽出する場合
        if options.get('last_errors'):
            error_logs = [log for log in filtered if log.get('level') in ['ERROR', 'CRITICAL']]
            return error_logs[:options['last_errors']]
        
        return filtered
    
    def parse_time_range(self, time_range: str) -> datetime:
        """時間範囲文字列をdatetimeに変換"""
        now = datetime.now()
        
        if time_range.endswith('m'):
            minutes = int(time_range[:-1])
            return now - timedelta(minutes=minutes)
        elif time_range.endswith('h'):
            hours = int(time_range[:-1])
            return now - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            return now - timedelta(days=days)
        else:
            return now - timedelta(hours=1)  # デフォルトは1時間
    
    def parse_timestamp(self, timestamp: str) -> datetime:
        """タイムスタンプ文字列をdatetimeに変換"""
        try:
            # ISO形式の場合
            if 'T' in timestamp:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            # 通常の形式
            else:
                return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.min
    
    def output_json(self, logs: List[Dict]):
        """JSON形式で出力"""
        self.stdout.write(json.dumps(logs, indent=2, ensure_ascii=False))
    
    def output_human(self, logs: List[Dict]):
        """人間が読みやすい形式で出力"""
        for log in logs:
            self.stdout.write(f"\n{'='*80}")
            self.stdout.write(f"時刻: {log.get('timestamp', 'N/A')}")
            self.stdout.write(f"レベル: {log.get('level', 'N/A')}")
            self.stdout.write(f"リクエストID: {log.get('request_id', 'N/A')}")
            self.stdout.write(f"ユーザーID: {log.get('user_id', 'N/A')}")
            self.stdout.write(f"操作: {log.get('operation', 'N/A')}")
            self.stdout.write(f"メッセージ: {log.get('message', 'N/A')}")
            
            if 'location' in log:
                loc = log['location']
                self.stdout.write(f"場所: {loc.get('file')}:{loc.get('line')} in {loc.get('function')}")
            
            if 'exception' in log:
                exc = log['exception']
                self.stdout.write(f"\n例外: {exc.get('type')} - {exc.get('message')}")
                if 'traceback' in exc:
                    self.stdout.write("トレースバック:")
                    for line in exc['traceback']:
                        self.stdout.write(f"  {line.strip()}")
    
    def output_for_claude(self, logs: List[Dict]):
        """Claude Code用に最適化された形式で出力"""
        # リクエストIDでグループ化
        requests = defaultdict(list)
        for log in logs:
            rid = log.get('request_id', 'no-request-id')
            requests[rid].append(log)
        
        # エラーサマリー
        self.stdout.write("## エラーログ解析レポート\n")
        self.stdout.write(f"総ログ数: {len(logs)}")
        self.stdout.write(f"エラー数: {sum(1 for log in logs if log.get('level') in ['ERROR', 'CRITICAL'])}")
        self.stdout.write(f"影響を受けたリクエスト数: {len(requests)}\n")
        
        # エラータイプの集計
        error_types = defaultdict(int)
        for log in logs:
            if 'exception' in log:
                error_types[log['exception'].get('type', 'Unknown')] += 1
        
        if error_types:
            self.stdout.write("### エラータイプ別集計:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"- {error_type}: {count}件")
            self.stdout.write("")
        
        # 各リクエストの詳細
        for rid, request_logs in list(requests.items())[:5]:  # 最大5リクエスト分
            self.stdout.write(f"\n### リクエストID: {rid}")
            
            # エラーログを優先的に表示
            error_logs = [log for log in request_logs if log.get('level') in ['ERROR', 'CRITICAL']]
            
            if error_logs:
                for error_log in error_logs:
                    self.stdout.write(f"\n#### エラー詳細:")
                    self.stdout.write(f"- 時刻: {error_log.get('timestamp')}")
                    self.stdout.write(f"- メッセージ: {error_log.get('message')}")
                    
                    if 'location' in error_log:
                        loc = error_log['location']
                        self.stdout.write(f"- 発生箇所: `{loc.get('file')}:{loc.get('line')}` in `{loc.get('function')}()`")
                    
                    if 'exception' in error_log:
                        exc = error_log['exception']
                        self.stdout.write(f"- 例外タイプ: `{exc.get('type')}`")
                        self.stdout.write(f"- エラーメッセージ: {exc.get('message')}")
                        
                        # トレースバックの重要な部分を抽出
                        if 'traceback' in exc and exc['traceback']:
                            self.stdout.write("\n#### スタックトレース（重要部分）:")
                            self.stdout.write("```python")
                            # アプリケーションコードのみを表示
                            app_traces = [
                                line for line in exc['traceback']
                                if '/backend/' in line and 'site-packages' not in line
                            ]
                            for line in app_traces[-5:]:  # 最後の5行
                                self.stdout.write(line.strip())
                            self.stdout.write("```")
                    
                    # エラーコンテキスト
                    if 'error_context' in error_log:
                        context = error_log['error_context']
                        if 'stack_frames' in context:
                            self.stdout.write("\n#### 詳細なスタック情報:")
                            for frame in context['stack_frames'][-3:]:  # 最後の3フレーム
                                self.stdout.write(f"- `{frame['file']}:{frame['line']}` in `{frame['function']}`")
                                if frame.get('code'):
                                    self.stdout.write(f"  コード: `{frame['code']}`")
                                if 'locals' in frame:
                                    self.stdout.write("  ローカル変数:")
                                    for var, value in list(frame['locals'].items())[:5]:
                                        self.stdout.write(f"    - {var}: {value}")
            
            # リクエスト情報
            request_start = next((log for log in request_logs if 'Request Started' in log.get('message', '')), None)
            if request_start and 'request' in request_start:
                req = request_start['request']
                self.stdout.write(f"\n#### リクエスト情報:")
                self.stdout.write(f"- メソッド: {req.get('method')}")
                self.stdout.write(f"- パス: {req.get('path')}")
                if req.get('query_params'):
                    self.stdout.write(f"- クエリパラメータ: {req.get('query_params')}")
                if req.get('body'):
                    self.stdout.write(f"- ボディ: {json.dumps(req.get('body'), ensure_ascii=False)}")
            
            # ユーザー操作履歴
            user_actions = None
            for log in request_logs:
                if 'user_actions' in log:
                    user_actions = log['user_actions']
                    break
            
            if user_actions:
                self.stdout.write(f"\n#### ユーザー操作履歴（エラー発生前）:")
                for action in user_actions[-10:]:  # 直近10件の操作
                    self.stdout.write(f"- [{action['timestamp']}] {action['actionType']}: {action['component']}")
                    if action.get('details'):
                        details = action['details']
                        if details.get('elementId'):
                            self.stdout.write(f"  要素: {details['elementId']}")
                        if details.get('value'):
                            self.stdout.write(f"  値: {details['value']}")
                        if details.get('path'):
                            self.stdout.write(f"  パス: {details['path']}")
        
        # 推奨アクション
        self.stdout.write("\n## 推奨される次のステップ:")
        self.stdout.write("1. 上記のエラー発生箇所のコードを確認")
        self.stdout.write("2. エラーメッセージとローカル変数の値から原因を特定")
        self.stdout.write("3. 必要に応じてデバッグログを追加して詳細を調査")