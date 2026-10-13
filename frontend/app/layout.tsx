import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Text → Calendar",
  description: "Paste any text, download a calendar file (.ics / .ical).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
