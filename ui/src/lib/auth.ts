import NextAuth from "next-auth";
import Cognito from "next-auth/providers/cognito";
import Credentials from "next-auth/providers/credentials";
import {
  emailFromIdToken,
  nameFromIdToken,
  relayDeskRoleFromIdToken,
} from "@/lib/cognito";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";
import type { RelayDeskRole } from "@/lib/roles";

const cognitoIssuer = process.env.COGNITO_ISSUER;
const cognitoClientId = process.env.COGNITO_CLIENT_ID;
const cognitoClientSecret = process.env.COGNITO_CLIENT_SECRET;
const cognitoApiScope = process.env.COGNITO_SCOPE ?? "relaydesk-api/access";
const authDisabledForLocal = isAuthDisabledForLocal();

const providers = [];

if (cognitoIssuer && cognitoClientId && cognitoClientSecret) {
  providers.push(
    Cognito({
      clientId: cognitoClientId,
      clientSecret: cognitoClientSecret,
      issuer: cognitoIssuer,
      authorization: {
        params: {
          scope: `openid email profile ${cognitoApiScope}`,
        },
      },
      checks: ["pkce", "state"],
    }),
  );
}

if (authDisabledForLocal) {
  providers.push(
    Credentials({
      name: "LocalDev",
      credentials: {},
      async authorize() {
        return {
          id: "local-dev-user",
          name: "Local Dev User",
          email: "local@example.com",
          role: "relaydesk-admins" satisfies RelayDeskRole,
        };
      },
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  trustHost: true,
  callbacks: {
    async jwt({ token, account, user }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }
      if (account?.id_token) {
        token.role = relayDeskRoleFromIdToken(account.id_token);
        const idEmail = emailFromIdToken(account.id_token);
        const idName = nameFromIdToken(account.id_token);
        if (idEmail) token.email = idEmail;
        if (idName) token.name = idName;
      } else if (user?.role) {
        token.role = user.role;
      }
      if (user?.email && !token.email) {
        token.email = user.email.toLowerCase();
      }
      if (user?.name && !token.name) {
        token.name = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken =
        typeof token.accessToken === "string" ? token.accessToken : undefined;
      if (session.user) {
        session.user.role =
          typeof token.role === "string"
            ? (token.role as RelayDeskRole)
            : "guest-clients";
        if (typeof token.email === "string") {
          session.user.email = token.email;
        }
        if (typeof token.name === "string") {
          session.user.name = token.name;
        }
      }
      return session;
    },
  },
});
