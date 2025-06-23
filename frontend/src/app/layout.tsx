import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YouTube 쉐도잉 시스템",
  description: "영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
