# よく使うコマンド（例）

起動:
- docker compose up -d

ログ:
- docker compose logs -f backend
- docker compose logs -f frontend

テスト（例）:
- docker compose exec backend python manage.py test
- docker compose exec frontend npm test
