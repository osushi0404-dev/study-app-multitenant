# plan_I019_ESLint_exhaustive-deps有効化

## 基本情報
- **計画書ID**: plan_I019_ESLint_exhaustive-deps有効化
- **関連イシュー**: I019
- **作成根拠資料**: I017 コードレビュー指摘（2026-04-01）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-03

---

## 1. 背景/目的

`eslint-plugin-react-hooks` の `react-hooks/exhaustive-deps` ルールが package.json の eslintConfig に明示されていない。
CRA（react-scripts 5.0.1）の `react-app` 継承設定では内部的に `warn` レベルで有効化されているが、
`warn` では CI 通過のまま stale closure バグが無音で蓄積する。
`error` レベルで明示し、既存の全違反を根本修正・または意図的に抑制する。

---

## 2. 受け入れ条件

- [ ] `react-hooks/exhaustive-deps` が **`error`** レベルで `package.json` の `eslintConfig.rules` に明示されている
- [ ] CI の Frontend Lint（`npx eslint src/ --ext .ts,.tsx`）がエラーなく通過する
- [ ] 既存コードの依存配列漏れがすべて修正または意図的に抑制されている（抑制箇所には理由コメントあり）

---

## 3. 影響範囲

- **Backend**: なし
- **Frontend**: `package.json`（eslintConfig） + 15 ファイル（下記一覧）
- **DB**: なし
- **Config/Infra**: なし

---

## 4. 調査結果

### 4-1. 現状の ESLint 設定

`frontend/package.json` の `eslintConfig.rules` に `react-hooks/exhaustive-deps` の記載なし。
`react-app` 継承で内部的には `warn` 扱いだが、`warn` は CI exit 0 のまま通過するため抑止力がない。

### 4-2. 違反ファイル一覧（静的調査）

| # | ファイル | 行 | 違反内容 | 修正方針 |
|---|---------|-----|---------|---------|
| 1 | `pages/Dashboard.tsx` | 77-79 | `fetchDashboardData` が deps に含まれていない | `useCallback([selectedSubject, showAchievement, showStreakNotification])` ※#14で通知関数を安定化後 |
| 2 | `pages/Statistics.tsx` | 87-89 | `loadStatistics` が deps に含まれていない | エフェクト内にインライン化 |
| 3 | `pages/Monitoring.tsx` | 134-141 | `fetchMonitoringData` が deps に含まれていない | `useCallback([])` でラップ（onClick でも使用） |
| 4 | `pages/QuizManagement.tsx` | 140-143 | `fetchProblems`/`fetchSubjects` が deps に含まれていない | `// eslint-disable-next-line`（クロージャで最新 filter を参照する意図的パターン。useCallback 化すると mount effect が filter 変更のたびに再実行されるため） |
| 5 | `pages/QuizManagement.tsx` | 146-151 | `fetchProblems`/`subjects.length` が deps に含まれていない | `// eslint-disable-next-line`（同上） |
| 6 | `pages/Settings.tsx` | 120-122 | `loadSettings` が deps に含まれていない | エフェクト内にインライン化 |
| 7 | `pages/UserManagement.tsx` | 65-67 | `fetchUsers` が deps に含まれていない | `useCallback([])` でラップ（削除後にも呼び出し） |
| 8 | `pages/SubjectDetail.tsx` | 29-35 | `fetchSubject` が deps に含まれていない | エフェクト内にインライン化 |
| 9 | `pages/UserEdit.tsx` | 70-72 | `fetchUser` が deps に含まれていない | `useCallback([id])` でラップ（保存後にも呼び出し） |
| 10 | `pages/EmailVerification.tsx` | 28-34 | `handleVerification` が deps に含まれていない | エフェクト内にインライン化 |
| 11 | `pages/QuizSession.tsx` | 73-81 | `loadSession`/`createNewSession` が deps に含まれていない | `useCallback` 化（`loadNextProblem` も `useCallback([])` 化し連鎖を解消） |
| 12 | `pages/QuizSession.tsx` | 84-93 | `handleSubmitAnswer` が deps に含まれていない | `useCallback` でラップ（onClick でも使用） |
| 13 | `contexts/AuthContext.tsx` | 287 | `resetAutoLogoutTimer` が deps に含まれていない | `handleLogout` → `useCallback([])`、`resetAutoLogoutTimer` → `useCallback([user, handleLogout])` |
| 14 | `contexts/NotificationContext.tsx` | 30-47 | `loadUserSettingsAndScheduleReminders`/`updateActiveRemindersCount` が deps に含まれていない | `showAchievement`/`showStreakNotification`/`updateActiveRemindersCount` → `useCallback([])`。`loadUserSettingsAndScheduleReminders` のみ `// eslint-disable-next-line`（scheduleReminders チェーンが複雑なため） |

**既存抑制（変更不要）:**
- `components/SubjectSelector.tsx:27,39` — 既に `// eslint-disable-line react-hooks/exhaustive-deps` 記載あり

---

## 5. 変更点一覧

### 5-1. `frontend/package.json`

```json
"rules": {
  "no-restricted-imports": [...],
  "react-hooks/exhaustive-deps": "error"   // ← 追加（warn → error: stale closure を CI でブロック）
}
```

### 5-2. `frontend/src/pages/Dashboard.tsx`

`fetchDashboardData` を `useCallback` 化。`checkForAchievements`（line 159）は `fetchDashboardData` からのみ呼ばれているため、useCallback ボディ内に移動してローカル関数にする（deps への追加が不要になり、かつ stale closure も排除できる）。

```diff
+ import React, { useState, useEffect, useCallback } from 'react';

- useEffect(() => {
-   fetchDashboardData();
- }, [selectedSubject]);
+ useEffect(() => {
+   fetchDashboardData();
+ }, [selectedSubject, fetchDashboardData]);

- const fetchDashboardData = async () => {
+ const fetchDashboardData = useCallback(async () => {
+   // checkForAchievements をここに移動（fetchDashboardData からのみ使用）
+   const checkForAchievements = (data: DashboardData) => {
+     // 既存実装をそのまま移動
+   };
    ...
    checkForAchievements(dashboardDataWithDefaults);
    ...
- };
+ }, [selectedSubject, showAchievement, showStreakNotification]);

- const checkForAchievements = (data: DashboardData) => { ... }; // ← 削除（useCallback 内へ移動）
```

### 5-3. `frontend/src/pages/Statistics.tsx`

`loadStatistics` をエフェクト内にインライン化（`period`/`selectedSubject` は既存 deps に含まれており追加不要）。

```diff
- useEffect(() => {
-   loadStatistics();
- }, [period, selectedSubject]);
-
- const loadStatistics = async () => { ... };
+ useEffect(() => {
+   const loadStatistics = async () => { ... };
+   loadStatistics();
+ }, [period, selectedSubject]);
```

### 5-4. `frontend/src/pages/Monitoring.tsx`

```diff
+ import React, { useState, useEffect, useCallback } from 'react';

- const fetchMonitoringData = async () => { ... };
+ const fetchMonitoringData = useCallback(async () => { ... }, []);

- useEffect(() => {
-   fetchMonitoringData();
-   const interval = setInterval(fetchMonitoringData, 30000);
-   return () => clearInterval(interval);
- }, []);
+ useEffect(() => {
+   fetchMonitoringData();
+   const interval = setInterval(fetchMonitoringData, 30000);
+   return () => clearInterval(interval);
+ }, [fetchMonitoringData]);
```

### 5-5. `frontend/src/pages/QuizManagement.tsx`

`exhaustive-deps` エラーは deps 配列行に報告されるため、コメントは deps 配列行の直前（または同行）に配置する。

```diff
  useEffect(() => {
    fetchProblems();
    fetchSubjects();
+ // fetchProblems/fetchSubjects はクロージャで最新 filterSubject/filterDifficulty を参照する
+ // useCallback 化すると mount effect が filter 変更のたびに再実行されるため意図的に抑制
+ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (subjects.length > 0) {
      setPage(0);
      fetchProblems();
    }
+ // fetchProblems はクロージャで最新 filter を読み取る。useCallback 化すると
+ // この effect と mount effect が二重トリガーになるため意図的に抑制
+ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSubject, filterDifficulty]);
```

### 5-6. `frontend/src/pages/Settings.tsx`

```diff
- useEffect(() => {
-   loadSettings();
- }, []);
-
- const loadSettings = async () => { ... };
+ useEffect(() => {
+   const loadSettings = async () => { ... };
+   loadSettings();
+ }, []);
```

### 5-7. `frontend/src/pages/UserManagement.tsx`

```diff
+ import React, { useState, useEffect, useCallback } from 'react';

- const fetchUsers = async () => { ... };
+ const fetchUsers = useCallback(async () => { ... }, []);

- useEffect(() => {
-   fetchUsers();
- }, []);
+ useEffect(() => {
+   fetchUsers();
+ }, [fetchUsers]);
```

### 5-8. `frontend/src/pages/SubjectDetail.tsx`

```diff
- useEffect(() => {
-   if (!isOrgAdmin) { setLoading(false); return; }
-   fetchSubject();
- }, [id, isOrgAdmin]);
-
- const fetchSubject = async () => { ... };
+ useEffect(() => {
+   if (!isOrgAdmin) { setLoading(false); return; }
+   const fetchSubject = async () => { ... };
+   fetchSubject();
+ }, [id, isOrgAdmin]);
```

### 5-9. `frontend/src/pages/UserEdit.tsx`

```diff
+ import React, { useState, useEffect, useCallback } from 'react';

- const fetchUser = async () => { ... };
+ const fetchUser = useCallback(async () => { ... }, [id]);

- useEffect(() => {
-   fetchUser();
- }, [id]);
+ useEffect(() => {
+   fetchUser();
+ }, [fetchUser]);
```

### 5-10. `frontend/src/pages/EmailVerification.tsx`

```diff
- useEffect(() => {
-   if (token) { handleVerification(token); } else { setStatus('resend'); }
- }, [token]);
-
- const handleVerification = async (verificationToken: string) => { ... };
+ useEffect(() => {
+   const handleVerification = async (verificationToken: string) => { ... };
+   if (token) { handleVerification(token); } else { setStatus('resend'); }
+ }, [token]);
```

### 5-11. `frontend/src/pages/QuizSession.tsx`

`isReviewMode` を ref 経由で参照することで `loadNextProblem` の deps を空にし、連鎖を断ち切る。
ref の同期は React 18 Concurrent Mode 対応のため `useLayoutEffect` で行う（レンダー本体での直接代入は破棄されたレンダーで ref が汚染されるリスクがあるため）。

```diff
+ import React, { useState, useEffect, useLayoutEffect, useCallback, useRef } from 'react';

+ // isReviewMode を ref 経由で参照（loadNextProblem を useCallback([]) にするため）
+ const isReviewModeRef = useRef(isReviewMode);
+ useLayoutEffect(() => {
+   isReviewModeRef.current = isReviewMode;
+ });

- const loadNextProblem = async (sessionId: string) => {
+ const loadNextProblem = useCallback(async (sessionId: string) => {
    ...
-   if (response.data.is_review_mode && !isReviewMode) {
+   if (response.data.is_review_mode && !isReviewModeRef.current) {
    ...
- };
+ }, []); // isReviewMode は ref 経由アクセスのため deps 不要

- const createNewSession = async () => {
+ const createNewSession = useCallback(async () => {
    ...
- };
+ }, [subjectId, navigate, loadNextProblem]);

- const loadSession = async (sessionId: string) => {
+ const loadSession = useCallback(async (sessionId: string) => {
    ...
- };
+ }, [navigate, loadNextProblem]);

- useEffect(() => {
-   if (id) { loadSession(id); } else { createNewSession(); }
- }, [id]);
+ useEffect(() => {
+   if (id) { loadSession(id); } else { createNewSession(); }
+ }, [id, loadSession, createNewSession]);

- const handleSubmitAnswer = async (): Promise<void> => { ... };
+ const handleSubmitAnswer = useCallback(async (): Promise<void> => {
+   ...
+ }, [session, currentProblem, selectedChoices, textAnswer, startTime]);

  useEffect(() => {
    if (singleChoiceCondition) { handleSubmitAnswer(); }
- }, [selectedChoices, currentProblem, submitting, showResult]);
+ }, [selectedChoices, currentProblem, submitting, showResult, handleSubmitAnswer]);
```

### 5-12. `frontend/src/contexts/AuthContext.tsx`

`handleLogout` → `useCallback([])`、`resetAutoLogoutTimer` → `useCallback([user, handleLogout])`。
`showErrorToast`/`showSuccessToast` はモジュールレベルの安定関数のため deps 不要。

```diff
- const handleLogout = async () => {
+ const handleLogout = useCallback(async () => {
    ...
- };
+ }, []); // refs + authService + apiClient + setUser はすべて安定

- const resetAutoLogoutTimer = () => {
+ const resetAutoLogoutTimer = useCallback(() => {
    ...
- };
+ }, [user, handleLogout]);

  useEffect(() => {
    if (!user) return;
    ...
    resetAutoLogoutTimer();
    ...
- }, [user]);
+ }, [user, resetAutoLogoutTimer]);
```

import に `useCallback` を追加。

### 5-13. `frontend/src/contexts/NotificationContext.tsx`

`showAchievement`/`showStreakNotification`/`updateActiveRemindersCount` → `useCallback([])`。
`loadUserSettingsAndScheduleReminders` は `scheduleReminders` チェーンが複雑なため mount effect のみ抑制。

```diff
+ import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

- const updateActiveRemindersCount = () => { ... };
+ const updateActiveRemindersCount = useCallback(() => { ... }, []);

- const showAchievement = (message: string) => { ... };
+ const showAchievement = useCallback((message: string) => { ... }, []);

- const showStreakNotification = (days: number) => { ... };
+ const showStreakNotification = useCallback((days: number) => { ... }, []);

  useEffect(() => {
    loadUserSettingsAndScheduleReminders();
    updateActiveRemindersCount();
    const interval = setInterval(updateActiveRemindersCount, 60000);
    return () => clearInterval(interval);
+ // loadUserSettingsAndScheduleReminders は scheduleReminders チェーンが複雑で
+ // useCallback 化すると循環参照になるため mount-only として意図的に抑制
+ // eslint-disable-next-line react-hooks/exhaustive-deps
- }, []);
+ }, [updateActiveRemindersCount]);
```

---

## 6. 実装手順

1. `frontend/package.json` に `"react-hooks/exhaustive-deps": "error"` 追加
2. **Pattern A（インライン化）**: Settings.tsx / Statistics.tsx / SubjectDetail.tsx / EmailVerification.tsx
3. **Pattern B（useCallback 化）**:
   - NotificationContext.tsx（`showAchievement`/`showStreakNotification`/`updateActiveRemindersCount`）を先に実施
   - Dashboard.tsx（通知関数が安定化された後に deps 追加）
   - Monitoring.tsx / UserManagement.tsx / UserEdit.tsx
   - AuthContext.tsx（`handleLogout` → `resetAutoLogoutTimer` の順）
   - QuizSession.tsx（`loadNextProblem` → `createNewSession`/`loadSession` → `handleSubmitAnswer` の順）
     - `isReviewModeRef` は `useLayoutEffect` で同期（render 本体への直接代入は NG）
4. **Pattern C（eslint-disable-next-line）**: QuizManagement.tsx のみ
5. CI 確認（`npx eslint src/ --ext .ts,.tsx` exit 0）

---

## 7. テスト計画

- **自動テスト**: CI Frontend Lint が exit 0 で通過することを確認
- **手動テスト**: 各画面が従来通り動作することを確認（データ取得・フォーム・クイズセッション等）

詳細: `docs/tests/open/I019_auto_test.md` / `docs/tests/open/I019_manual_test.md`

---

## 8. ロールバック

- `git revert` で package.json のルール追加を取り消し、各ファイルの変更を戻す
- 機能変更がないため DB ロールバックは不要

---

## 9. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| useCallback 化による無限レンダリング | 画面がハングアップ | QuizSession は `loadNextProblem` → `createNewSession/loadSession` の順で実装し都度 lint 確認 |
| `handleSubmitAnswer` の useCallback deps 変更による自動送信の誤動作 | クイズ回答が二重送信 | `submitting` フラグで制御済みを確認してから実装 |
| `resetAutoLogoutTimer` の useCallback 化による timer 再登録 | セッション延長が二重起動 | useEffect deps が `[user, resetAutoLogoutTimer]` であり user 変更時のみ再実行されることを確認 |
| インライン化による可読性低下 | 保守性影響 | 20 行超の場合は useCallback への変更を検討（Settings/Statistics は短いため問題なし） |

---

## 10. 承認ポイント

### セキュリティチェック
- **セキュリティ影響なし**（ESLint 設定・依存配列修正のみ。API 呼び出し・認証・データ処理のロジック変更なし）
- `exhaustive-deps` を `error` 化することで今後の stale closure バグを CI 段階でブロックできる（セキュリティ強化）

### 設計判断の明示

| 設計項目 | 根拠 | イシュー明記 / 仮定 |
|---------|------|---------|
| ルール severity を `error` に設定 | `exhaustive-deps` は正確性ルール。`warn` では CI が通過し stale closure が蓄積する | **仮定**（イシューは「warn または error」） |
| `QuizManagement.tsx` effects のみ `// eslint-disable-next-line` | `fetchProblems` を `useCallback` 化すると mount effect と filter effect が二重トリガーになるアーキテクチャ上の理由あり | **仮定** |
| `QuizSession.tsx`: `isReviewMode` を useRef 経由にして `loadNextProblem` を `useCallback([])` 化 | deps 爆発を防ぎつつ stale closure を排除するモダン React パターン | **仮定** |
| `AuthContext.tsx`: `handleLogout` → `useCallback([])`、`resetAutoLogoutTimer` → `useCallback([user, handleLogout])` | 正しく deps を宣言。user 変更時のみ timer が再セットされる意図と一致 | **仮定** |
| `NotificationContext.tsx`: 通知関数を `useCallback([])` 化して Dashboard deps に含める | 根本原因（不安定関数）を修正する正しいアプローチ | **仮定** |
