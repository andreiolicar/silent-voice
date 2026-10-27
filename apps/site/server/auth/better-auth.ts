import { betterAuth } from 'better-auth'
import { admin, twoFactor } from 'better-auth/plugins'
import { expo } from '@better-auth/expo'
import { APIError, createAuthMiddleware, getSessionFromCtx } from 'better-auth/api'
import type { Pool } from 'pg'
import type Database from 'better-sqlite3'
import type { ServerConfig } from '../config.ts'
import { createAuthMailer, type AuthMailer } from './email.ts'

export function createAuth(config: ServerConfig, database: Pool | Database.Database, mailer: AuthMailer = createAuthMailer(config.resendApiKey, config.authEmailFrom)) {
  const enrollment = new WeakSet<object>()
  return betterAuth({
    appName: 'Silent Voice',
    baseURL: config.authUrl || config.origin,
    basePath: '/api/auth',
    secret: config.authSecret || config.sessionSecret,
    database,
    trustedOrigins: [...new Set([config.origin, ...(config.allowedOrigins || []), 'silentvoicemobile://'])],
    user: { modelName: 'auth_user' },
    account: { modelName: 'auth_account' },
    verification: { modelName: 'auth_verification' },
    session: { modelName: 'auth_session', expiresIn: 7 * 86400, updateAge: 86400, cookieCache: { enabled: false } },
    emailAndPassword: {
      enabled: true, minPasswordLength: 12, maxPasswordLength: 128,
      autoSignIn: false, requireEmailVerification: true,
      resetPasswordTokenExpiresIn: 3600, revokeSessionsOnPasswordReset: true,
      sendResetPassword: async ({ user, url }) => mailer({ to: user.email, url, kind: 'reset' }),
    },
    emailVerification: {
      expiresIn: 86400, sendOnSignUp: true, sendOnSignIn: true, autoSignInAfterVerification: false,
      sendVerificationEmail: async ({ user, url }) => mailer({ to: user.email, url, kind: 'verify' }),
    },
    advanced: { useSecureCookies: config.secureCookies, defaultCookieAttributes: { httpOnly: true, secure: config.secureCookies, sameSite: 'lax' } },
    rateLimit: {
      enabled: true, storage: 'database', modelName: 'auth_rate_limit', window: 60, max: 100,
      customRules: {
        '/sign-in/email': { window: 900, max: 5 },
        '/sign-up/email': { window: 900, max: 5 },
        '/request-password-reset': { window: 60, max: 2 },
        '/send-verification-email': { window: 60, max: 2 },
        '/two-factor/*': { window: 60, max: 10 },
      },
    },
    plugins: [admin({ defaultRole: 'user', adminRoles: ['admin'] }), twoFactor({ issuer: 'Silent Voice', schema: { twoFactor: { modelName: 'auth_two_factor' } } }), expo()],
    hooks: {
      before: createAuthMiddleware(async ctx => {
        if (ctx.path === '/change-password') ctx.body.revokeOtherSessions = true
        if (ctx.path.startsWith('/admin/')) {
          const session = await getSessionFromCtx(ctx)
          if (!session) throw new APIError('UNAUTHORIZED', { message: 'Entre novamente.' })
          if (session.user.role !== 'admin' || !session.user.emailVerified)
            throw new APIError('FORBIDDEN', { message: 'Acesso não autorizado.' })
          if (!session.user.twoFactorEnabled)
            throw new APIError('FORBIDDEN', { code: 'MFA_SETUP_REQUIRED', message: 'Configure a autenticação em duas etapas.' })
        }
        if (ctx.path === '/sign-up/email' && ['role','emailVerified','twoFactorEnabled','banned'].some(key => Object.hasOwn(ctx.body || {}, key)))
          throw new APIError('BAD_REQUEST', { message: 'Campos de cadastro inválidos.' })
        if (ctx.path === '/two-factor/verify-totp') {
          const session = await getSessionFromCtx(ctx)
          if (session && !session.user.twoFactorEnabled) enrollment.add(ctx.context)
        }
      }),
      after: createAuthMiddleware(async ctx => {
        if (ctx.context.returned instanceof APIError) return
        if ((enrollment.has(ctx.context) || ctx.path === '/two-factor/disable') && ctx.context.session) {
          await ctx.context.internalAdapter.deleteUserSessions(ctx.context.session.user.id)
        }
      }),
    },
    logger: { disabled: true },
  })
}
export type SilentVoiceAuth = ReturnType<typeof createAuth>
