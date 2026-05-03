export interface SourceExcerpt {
  text: string;
  article: string;
}

export interface PolicyRecommendation {
  policy_name: string;
  applicable: boolean;
  eligibility_reasoning: string;
  source_excerpts: SourceExcerpt[];
}

export interface Referral {
  team: string;
  phone: string;
  reason: string;
}

export interface QueryResponse {
  recommendations: PolicyRecommendation[];
  referral?: Referral | null;
}

export interface ChatMessage {
  role: "citizen" | "counselor";
  content: string;
}

// 수정사항-1: 체크리스트 기반 정책 판단 타입
export interface PolicyCriterion {
  label: string;
  met: boolean | null;
}

export interface PolicyChecklist {
  name: string;
  criteria: PolicyCriterion[];
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatResponse {
  citizen_message: string;
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
}

export interface ClassifyResponse {
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
}

export interface Hospital {
  name: string;
  phone: string;
  cancers: string[];
  distance_km?: number;
  lat?: number;
  lng?: number;
}

export interface HospitalOrigin {
  lat: number;
  lng: number;
}

export interface HospitalSearchResponse {
  hospitals: Hospital[];
  origin?: HospitalOrigin | null;
}
