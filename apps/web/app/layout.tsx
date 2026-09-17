import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReviewForge",
  description: "Local-first AI video editor for YouTube product review videos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
