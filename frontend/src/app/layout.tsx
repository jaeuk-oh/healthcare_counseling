import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "보건소 의료비 지원 상담 AI",
  description: "RAG 기반 의료비 지원 정책 상담 시스템",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
