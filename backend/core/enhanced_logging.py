"""
エラー原因特定を効率化するための拡張ログ設定
Claude Codeが効率的にエラー箇所を特定できるような詳細情報を含める
"""
import logging
import logging.handlers
import json
import traceback
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

# ログディレクトリの設定
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


class DetailedFormatter(logging.Formatter):
    """エラー原因特定に必要な詳細情報を含むフォーマッタ"""
    
    def format(self, record):
        # 基本情報
        base_info = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", str(uuid.uuid4())),
            "user_id": getattr(record, "user_id", "-"),
            "message": record.getMessage(),
            "location": {
                "file": record.pathname,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
        }
        
        # エラーレベルの場合は追加情報を収集
        if record.levelname in ["ERROR", "CRITICAL"]:
            base_info["error_context"] = self._get_error_context(record)
            
        # 例外情報がある場合
        if record.exc_info:
            base_info["exception"] = self._format_exception(record.exc_info)
            
        # カスタム属性を追加
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                try:
                    # JSON化可能な値のみ追加
                    json.dumps(value)
                    base_info[key] = value
                except (TypeError, ValueError):
                    base_info[key] = str(value)
                    
        return json.dumps(base_info, ensure_ascii=False, indent=2)
    
    def _get_error_context(self, record) -> Dict[str, Any]:
        """エラー発生時のコンテキスト情報を収集"""
        context = {}
        
        # スタックトレースの詳細
        if record.exc_info:
            tb = record.exc_info[2]
            stack_frames = []
            
            for frame_info in traceback.extract_tb(tb):
                frame_data = {
                    "file": frame_info.filename,
                    "line": frame_info.lineno,
                    "function": frame_info.name,
                    "code": frame_info.line
                }
                
                # ローカル変数の情報を取得（デバッグモード時のみ）
                if hasattr(record, 'include_locals') and record.include_locals:
                    frame = tb.tb_frame
                    while frame:
                        if frame.f_code.co_filename == frame_info.filename and frame.f_lineno == frame_info.lineno:
                            frame_data["locals"] = {
                                k: str(v)[:200] for k, v in frame.f_locals.items()
                                if not k.startswith('_')
                            }
                            break
                        frame = frame.f_back
                
                stack_frames.append(frame_data)
                
            context["stack_frames"] = stack_frames
            
        return context
    
    def _format_exception(self, exc_info) -> Dict[str, Any]:
        """例外情報を構造化"""
        exc_type, exc_value, exc_tb = exc_info
        
        return {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": traceback.format_exception(exc_type, exc_value, exc_tb)
        }


class ErrorContextMiddleware:
    """エラー発生時に詳細なコンテキスト情報を収集するミドルウェア"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
        
    def __call__(self, request):
        # リクエストIDを生成
        request.request_id = str(uuid.uuid4())
        
        try:
            response = self.get_response(request)
            
            # エラーレスポンスの場合
            if response.status_code >= 400:
                self._log_error_response(request, response)
                
            return response
            
        except Exception as e:
            self._log_exception(request, e)
            raise
    
    def _log_error_response(self, request, response):
        """エラーレスポンスの詳細をログ出力"""
        try:
            error_info = {
                "request_id": request.request_id,
                "user_id": getattr(request.user, 'id', 'anonymous'),
                "status_code": response.status_code,
                "request": {
                    "method": request.method,
                    "path": request.path,
                    "query_params": dict(request.GET),
                    "headers": self._safe_headers(request),
                }
            }
            
            # POSTデータ（センシティブ情報を除外）- エラーが発生してもログ出力を続ける
            if request.method == "POST":
                body = self._safe_body(request)
                if body is not None:
                    error_info["request"]["body"] = body
            
            # フロントエンドの操作履歴を追加
            user_actions = self._get_user_actions(request)
            if user_actions:
                error_info["user_actions"] = user_actions
                
            self.logger.error(
                f"HTTP {response.status_code} Error: {request.method} {request.path}",
                extra=error_info
            )
        except Exception as e:
            # ログ出力自体でエラーが発生しても、リクエスト処理は継続
            self.logger.error(f"Error in _log_error_response: {str(e)}")
    
    def _log_exception(self, request, exception):
        """例外の詳細をログ出力"""
        error_info = {
            "request_id": request.request_id,
            "user_id": getattr(request.user, 'id', 'anonymous'),
            "request": {
                "method": request.method,
                "path": request.path,
                "query_params": dict(request.GET),
                "headers": self._safe_headers(request),
            },
            "include_locals": True  # ローカル変数情報を含める
        }
        
        # フロントエンドの操作履歴を追加
        user_actions = self._get_user_actions(request)
        if user_actions:
            error_info["user_actions"] = user_actions
        
        # Django関連の追加情報
        if hasattr(request, 'resolver_match') and request.resolver_match:
            error_info["view"] = {
                "name": request.resolver_match.view_name,
                "args": request.resolver_match.args,
                "kwargs": request.resolver_match.kwargs
            }
            
        self.logger.exception(
            f"Unhandled exception in {request.method} {request.path}",
            extra=error_info
        )
    
    def _safe_headers(self, request):
        """センシティブな情報を除外したヘッダー"""
        safe_headers = {}
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        
        for header, value in request.headers.items():
            if header.lower() in sensitive_headers:
                safe_headers[header] = '[REDACTED]'
            else:
                safe_headers[header] = value
                
        return safe_headers
    
    def _safe_body(self, request):
        """センシティブな情報を除外したリクエストボディ"""
        try:
            # DRFのrequest.dataを優先的に使用（既に読み込み済みの場合）
            if hasattr(request, 'data'):
                body = dict(request.data)
            # POSTリクエストの場合はrequest.POSTを使用
            elif request.method == 'POST' and hasattr(request, 'POST'):
                body = dict(request.POST)
            # それ以外の場合、bodyへのアクセスは避ける
            else:
                return None
                
            # パスワードなどのセンシティブフィールドを除外
            sensitive_fields = ['password', 'password_confirm', 'token', 'secret', 'api_key', 'current_password', 'new_password']
            for field in sensitive_fields:
                if field in body:
                    body[field] = '[REDACTED]'
                    
            return body
        except Exception as e:
            # エラーが発生した場合はNoneを返す（500エラーを防ぐ）
            return None
    
    def _get_user_actions(self, request):
        """フロントエンドから送信されたユーザー操作履歴を取得"""
        try:
            user_actions_header = request.headers.get('X-User-Actions', '')
            if user_actions_header:
                return json.loads(user_actions_header)
        except Exception:
            pass
        return None


def create_logger(name: str) -> logging.Logger:
    """エラー原因特定に最適化されたロガーを作成"""
    logger = logging.getLogger(name)
    
    # ハンドラーがまだ設定されていない場合のみ追加
    if not logger.handlers:
        # JSONファイルハンドラー
        json_handler = logging.FileHandler(
            LOG_DIR / f"{name}.jsonl",
            encoding='utf-8'
        )
        json_handler.setFormatter(DetailedFormatter())
        logger.addHandler(json_handler)
        
        # コンソールハンドラー（開発環境用）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(DetailedFormatter())
        logger.addHandler(console_handler)
        
    logger.setLevel(logging.DEBUG)
    return logger


# ログ設定の更新用辞書
ENHANCED_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            '()': DetailedFormatter,
        },
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOG_DIR / 'django.log'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        'detailed_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOG_DIR / 'django_detailed.jsonl'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'error_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOG_DIR / 'errors.jsonl'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'formatter': 'detailed',
            'level': 'ERROR',
            'encoding': 'utf-8',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'detailed_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file', 'detailed_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file', 'detailed_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'app': {
            'handlers': ['console', 'file', 'detailed_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file', 'detailed_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'auth': {
            'handlers': ['console', 'file', 'detailed_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
    'root': {
        'handlers': ['console', 'file', 'detailed_file'],
        'level': 'INFO',
    }
}