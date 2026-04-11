# UserRegistrationView 詳細解説

## 概要
`UserRegistrationView`は、Django REST Frameworkの`generics.CreateAPIView`を継承したクラスベースビューで、ユーザー登録機能を実装しています。

## コード解説（行番号55-144）

### 55行目: デコレータ（レート制限）
```python
@method_decorator(ratelimit(key='ip', rate='3/5m', method='POST'), name='post')
```
- `django_ratelimit`ライブラリを使用したレート制限
- IPアドレスベースで5分間に3回までのPOSTリクエストに制限
- ブルートフォース攻撃やスパム登録を防ぐセキュリティ対策

### 56-59行目: クラス定義と基本設定
```python
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
```
- `generics.CreateAPIView`: DRFのジェネリックビュー（作成専用）
- `queryset`: 全ユーザーオブジェクトを対象（実際は新規作成のみ）
- `serializer_class`: 入力検証とデータ変換用のシリアライザー指定
- `permission_classes`: 認証不要（誰でもアクセス可能）

### 61-64行目: createメソッドのオーバーライド開始
```python
def create(self, request, *args, **kwargs):
    import logging
    logger = logging.getLogger('django')

    logger.info(f"Registration attempt with data: {request.data}")
```
- 親クラスの`create`メソッドをオーバーライド
- loggingモジュールをインポート（メソッド内でのインポートは一般的でないが動作する）
- 'django'という名前のロガーを取得
- 登録試行のログを記録（デバッグ用）

### 67行目: try文開始
```python
try:
```
- 例外処理のブロック開始
- 登録処理全体をtry-exceptで包むことでエラーハンドリング

### 68行目: トランザクション開始
```python
with transaction.atomic():
```
- データベーストランザクションの開始
- ユーザー作成と関連オブジェクト作成を一つのトランザクションで実行
- エラー時は全てロールバックされる（データ整合性保証）

### 69-78行目: シリアライザーでのバリデーション
```python
serializer = self.get_serializer(data=request.data)
if not serializer.is_valid():
    logger.error(f"Validation failed: {serializer.errors}")
    return Response({
        'error': {
            'main_message': '入力内容にエラーがあります',
            'sub_message': next(iter(serializer.errors.values()))[0] if serializer.errors else None,
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)
```
- リクエストデータからシリアライザーインスタンス作成
- `is_valid()`でバリデーション実行
- バリデーション失敗時：
  - エラーログを記録
  - 構造化されたエラーレスポンスを返す
  - `sub_message`には最初のエラーメッセージを設定
  - 400 Bad Requestステータスで返却

### 80-82行目: ユーザー作成
```python
logger.info("Validation passed, creating user...")
user = serializer.save()
logger.info(f"User created successfully: {user.email}")
```
- バリデーション成功のログ記録
- `serializer.save()`でユーザーオブジェクトを作成・保存
- 作成成功のログ記録（メールアドレス付き）

### 84-90行目: メール認証送信
```python
# Send email verification
try:
    self.send_verification_email(user)
    logger.info("Email verification sent")
except Exception as email_error:
    logger.error(f"Email sending failed: {str(email_error)}", exc_info=True)
    # Continue with registration even if email fails
```
- メール送信処理を別のtry-exceptブロックで実行
- `send_verification_email`メソッドを呼び出し
- メール送信失敗時：
  - エラーログを記録（スタックトレース付き）
  - 登録処理は継続（メール送信失敗でも登録は成功とする）

### 92-95行目: 成功レスポンス
```python
return Response({
    'message': '登録完了。メール認証を行ってください。',
    'user_id': str(user.id)
}, status=status.HTTP_201_CREATED)
```
- 登録成功時のレスポンス
- メッセージとユーザーIDを返す
- 201 Created ステータス（リソース作成成功）

### 96-104行目: 例外処理
```python
except Exception as e:
    logger.error(f"Registration error: {str(e)}", exc_info=True)
    return Response({
        'error': {
            'main_message': 'エラーが発生しました',
            'sub_message': str(e) if settings.DEBUG else None,
            'details': {}
        }
    }, status=status.HTTP_400_BAD_REQUEST)
```
- 予期しない例外をキャッチ
- エラーログを記録（スタックトレース付き）
- DEBUGモードの場合のみ詳細エラーメッセージを返す
- 本番環境では詳細を隠す（セキュリティ対策）

### 106-143行目: send_verification_emailメソッド
```python
def send_verification_email(self, user):
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)
```
- 32バイトの安全なランダムトークン生成
- 24時間後の有効期限を設定

```python
EmailVerification.objects.create(
    user=user,
    token=token,
    expires_at=expires_at
)
```
- EmailVerificationモデルにトークン情報を保存

```python
# For development, skip email sending
if settings.DEBUG:
    print(f"Email verification token for {user.email}: {token}")
    return
```
- 開発環境ではメール送信をスキップ
- コンソールにトークンを出力（テスト用）

```python
verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

subject = "学習アプリ - メール認証"
message = f"""
こんにちは、

学習アプリにご登録いただき、ありがとうございます。

以下のリンクをクリックしてメール認証を完了してください：
{verification_url}

このリンクは24時間有効です。

学習アプリチーム
"""

send_mail(
    subject,
    message,
    settings.DEFAULT_FROM_EMAIL,
    [user.email],
    fail_silently=False,
)
```
- フロントエンドURLとトークンを組み合わせて認証URL作成
- 日本語のメール本文を作成
- Djangoの`send_mail`関数でメール送信
- `fail_silently=False`でエラー時に例外を発生させる

## 主な特徴

1. **セキュリティ対策**
   - レート制限によるブルートフォース攻撃防止
   - トランザクション処理によるデータ整合性保証
   - 本番環境でのエラー詳細非表示

2. **エラーハンドリング**
   - 多層的な例外処理
   - 構造化されたエラーレスポンス
   - メール送信失敗時の柔軟な対応

3. **ログ記録**
   - 各処理段階での詳細なログ
   - エラー時のスタックトレース記録

4. **開発環境対応**
   - メール送信のスキップ機能
   - デバッグ情報の条件付き表示
