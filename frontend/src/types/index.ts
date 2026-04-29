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

export interface QueryResponse {
  recommendations: PolicyRecommendation[];
}

export interface ChatMessage {
  role: "citizen" | "counselor";
  content: string;
}

export interface ChatResponse {
  citizen_message: string;
  recommendations: PolicyRecommendation[];
}
