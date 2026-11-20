# 敵対的レビュー [I590]（別プロセス・2026-11-20 17:48）

- 見た範囲: origin/develop...c659216d49efe109568526f3e588b0d81c7b1d27
- 所要時間: 20 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（19 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I590.md の「## 必ず確かめる項目」（3 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 12 秒 | 0 | 0 | $0.1864 | ― | ― | ― |
| 2 | 報告あり | 17 秒 | 0 | 0 | $0.1967 | ― | ― | ― |
| 3 | 報告あり | 16 秒 | 0 | 0 | $0.1799 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I590] ── 観点: ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説: [`get_conditional_response` が返しうる 304・412 の両方に見出しが付くか、`etag` が無いときに応答が `None` になる分岐で 200 に付くか、`data is None` の 404 は例外なので見出しの対象外か、`get_object()` より前に条件判定が動いて他組織の画像の有無が漏れないか]

V1 の根拠（静的読解。`backend/problems/views.py:671-689`）:
- `get_conditional_response` が返す応答は 304 と 412 だけ。`response is None` のときは 200 の `HttpResponse` を作る。
- どの分岐でも、`if response is None:` の外にあるループ（684-685 行）を通る。このため 200・304・412 のすべてに `nosniff` と CSP が付く。
- `get_object()` は 672 行にあり、条件判定（676 行）より前にある。他組織の画像は 404 になり、見出しの違いから画像の有無を知られない。
- 404 は `NotFound` の例外で返り、見出しの対象外。本文を持たず、中身の漏れもない。
- `etag` が無い（checksum が空の）場合は `response` が `None` のまま 200 の経路に入る。ここでも見出しは付く。
- 上記の根拠はコードの読解だけ。実験案は出さない。TC-03 のテストが 3 状態を固定している点は、差分で確認した。

> ITEM: V1 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I590] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | TC-01 の AST 走査は `from . import utils` や `from .utils import x` のような相対 import を数えない。`ImportFrom.module` が `None` になるか、先頭に `problems` が付かないため。ただし、元の絶対 import `from problems.utils import ...` に戻した場合は確実に捕捉する。TC-02(a) も同時に落ちる。 | test_I590_review_leftovers.py:48-56 | 静的読解。通常の書き方による事故（絶対 import への復帰）は検知できるので、Low にとどめる。 |
| Low | tautology | TC-02(b) の `detect_mime` 差し替えは、元のコードに戻しても落ちない。`from ... import` で束縛済みの関数を使うため。これは計画書とテスト文書に明記されており、将来の守りとして置かれている。 | test_I590_review_leftovers.py:76-81 | 静的読解。TC-02(a) と TC-01 が実際の失敗の注入を担う。 |

V2 の結論は次のとおり。
- 元の `from problems.utils import ALLOWED_IMAGE_FORMATS, detect_mime` に戻すと、TC-01 は `['problems.utils']` で落ちる。
- 同じく戻すと、TC-02(a) は落ちる。`from problems.utils import ALLOWED_IMAGE_FORMATS` は同一の dict オブジェクトを束縛する。このため `monkeypatch.setitem` が効き、`text/plain` が許可されて `MediaMigrationError` が出ない（`DID NOT RAISE`）。
- 数え方が効くことは、TC-01 内の失敗の注入で自己検証されている。
- TC-02 のテストデータは `checksum` と `file_size_bytes` が実データと一致する。そのため、`_checked_content` は先にある大きさ・checksum の検査を通過し、MIME 判定の段階でだけ止まる。メッセージの match も実装の文言と一致する。

反証失敗（新規指摘なし）。探索した仮説:
- AST 走査の相対 import の抜け。
- `setitem` が同一オブジェクトを共有するかどうか。
- TC-02 が別の理由（大きさ・checksum の食い違い）で偶然通っていないか。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I590] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 受け入れ条件・エッジ | 0027 が止まったときの案内が「値の使い道を確かめて空にして」だけで、空にする具体的な手順（更新文など）が無い。0010 が旧列の値を `image_directory` へ写した経緯があるため、古い DB では止まりうる。ただし止まること自体が仕様で、データは失われない。コードレビューの F2 とほぼ同じ指摘 | `0027_remove_subject_image_directory.py:11-17` | 静的読解 |

反証失敗（Critical/High の新規指摘なし）。探索した仮説は次の 3 本。

1. **空白だけの値や NULL を取りこぼす**
   - 判定は `exclude(image_directory='')` なので、空文字以外はすべて数える。空白だけの `' '` も止まる。
   - 列は NOT NULL なので、NULL の抜け道は無い。
   - TC-04 は `"problems/x"` と `" "` の両方で止まることを確かめている。
2. **判定と列の削除の順序、戻し**
   - `RunPython` が `RemoveField` より前にある。
   - 判定は読むだけなので、PostgreSQL の保留中トリガーの問題は起きない。TC-04 の本物のマイグレーション経路でも通っている。
   - 戻しは `RemoveField` の逆操作で列を `default=''` で再作成する。`RunPython` の戻しは noop。
   - 流れた時点で全行が空だったので、戻しで値は失われない。
   - TC-04 は戻した後の全行が `''` であることも確かめている。
3. **判定を外しても通る見かけ上のテスト**
   - 判定の `RunPython` を除いた写しで、値があれば列が消えることを確かめている。判定が効いていることの確認になっている。
   - 例外を出す判定なので、トランザクションごとやり直せる。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: c659216d49efe109568526f3e588b0d81c7b1d27
ROUNDS: 1
VERDICT: OK
