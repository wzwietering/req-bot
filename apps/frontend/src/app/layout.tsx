import type { Metadata } from "next";
import { Geist, Geist_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "../components/auth/AuthProvider";
import { QuotaProvider } from "../contexts/QuotaContext";
import { QuotaBanner } from "../components/layout/QuotaBanner";
import { QuotaErrorBoundary } from "../components/errors/QuotaErrorBoundary";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-ibm-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "SpecScribe - Your AI Business Analyst",
  description: "Turn conversations into code-ready specifications in minutes. SpecScribe uses a guided 8-question interview to capture precise, prioritized requirements: MUST, SHOULD, COULD.",
  keywords: "SpecScribe, AI business analyst, requirements gathering, software specifications, developer tools, project management, business analyst, requirements engineering",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${ibmPlexSans.variable} antialiased`}
      >
        <AuthProvider>
          <QuotaErrorBoundary>
            <QuotaProvider>
              <QuotaBanner />
              {children}
            </QuotaProvider>
          </QuotaErrorBoundary>
        </AuthProvider>
      </body>
    </html>
  );
}
