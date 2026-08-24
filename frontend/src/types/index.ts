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
  role: "user" | "assistant";
  content: string;
}

export interface PolicyCriterion {
  label: string;
  met: boolean | null;
  confirmable_by: "phone" | "visit";
  /**
   * false 면 met === false 가 "부적격"이 아니라 "분기 판별 결과"라는 뜻이다.
   * 예: 성인암의 '보험 유형 확인'은 건강보험 가입자일 때 false 인데, 탈락이 아니라
   * 수검일·진단일을 더 확인하는 경로로 간다는 의미다.
   * 서버가 안 내려주는 구버전 응답을 대비해 optional 로 둔다 (없으면 true 취급).
   */
  decisive?: boolean;
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
  counselor_message: string;
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
  session_id: string;
}

export interface ClassifyResponse {
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
}

export interface Persona {
  id: string;
  label: string;
}

export interface TrainStartResponse {
  citizen_message: string;
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
  session_id: string;
}

export interface TrainTurnResponse {
  citizen_message: string;
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
  session_id: string | null;
}

