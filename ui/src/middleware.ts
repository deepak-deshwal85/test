import { auth } from "@/lib/auth";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";
import { NextResponse } from "next/server";

const skipSsoInLocal = isAuthDisabledForLocal();

export default auth((req) => {
  if (skipSsoInLocal) {
    return NextResponse.next();
  }

  const isLoggedIn = !!req.auth;
  const isLoginPage = req.nextUrl.pathname.startsWith("/login");
  const isAuthApi = req.nextUrl.pathname.startsWith("/api/auth");
  const isBackendApi = req.nextUrl.pathname.startsWith("/api/backend");

  if (isAuthApi) {
    return NextResponse.next();
  }

  if (!isLoggedIn && isBackendApi) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  if (!isLoggedIn && !isLoginPage) {
    const login = new URL("/login", req.nextUrl.origin);
    login.searchParams.set("callbackUrl", req.nextUrl.pathname);
    return NextResponse.redirect(login);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
