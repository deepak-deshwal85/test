import type { Metadata } from "next";
import { SessionProvider } from "next-auth/react";
import { ClientProfileGuard } from "@/components/client-profile-guard";
import "./globals.css";

export const metadata: Metadata = {
  title: "RelayDesk",
  description: "Voice AI operations console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <ClientProfileGuard>{children}</ClientProfileGuard>
        </SessionProvider>
      </body>
    </html>
  );
}
