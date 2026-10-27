import { isAbsolute, relative, resolve, sep } from "node:path";

export type ServerConfig = {
  port: number;
  origin: string;
  allowedOrigins?: readonly string[];
  databasePath: string;
  databaseUrl?: string;
  directDatabaseUrl?: string;
  host?: string;
  trustProxy?: boolean;
  trustedClientIpHeader?: 'cf-connecting-ip';
  frontendPath?: string;
  sessionSecret: string;
  authSecret?: string;
  authUrl?: string;
  resendApiKey?: string;
  authEmailFrom?: string;
  secureCookies: boolean;
  zaiApiKey?: string;
  zaiModel: string;
  chatTimeoutMs: number;
  idleTimeoutMs: number;
};
export function loadConfig(): ServerConfig {
  const databasePath = process.env.SQLITE_PATH || "data/silent-voice.sqlite";
  const publicRelative = relative(resolve("public"), resolve(databasePath));
  if (
    !publicRelative ||
    (!publicRelative.startsWith(`..${sep}`) &&
      publicRelative !== ".." &&
      !isAbsolute(publicRelative))
  ) {
    throw new Error(
      "SQLITE_PATH must remain outside the public asset directory",
    );
  }
  const production = process.env.NODE_ENV === "production";
  const origin = process.env.APP_ORIGIN || "http://127.0.0.1:5173";
  const allowedOrigins = [origin];
  if ((process.env.NODE_ENV || "development") === "development") {
    try {
      const local = new URL(origin);
      if (
        local.origin === origin &&
        ["http:", "https:"].includes(local.protocol) &&
        ["localhost", "127.0.0.1"].includes(local.hostname)
      ) {
        local.hostname =
          local.hostname === "localhost" ? "127.0.0.1" : "localhost";
        allowedOrigins.push(local.origin);
      }
    } catch {
      /* Invalid configured origins remain exact-only. */
    }
  }
  for (const extra of (process.env.ADDITIONAL_APP_ORIGINS || "")
    .split(",")
    .filter(Boolean)) {
    const url = new URL(extra.trim());
    if (
      url.origin !== extra.trim() ||
      (production && url.protocol !== "https:")
    )
      throw new Error("Invalid allowed origin");
    allowedOrigins.push(url.origin);
  }
  if (production && !process.env.DATABASE_URL)
    throw new Error("DATABASE_URL required in production");
  const secret = process.env.SESSION_SECRET;
  if (production && (!secret || secret.length < 32))
    throw new Error("SESSION_SECRET must contain at least 32 characters");
  return {
    port: Number(process.env.PORT || 3001),
    origin,
    allowedOrigins,
    databasePath,
    databaseUrl: process.env.DATABASE_URL,
    directDatabaseUrl: process.env.DATABASE_URL_UNPOOLED,
    host: process.env.HOST || (production ? "0.0.0.0" : "127.0.0.1"),
    trustProxy: production,
    // Render's public ingress always passes through its Cloudflare edge, which
    // overwrites this header. Never trust it on arbitrary/local deployments.
    trustedClientIpHeader: production && process.env.RENDER === 'true' ? 'cf-connecting-ip' : undefined,
    frontendPath: production ? resolve("dist") : undefined,
    authSecret: process.env.BETTER_AUTH_SECRET,
    authUrl: process.env.BETTER_AUTH_URL,
    resendApiKey: process.env.RESEND_API_KEY,
    authEmailFrom: process.env.AUTH_EMAIL_FROM,
    sessionSecret:
      secret || "local-development-only-change-before-deploy-please",
    secureCookies: production,
    zaiApiKey: process.env.ZAI_API_KEY,
    zaiModel: process.env.ZAI_MODEL || "glm-4.5-flash",
    chatTimeoutMs: 45_000,
    idleTimeoutMs: 15_000,
  };
}
