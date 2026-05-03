export interface EventOut {
  id: string;
  event_type: string;
  event_ts_ms: number;
  source_id: string | null;
  track_id: number | null;
  zone_id: string | null;
  confidence: number | null;
  bbox: string | null;
  missing_ppe: string | null;
  clip_ref: string | null;
  clip_key: string | null;
  received_at: string;
}

export interface EventListOut {
  items: EventOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface ZoneOut {
  id: string;
  zone_id: string;
  polygon: number[][] | null;
  required_ppe: string[] | null;
  camera_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyOut {
  id: string;
  zone_id: string;
  required_ppe: string[] | null;
  active: boolean;
  created_at: string;
}

export interface SummaryBucket {
  period: string;
  ppe_violations: number;
  zone_enter: number;
  zone_exit: number;
  by_zone: Record<string, number>;
  by_ppe: Record<string, number>;
}

export interface SummaryOut {
  from_date: string;
  to_date: string;
  granularity: string;
  buckets: SummaryBucket[];
  totals: Record<string, number>;
}

export interface TrendPoint {
  ts: string;
  count: number;
}

export interface TrendOut {
  event_type: string;
  interval: string;
  series: TrendPoint[];
}

export interface ChannelOut {
  id: string;
  name: string;
  type: string;
  config: Record<string, string>;
  active: boolean;
  created_at: string;
}

export interface RuleOut {
  id: string;
  channel_id: string;
  event_type: string;
  zone_id: string | null;
  active: boolean;
  created_at: string;
}
