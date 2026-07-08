import NextAuth from "next-auth";
import Cognito from "next-auth/providers/cognito";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";

const cognitoIssuer = process.env.COGNITO_ISSUER;
const cognitoClientId = process.env.COGNITO_CLIENT_ID;
const cognitoClientSecret = process.env.COGNITO_CLIENT_SECRET;

const providers = [];

if (cognitoIssuer && cognitoClientId && cognitoClientSecret) {
  providers.push(
    Cognito({
      clientId: cognitoClientId,
      clientSecret: cognitoClientSecret,
      issuer: cognitoIssuer,
    }),
  );
} else {
  if (process.env.AUTH_GITHUB_ID && process.env.AUTH_GITHUB_SECRET) {
    providers.push(
      GitHub({
        clientId: process.env.AUTH_GITHUB_ID,
        clientSecret: process.env.AUTH_GITHUB_SECRET,
      }),
    );
  }
  if (process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET) {
    providers.push(
      Google({
        clientId: process.env.AUTH_GOOGLE_ID,
        clientSecret: process.env.AUTH_GOOGLE_SECRET,
      }),
    );
  }
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
