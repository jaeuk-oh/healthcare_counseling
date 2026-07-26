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
  // 상담사가 시민에게 그대로 읽어줄 수 있는 제안 답변 (counselor_message와 동일 값, 하위 호환)
  suggested_reply?: string;
  // 상담사 대상 내부 브리핑 (근거·다음 확인 항목·주의사항, 시민 비노출)
  counselor_note?: string;
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
  session_id: string;
}

export type SuggestionAction = "accepted" | "edited" | "rejected";

export interface SuggestionFeedbackRequest {
  session_id?: string | null;
  turn_index: number;
  suggested_reply: string;
  final_reply?: string;
  action: SuggestionAction;
}

export interface ClassifyResponse {
  checklist: PolicyChecklist[];
  token_usage: TokenUsage;
}

