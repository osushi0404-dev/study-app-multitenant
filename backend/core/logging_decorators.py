"""
エラー解析を効率化するためのデコレータ集
"""
import functools
import logging
import time
import uuid
from typing import Callable
from django.db import connection
from django.conf import settings
import json


def log_api_call(operation_name: str = None):
    """
    APIビューに詳細なログ出力を追加するデコレータ
    エラー発生時にClaude Codeが原因を特定しやすい情報を記録
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # リクエストIDの生成
            request_id = getattr(request, 'request_id', str(uuid.uuid4()))
            request.request_id = request_id

            # ロガーの取得
            logger = logging.getLogger('app')

            # 操作名の決定
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            # 開始時刻
            start_time = time.time()

            # リクエスト情報をログ
            request_info = {
                "request_id": request_id,
                "user_id": getattr(request.user, 'id', 'anonymous'),
                "operation": op_name,
                "request": {
                    "method": request.method,
                    "path": request.path,
                    "query_params": dict(request.GET),
                    "content_type": request.content_type,
                }
            }

            # POSTデータの記録（センシティブ情報を除外）
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if hasattr(request, 'data'):
                        body_data = dict(request.data)
                    else:
                        body_data = json.loads(request.body) if request.body else {}

                    # センシティブフィールドをマスク
                    safe_body = mask_sensitive_data(body_data)
                    request_info["request"]["body"] = safe_body
                except Exception:
                    request_info["request"]["body"] = "[Failed to parse body]"

            logger.info(f"API Request Started: {op_name}", extra=request_info)

            # DBクエリのトラッキング開始
            initial_queries = len(connection.queries) if settings.DEBUG else 0

            try:
                # 実際の処理を実行
                response = func(request, *args, **kwargs)

                # 処理時間とDBクエリ数
                duration = time.time() - start_time
                query_count = len(connection.queries) - initial_queries if settings.DEBUG else 0

                # 成功レスポンスのログ
                response_info = {
                    "request_id": request_id,
                    "user_id": getattr(request.user, 'id', 'anonymous'),
                    "operation": op_name,
                    "duration_seconds": round(duration, 3),
                    "status_code": getattr(response, 'status_code', 200),
                    "db_queries": query_count,
                }

                # デバッグモードでは実行されたクエリも記録
                if settings.DEBUG and query_count > 0:
                    response_info["executed_queries"] = connection.queries[-query_count:]

                logger.info(f"API Request Completed: {op_name}", extra=response_info)

                return response

            except Exception as e:
                # エラー時の詳細情報
                duration = time.time() - start_time
                query_count = len(connection.queries) - initial_queries if settings.DEBUG else 0

                error_info = {
                    "request_id": request_id,
                    "user_id": getattr(request.user, 'id', 'anonymous'),
                    "operation": op_name,
                    "duration_seconds": round(duration, 3),
                    "db_queries": query_count,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "view_args": args,
                    "view_kwargs": kwargs,
                }

                # デバッグモードでは追加情報を含める
                if settings.DEBUG:
                    error_info["local_variables"] = {
                        k: str(v)[:500] for k, v in locals().items()
                        if k not in ['request', 'func', 'logger']
                    }
                    if query_count > 0:
                        error_info["executed_queries"] = connection.queries[-query_count:]

                logger.exception(
                    f"API Request Failed: {op_name}",
                    extra=error_info
                )
                raise

        return wrapper
    return decorator


def log_db_operation(operation_name: str):
    """
    データベース操作に詳細なログを追加するデコレータ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('app')
            start_time = time.time()

            # DBクエリのトラッキング開始
            initial_queries = len(connection.queries) if settings.DEBUG else 0

            try:
                result = func(*args, **kwargs)

                # 成功時のログ
                duration = time.time() - start_time
                query_count = len(connection.queries) - initial_queries if settings.DEBUG else 0

                logger.debug(
                    f"DB Operation Completed: {operation_name}",
                    extra={
                        "operation": operation_name,
                        "duration_seconds": round(duration, 3),
                        "query_count": query_count,
                        "queries": connection.queries[-query_count:] if settings.DEBUG and query_count > 0 else None
                    }
                )

                return result

            except Exception as e:
                # エラー時の詳細ログ
                duration = time.time() - start_time
                query_count = len(connection.queries) - initial_queries if settings.DEBUG else 0

                logger.exception(
                    f"DB Operation Failed: {operation_name}",
                    extra={
                        "operation": operation_name,
                        "duration_seconds": round(duration, 3),
                        "query_count": query_count,
                        "error_type": type(e).__name__,
                        "queries": connection.queries[-query_count:] if settings.DEBUG and query_count > 0 else None,
                        "args": str(args)[:500],
                        "kwargs": str(kwargs)[:500],
                    }
                )
                raise

        return wrapper
    return decorator


def log_celery_task(task_name: str = None):
    """
    Celeryタスクに詳細なログを追加するデコレータ
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger('app')
            task_id = str(uuid.uuid4())
            actual_task_name = task_name or func.__name__
            start_time = time.time()

            logger.info(
                f"Celery Task Started: {actual_task_name}",
                extra={
                    "task_id": task_id,
                    "task_name": actual_task_name,
                    "args": str(args)[:500],
                    "kwargs": str(kwargs)[:500],
                }
            )

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                logger.info(
                    f"Celery Task Completed: {actual_task_name}",
                    extra={
                        "task_id": task_id,
                        "task_name": actual_task_name,
                        "duration_seconds": round(duration, 3),
                        "result": str(result)[:500] if result else None,
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.exception(
                    f"Celery Task Failed: {actual_task_name}",
                    extra={
                        "task_id": task_id,
                        "task_name": actual_task_name,
                        "duration_seconds": round(duration, 3),
                        "error_type": type(e).__name__,
                        "args": str(args)[:500],
                        "kwargs": str(kwargs)[:500],
                    }
                )
                raise

        return wrapper
    return decorator


def mask_sensitive_data(data: dict) -> dict:
    """センシティブなデータをマスクする"""
    if not isinstance(data, dict):
        return data

    sensitive_fields = [
        'password', 'token', 'secret', 'api_key', 'authorization',
        'credit_card', 'ssn', 'pin', 'cvv'
    ]

    masked_data = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            masked_data[key] = '[REDACTED]'
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value

    return masked_data
