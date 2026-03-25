import type { Metadata } from "next";
import localFont from "next/font/local";
import { Gilda_Display } from "next/font/google";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

const gildaDisplay = Gilda_Display({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-gilda",
});

const bungee = localFont({
  src: "./fonts/Bungee/Bungee-Regular.ttf",
  variable: "--font-bungee",
  weight: "400",
});

export const metadata: Metadata = {
  title: "CompeteSmart",
  description: "Mastering the art of market intelligence",
};

import { SessionManager } from "@/components/SessionManager";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${gildaDisplay.variable} ${bungee.variable} antialiased`}
      >
        <SessionManager />
        {children}
      </body>
    </html>
  );
}
