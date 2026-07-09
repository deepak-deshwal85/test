import "next-auth";
import type { DefaultSession } from "next-auth";
import "next-auth/jwt";
import type { RelayDeskRole } from "@/lib/roles";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user?: {
      role?: RelayDeskRole;
    } & DefaultSession["user"];
  }

  interface User {
    role?: RelayDeskRole;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    role?: RelayDeskRole;
  }
}
