// API の型は backend/openapi.yaml から作った schema.d.ts を正にする（I493）。ここでは画面が使う短い名前を付けるだけ
import type { components } from './schema';

type Schemas = components['schemas'];

export type DashboardOverview = Schemas['DashboardOverview'];
export type DashboardRecommendationKind = Schemas['DashboardRecommendationKindEnum'];
// 難易度別の苦手（I466）
export type DashboardWeakDifficulty = Schemas['DashboardWeakDifficulty'];
// 学習統計（I488）
export type DashboardAnalytics = Schemas['DashboardAnalytics'];
export type DashboardAnalyticsGranularity = Schemas['DashboardAnalyticsGranularityEnum'];
// 設定（I487）。読むときの形と、PATCH で送る形（どの項目も省略できる）
export type UserSettings = Schemas['UserSettings'];
export type PatchedUserSettings = Schemas['PatchedUserSettings'];
// 学ぶ科目（I494）。選んだ科目・選べる自組織の科目・置き換えの本文
export type UserSubject = Schemas['UserSubject'];
export type AvailableSubject = Schemas['AvailableSubject'];
export type UserSubjectSelection = Schemas['UserSubjectSelection'];
// パスキー（I619）。一覧の 1 行・一覧・WebAuthn の options・本人確認の印・ログインの応答
export type Passkey = Schemas['Passkey'];
export type PaginatedPasskeyList = Schemas['PaginatedPasskeyList'];
export type WebAuthnOptions = Schemas['WebAuthnOptions'];
export type ReauthToken = Schemas['ReauthToken'];
export type LoginResponse = Schemas['LoginResponse'];
// メンバー管理と登録用リンク（I620）
export type Member = Schemas['Member'];
export type PaginatedMemberList = Schemas['PaginatedMemberList'];
export type RegistrationLinkIssued = Schemas['RegistrationLinkIssued'];
export type RegistrationLinkOptions = Schemas['RegistrationLinkOptions'];
