import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Trợ Lý Luật Giao Thông",
  description: "Giao diện chatbot theo phong cách tối, tối ưu cho hội thoại tiếng Việt.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="antialiased">{children}</body>
    </html>
  );
}
