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
  role: "user" | "assistant";
  content: string;
}
