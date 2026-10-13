import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chronos AI — Calendar Event Generator",
  description: "Turn any text into a downloadable calendar (.ics) file.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
