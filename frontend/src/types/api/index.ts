// API の型は backend/openapi.yaml から作った schema.d.ts を正にする（I493）。ここでは画面が使う短い名前を付けるだけ
import type { components } from './schema';

type Schemas = components['schemas'];

export type DashboardOverview = Schemas['DashboardOverview'];
export type DashboardRecommendationKind = Schemas['DashboardRecommendationKindEnum'];
// 学習統計（I488）
export type DashboardAnalytics = Schemas['DashboardAnalytics'];
export type DashboardAnalyticsGranularity = Schemas['DashboardAnalyticsGranularityEnum'];
// 設定（I487）。読むときの形と、PATCH で送る形（どの項目も省略できる）
export type UserSettings = Schemas['UserSettings'];
export type PatchedUserSettings = Schemas['PatchedUserSettings'];
