// API の型は backend/openapi.yaml から作った schema.d.ts を正にする（I493）。ここでは画面が使う短い名前を付けるだけ
import type { components } from './schema';

type Schemas = components['schemas'];

export type DashboardOverview = Schemas['DashboardOverview'];
export type DashboardRecommendationKind = Schemas['DashboardRecommendationKindEnum'];
