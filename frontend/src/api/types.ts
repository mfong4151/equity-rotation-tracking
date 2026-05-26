export interface RatioPoint {
  date: string;
  numerator_close: number;
  denominator_close: number;
  ratio: number;
}

export interface RatioSeries {
  id: number;
  numerator: string;
  denominator: string;
  pinned: boolean;
  points: RatioPoint[];
}

export interface GroupResponse {
  group: string;
  days: number;
  ratios: RatioSeries[];
}

export interface GroupListItem {
  name: string;
  hidden: boolean;
}

export interface AddRatioRequest {
  numerator_stock: string;
  denominator_stock: string;
  group_name?: string | null;
}

export interface RatioResponse {
  id: number;
  numerator: string;
  denominator: string;
  group_name: string | null;
  created_at: string;
}

export interface BatchTickerResult {
  ticker_symbol: string;
  ok: boolean;
  bars_added: number | null;
  latest_bar: string | null;
  error: string | null;
}

export interface BatchAddTickerResponse {
  results: BatchTickerResult[];
}
