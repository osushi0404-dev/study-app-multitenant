# I007 手動テスト: backend/media をリポジトリに含める

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `git clone` 後に `ls backend/media/` を実行する | `bk/` と `org/` ディレクトリが存在する | | |
| 2 | `docker compose up -d` でコンテナを起動し、`http://localhost/media/org/personal/subjects/aws-saa/problem/q02_problem.png` にブラウザでアクセスする | 画像が表示される（200 OK） | | |
| 3 | 管理画面またはアプリ上で画像付きの問題を表示する | 問題画像が正常に表示される（壊れた画像アイコンにならない） | | |
| 4 | DB に保存されているファイルパスのいずれかを取得し、`backend/media/<パス>` が実際に存在することを確認する | ファイルが存在する | | |

結論: OK / NG
