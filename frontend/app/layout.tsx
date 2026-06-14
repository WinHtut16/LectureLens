import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "LectureLens",
  description: "Search inside your recordings by meaning. Jump to the exact moment.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
