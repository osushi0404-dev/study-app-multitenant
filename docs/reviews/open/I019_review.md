# I019 コードレビュー文書

## 対象
`react-hooks/exhaustive-deps` ルール有効化および依存配列修正

---

## レビューチェックリスト

### ESLint 設定
- [ ] `package.json` の `eslintConfig.rules` に `"react-hooks/exhaustive-deps": "error"` が正しく追加されている

### 依存配列修正（Pattern A: インライン化）
- [ ] `Statistics.tsx`: `loadStatistics` がエフェクト内にインライン化されており、`[period, selectedSubject]` deps が正しい
- [ ] `Settings.tsx`: `loadSettings` がエフェクト内にインライン化されており、`[]` deps が正しい
- [ ] `SubjectDetail.tsx`: `fetchSubject` がエフェクト内にインライン化されており、`[id, isOrgAdmin]` deps が正しい
- [ ] `EmailVerification.tsx`: `handleVerification` がエフェクト内にインライン化されており、`[token]` deps が正しい

### 依存配列修正（Pattern B: useCallback 化）
- [ ] `Dashboard.tsx`: `fetchDashboardData` が `useCallback([selectedSubject])` でラップされ、effect deps に `fetchDashboardData` が含まれている
- [ ] `Monitoring.tsx`: `fetchMonitoringData` が `useCallback([])` でラップされ、effect deps に `fetchMonitoringData` が含まれている
- [ ] `UserManagement.tsx`: `fetchUsers` が `useCallback([])` でラップされ、effect deps に `fetchUsers` が含まれている
- [ ] `UserEdit.tsx`: `fetchUser` が `useCallback([id])` でラップされ、effect deps に `fetchUser` が含まれている
- [ ] `QuizSession.tsx`: `handleSubmitAnswer` が `useCallback` でラップされ、effect deps に追加されている

### 依存配列修正（Pattern B 追加: useCallback 化）
- [ ] `AuthContext.tsx`: `handleLogout` が `useCallback([])` でラップされている
- [ ] `AuthContext.tsx`: `resetAutoLogoutTimer` が `useCallback([user, handleLogout])` でラップされている
- [ ] `NotificationContext.tsx`: `showAchievement`/`showStreakNotification`/`updateActiveRemindersCount` が `useCallback([])` でラップされている
- [ ] `QuizSession.tsx`: `isReviewModeRef` が追加され `loadNextProblem` が `useCallback([])` でラップされている
- [ ] `QuizSession.tsx`: `createNewSession` が `useCallback([subjectId, navigate, loadNextProblem])` でラップされている
- [ ] `QuizSession.tsx`: `loadSession` が `useCallback([navigate, loadNextProblem])` でラップされている

### 依存配列修正（Pattern C: eslint-disable-next-line）
- [ ] 各抑制コメントに理由が明記されている
- [ ] `QuizManagement.tsx`: 2 箇所の effect に抑制コメントあり（それ以外は suppress 不使用）
- [ ] `NotificationContext.tsx`: `loadUserSettingsAndScheduleReminders` のみ抑制コメントあり

### 機能デグレなし確認
- [ ] `useCallback` 化により無限レンダリングが発生していない
- [ ] `handleSubmitAnswer` の自動送信（単一選択）が二重送信にならない
- [ ] `fetchUsers` / `fetchUser` がアクション後も正常に再取得できる

### コード品質
- [ ] 不要な import（useCallback 未使用など）が残っていない
- [ ] TypeScript 型エラーが発生していない
