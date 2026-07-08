import { auth } from "@/lib/auth";
import { isAuthDisabledForLocal, resolveApiBaseUrl } from "@/lib/runtime-config";
import { NextRequest, NextResponse } from "next/server";

const API_URL = resolveApiBaseUrl();
const skipSsoInLocal = isAuthDisabledForLocal();

async function proxy(request: NextRequest, path: string[]) {
  const session = await auth();
  if (!skipSsoInLocal && !session?.user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  if (!skipSsoInLocal && !session?.accessToken) {
    return NextResponse.json(
      { detail: "Missing OAuth access token — sign in with Cognito SSO" },
      { status: 401 },
    );
  }

  const targetPath = path.join("/");
  const url = new URL(`${API_URL}/${targetPath}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (!skipSsoInLocal && session?.accessToken) {
    headers.set("authorization", `Bearer ${session.accessToken}`);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(url.toString(), init);
  const body = await upstream.arrayBuffer();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
