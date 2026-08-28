import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "今日限定彩蛋",
  description: "一个安静、克制、略带浪漫的中文单页互动小网页。"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
