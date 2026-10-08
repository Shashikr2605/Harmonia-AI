import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Harmonia AI — Stem Separation",
  description:
    "Upload any song and AI separates it into vocals and instrumentals instantly. Powered by Demucs.",
  keywords: ["stem separation", "vocal remover", "AI music", "Demucs"],
  openGraph: {
    title: "Harmonia AI",
    description: "AI-powered audio stem separation",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
