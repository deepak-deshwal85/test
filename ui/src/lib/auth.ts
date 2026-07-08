import NextAuth from "next-auth";
import Cognito from "next-auth/providers/cognito";
import Credentials from "next-auth/providers/credentials";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";

const cognitoIssuer = process.env.COGNITO_ISSUER;
const cognitoClientId = process.env.COGNITO_CLIENT_ID;
const cognitoClientSecret = process.env.COGNITO_CLIENT_SECRET;
const authDisabledForLocal = isAuthDisabledForLocal();

const providers = [];

if (cognitoIssuer && cognitoClientId && cognitoClientSecret) {
  providers.push(
    Cognito({
      clientId: cognitoClientId,
      clientSecret: cognitoClientSecret,
      issuer: cognitoIssuer,
      // Federated IdPs (Google) return a Cognito-issued nonce that does not match
      // the value NextAuth sent; native email/password sign-in still works with PKCE.
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
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken =
        typeof token.accessToken === "string" ? token.accessToken : undefined;
      return session;
    },
  },
});
