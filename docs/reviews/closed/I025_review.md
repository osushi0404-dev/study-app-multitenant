# I025 コードレビュー文書

## 対象
`@typescript-eslint/no-unused-vars` / `no-redeclare` 警告の解消

---

## レビューチェックリスト

### 未使用 import の削除
- [ ] `App.tsx`: `ThemeProvider`, `createTheme` が削除されている
- [ ] `AIQuestionGenerator.tsx`: `SettingsIcon` が削除されている
- [ ] `Dashboard.tsx`: `Link` が削除されている
- [ ] `Login.tsx`: `Alert`, `toast` が削除されている
- [ ] `Monitoring.tsx`: `Fab`, `PeopleIcon`, `NotificationsIcon` が削除されている
- [ ] `Monitoring.tsx`: `interface Alert` → `interface MonitoringAlert` に rename され、`useState<MonitoringAlert[]>` に更新されている（MUI `Alert` import は残存）
- [ ] `QuizManagement.tsx`: `Alert`, `Switch`, `FormGroup`, `Divider`, `FilterList`, `Close`, `SmartToy`, `Choice` が削除されている
- [ ] `QuizSession.tsx`: `FormControl`, `Dialog`, `DialogTitle`, `DialogContent`, `DialogActions`, `Timer`, `QuestionAnswer`, `motion`, `AnimatePresence`, `Choice`, `SubmitAnswerData` が削除されている
- [ ] `Statistics.tsx`: `Legend`, `TrendingUp`, `Assessment`, `StatisticsData` が削除されている
- [ ] `auth.service.ts`: `TokenRefreshRequest` が削除されている

### 未使用変数の削除
- [ ] `QuizSession.tsx:164`: `completeSession` の代入が削除されている
- [ ] `Register.tsx:190`: `watch` が `useForm` の分割代入から除外されている
- [ ] `UserCreate.tsx:116`: `response` の代入が削除されている（`await` 呼び出しは残存）
- [ ] `UserManagement.tsx:56`: `loading` が削除されている
- [ ] `api.ts:167`: `data` の代入が削除されている（式は残存）

### 機能デグレなし確認
- [ ] import 削除により使用中のコンポーネント・型が消えていない
- [ ] 変数削除により副作用のある式（API 呼び出し等）が消えていない
- [ ] `Monitoring.tsx` の MUI `Alert` コンポーネントが JSX で正常に動作する（`no-redeclare` 解消）
