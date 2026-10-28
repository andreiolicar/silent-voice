// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { domAnimation, LazyMotion } from 'motion/react'
import { AdminApp } from './AdminApp'
const sdk = vi.hoisted(() => ({
  getSession: vi.fn(),
  signIn: { email: vi.fn() },
  signOut: vi.fn(),
  sendVerificationEmail: vi.fn(),
  requestPasswordReset: vi.fn(),
  resetPassword: vi.fn(),
  twoFactor: {
    verifyTotp: vi.fn(),
    verifyBackupCode: vi.fn(),
    enable: vi.fn(),
    disable: vi.fn(),
  },
  listSessions: vi.fn(),
  revokeSession: vi.fn(),
  revokeOtherSessions: vi.fn(),
  changePassword: vi.fn(),
}))
vi.mock('better-auth/react', () => ({ createAuthClient: () => sdk }))
const validSession = {
  session: {
    id: 'session-1',
    token: 'session-token',
    expiresAt: new Date(Date.now() + 86400000).toISOString(),
  },
  user: {
    id: 'admin-1',
    email: 'admin@example.com',
    name: 'Admin',
    role: 'admin',
    emailVerified: true,
    twoFactorEnabled: true,
  },
}

const lead = {
  id: 'lead-1',
  name: 'Ana Souza',
  email: 'ana@example.com',
  objective: 'Conhecer o dispositivo',
  profile: 'self',
  status: 'new',
  version: 1,
  createdAt: '2026-10-15T12:00:00.000Z',
  updatedAt: '2026-10-15T12:00:00.000Z',
  duplicateEmail: true,
}
const counts = { new: 1, contacted: 0, demo_scheduled: 0, closed: 0 }
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
function setupFetch(
  overrides: (
    path: string,
    init?: RequestInit
  ) => Response | Promise<Response> | undefined = () => undefined
) {
  const call = async (path: string, init?: RequestInit) => {
    const result = await fetch(path, init)
    const data = await result.json()
    return result.ok
      ? { data, error: null }
      : {
          data: null,
          error: { status: result.status, code: data.code ?? data.error },
        }
  }
  vi.clearAllMocks()
  sdk.getSession.mockImplementation(() => call('/api/auth/get-session'))
  sdk.signIn.email.mockImplementation((body) =>
    call('/api/auth/sign-in/email', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  )
  sdk.signOut.mockImplementation(() =>
    call('/api/auth/sign-out', { method: 'POST' })
  )
  sdk.listSessions.mockResolvedValue({ data: [], error: null })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const path = String(input)
      const overridden = overrides(path, init)
      if (overridden) return overridden
      if (path === '/api/health') return response({ status: 'ok' })
      if (path === '/api/auth/get-session') return response(validSession)
      if (path === '/api/auth/sign-in/email')
        return response({
          user: validSession.user,
          token: 'token',
          redirect: false,
        })
      if (path === '/api/auth/sign-out') return response({ success: true })
      if (path === '/api/admin/leads/lead-1')
        return response({ lead, notes: [] })
      if (path.startsWith('/api/admin/leads?'))
        return response({ items: [lead], total: 1, page: 1, counts })
      return response({ error: 'NOT_FOUND' }, 404)
    })
  )
}
function mount(path = '/admin/cadastros') {
  return render(
    <LazyMotion features={domAnimation} strict>
      <MemoryRouter initialEntries={[path]}>
        <AdminApp />
      </MemoryRouter>
    </LazyMotion>
  )
}
afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('administrative workflow', () => {
  it('blocks regular users from CRM even when they have a valid session', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session'
        ? response({
            ...validSession,
            user: { ...validSession.user, role: 'user' },
          })
        : undefined
    )
    mount()
    expect(
      await screen.findByRole('heading', { name: 'Acesso restrito' })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
  })
  it('sends admins without MFA to setup before rendering any CRM', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session'
        ? response({
            ...validSession,
            user: { ...validSession.user, twoFactorEnabled: false },
          })
        : undefined
    )
    mount()
    expect(
      await screen.findByRole('heading', { name: 'Segurança da conta' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Ativar autenticador' })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
  })
  it('requires the MFA challenge and a backend session before admitting login', async () => {
    setupFetch()
    sdk.signIn.email.mockResolvedValue({
      data: { twoFactorRedirect: true },
      error: null,
    })
    sdk.twoFactor.verifyTotp.mockResolvedValue({
      data: { user: validSession.user },
      error: null,
    })
    mount('/admin/login')
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.change(await screen.findByLabelText('Código do autenticador'), {
      target: { value: '123456' },
    })
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Verificar código' }))
    expect(
      await screen.findByRole('link', { name: 'Cadastros' })
    ).toBeInTheDocument()
  })

  it('keeps enrollment backup codes visible and requires acknowledgment before confirming the authenticator', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session'
        ? response({
            ...validSession,
            user: { ...validSession.user, twoFactorEnabled: false },
          })
        : undefined
    )
    sdk.twoFactor.enable.mockResolvedValue({
      data: {
        method: 'totp',
        totpURI: 'otpauth://totp/SilentVoice?secret=ABC123&issuer=SilentVoice',
        backupCodes: ['backup-one', 'backup-two'],
      },
      error: null,
    })
    sdk.twoFactor.verifyTotp.mockResolvedValue({
      data: { status: true },
      error: null,
    })
    mount('/admin/seguranca')
    fireEvent.change(await screen.findByLabelText('Senha atual'), {
      target: { value: 'current-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ativar autenticador' }))
    expect(await screen.findByText('backup-one')).toBeInTheDocument()
    expect(screen.getByLabelText('Chave manual')).toHaveValue('ABC123')
    expect(
      screen.getByRole('button', { name: 'Confirmar autenticador' })
    ).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Primeiro código do autenticador'), {
      target: { value: '123456' },
    })
    fireEvent.click(
      screen.getByLabelText('Guardei meus códigos de recuperação')
    )
    fireEvent.click(
      screen.getByRole('button', { name: 'Confirmar autenticador' })
    )
    expect(
      await screen.findByRole('button', { name: 'Entrar novamente' })
    ).toBeInTheDocument()
    expect(screen.queryByText('backup-one')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Chave manual')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Entrar novamente' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
  })
  it('accepts a backup challenge only after the server validates it', async () => {
    setupFetch()
    sdk.signIn.email.mockResolvedValue({
      data: { twoFactorRedirect: true },
      error: null,
    })
    sdk.twoFactor.verifyBackupCode
      .mockResolvedValueOnce({
        data: null,
        error: { code: 'INVALID_BACKUP_CODE', status: 400 },
      })
      .mockResolvedValueOnce({ data: { user: validSession.user }, error: null })
    mount('/admin/login')
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Usar código de recuperação' })
    )
    fireEvent.change(screen.getByLabelText('Código de recuperação'), {
      target: { value: 'invalid-code' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar código' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Código inválido'
    )
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Código de recuperação'), {
      target: { value: 'valid-code' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar código' }))
    expect(
      await screen.findByRole('link', { name: 'Cadastros' })
    ).toBeInTheDocument()
  })
  it('does not claim a recovery email was sent when the provider fails and does not replay the POST', async () => {
    setupFetch()
    sdk.requestPasswordReset.mockResolvedValue({
      data: null,
      error: { code: 'INTERNAL_SERVER_ERROR', status: 500 },
    })
    mount('/admin/login')
    fireEvent.click(screen.getByRole('button', { name: 'Esqueci minha senha' }))
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Enviar link de recuperação' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    expect(screen.queryByText(/Se houver uma conta/)).not.toBeInTheDocument()
    expect(sdk.requestPasswordReset).toHaveBeenCalledTimes(1)
    expect(
      screen.getByRole('button', { name: 'Enviar link de recuperação' })
    ).toBeEnabled()
  })
  it('offers verification resend for unverified email and shows provider errors honestly', async () => {
    setupFetch()
    sdk.signIn.email.mockResolvedValue({
      data: null,
      error: { code: 'EMAIL_NOT_VERIFIED', status: 403 },
    })
    sdk.sendVerificationEmail.mockResolvedValue({
      data: null,
      error: { code: 'INTERNAL_SERVER_ERROR', status: 500 },
    })
    mount('/admin/login')
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Reenviar confirmação' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    expect(screen.queryByText(/Solicitação concluída/)).not.toBeInTheDocument()
  })
  it('does not admit a login response without a separately validated backend session', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session' ? response(null) : undefined
    )
    mount('/admin/login')
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
  })
  it('changes password while requesting revocation of other sessions', async () => {
    setupFetch()
    sdk.changePassword.mockResolvedValue({
      data: { token: null, user: validSession.user },
      error: null,
    })
    mount('/admin/seguranca')
    fireEvent.change(await screen.findByLabelText('Senha atual para alterar'), {
      target: { value: 'current-password' },
    })
    fireEvent.change(screen.getByLabelText('Nova senha'), {
      target: { value: 'new-strong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Alterar senha' }))
    expect(
      await screen.findByText(
        'Senha alterada. As outras sessões foram encerradas.'
      )
    ).toBeInTheDocument()
    expect(sdk.changePassword).toHaveBeenCalledWith(
      expect.objectContaining({
        currentPassword: 'current-password',
        newPassword: 'new-strong-password',
        revokeOtherSessions: true,
      })
    )
    expect(screen.getByLabelText('Nova senha')).toHaveValue('')
    expect(screen.getByLabelText('Senha atual para alterar')).toHaveValue('')
  })
  it('adopts the rotated authoritative session after password change and identifies its current-session sign-out', async () => {
    setupFetch()
    const rotated = {
      ...validSession,
      session: {
        id: 'rotated-session',
        token: 'rotated-token',
        expiresAt: new Date(Date.now() + 7 * 86400000).toISOString(),
      },
    }
    sdk.getSession
      .mockResolvedValueOnce({ data: validSession, error: null })
      .mockResolvedValue({ data: rotated, error: null })
    sdk.listSessions.mockResolvedValue({
      data: [{ ...rotated.session, userAgent: 'Rotated browser' }],
      error: null,
    })
    sdk.changePassword.mockResolvedValue({
      data: { token: 'rotated-token', user: rotated.user },
      error: null,
    })
    mount('/admin/seguranca')
    fireEvent.change(await screen.findByLabelText('Senha atual para alterar'), {
      target: { value: 'current-password' },
    })
    fireEvent.change(screen.getByLabelText('Nova senha'), {
      target: { value: 'new-strong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Alterar senha' }))
    expect(
      await screen.findByText(
        'Senha alterada. As outras sessões foram encerradas.'
      )
    ).toBeInTheDocument()
    expect(await screen.findByText('Esta sessão')).toBeInTheDocument()
    expect(screen.queryByText('Outra sessão')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sair desta sessão' }))
    expect(
      await screen.findByLabelText('Senha', { exact: true })
    ).toBeInTheDocument()
    expect(sdk.revokeSession).not.toHaveBeenCalled()
  })
  it('replaces the parent expiry timer with the authoritative rotated-session deadline', async () => {
    vi.useFakeTimers()
    setupFetch()
    const initial = {
      ...validSession,
      session: {
        ...validSession.session,
        expiresAt: new Date(Date.now() + 1000).toISOString(),
      },
    }
    const rotated = {
      ...validSession,
      session: {
        id: 'rotated-timer-session',
        token: 'rotated-timer-token',
        expiresAt: new Date(Date.now() + 86400000).toISOString(),
      },
    }
    sdk.getSession
      .mockResolvedValueOnce({ data: initial, error: null })
      .mockResolvedValue({ data: rotated, error: null })
    sdk.changePassword.mockResolvedValue({
      data: { token: rotated.session.token, user: rotated.user },
      error: null,
    })
    mount('/admin/seguranca')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    fireEvent.change(screen.getByLabelText('Senha atual para alterar'), {
      target: { value: 'current-password' },
    })
    fireEvent.change(screen.getByLabelText('Nova senha'), {
      target: { value: 'new-strong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Alterar senha' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(
      screen.getByText('Senha alterada. As outras sessões foram encerradas.')
    ).toBeInTheDocument()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500)
    })
    expect(
      screen.getByRole('heading', { name: 'Segurança da conta' })
    ).toBeInTheDocument()
    expect(
      screen.queryByLabelText('Senha', { exact: true })
    ).not.toBeInTheDocument()
  })
  it.each(['null', 'unauthorized', 'network'])(
    'requires reauthentication when password-change session validation fails: %s',
    async (failure) => {
      setupFetch()
      sdk.getSession.mockResolvedValueOnce({ data: validSession, error: null })
      if (failure === 'network')
        sdk.getSession.mockRejectedValue(new TypeError('network_lost'))
      else
        sdk.getSession.mockResolvedValue(
          failure === 'null'
            ? { data: null, error: null }
            : { data: null, error: { code: 'UNAUTHORIZED', status: 401 } }
        )
      sdk.changePassword.mockResolvedValue({
        data: { token: 'rotated-token', user: validSession.user },
        error: null,
      })
      mount('/admin/seguranca')
      fireEvent.change(
        await screen.findByLabelText('Senha atual para alterar'),
        { target: { value: 'current-password' } }
      )
      fireEvent.change(screen.getByLabelText('Nova senha'), {
        target: { value: 'new-strong-password' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Alterar senha' }))
      expect(
        await screen.findByLabelText('Senha', { exact: true })
      ).toBeInTheDocument()
      expect(
        screen.queryByRole('heading', { name: 'Segurança da conta' })
      ).not.toBeInTheDocument()
    }
  )
  it('reconfigures admin MFA only with confirmation and then requires a fresh login', async () => {
    setupFetch()
    sdk.twoFactor.disable.mockResolvedValue({
      data: { status: true },
      error: null,
    })
    mount('/admin/seguranca')
    fireEvent.change(await screen.findByLabelText('Senha para reconfigurar'), {
      target: { value: 'current-password' },
    })
    expect(
      screen.getByRole('button', { name: 'Reconfigurar autenticador' })
    ).toBeDisabled()
    fireEvent.click(
      screen.getByLabelText(
        'Quero substituir meu autenticador e encerrar todas as sessões'
      )
    )
    fireEvent.click(
      screen.getByRole('button', { name: 'Reconfigurar autenticador' })
    )
    expect(
      await screen.findByRole('button', { name: 'Entrar novamente' })
    ).toBeInTheDocument()
    expect(
      screen.queryByLabelText('Senha para reconfigurar')
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Cadastros' })
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Entrar novamente' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
  })
  it('revokes an individually selected session, refreshes the list and signs out the current session', async () => {
    setupFetch()
    const current = { ...validSession.session, userAgent: 'Current browser' }
    const other = {
      ...current,
      id: 'another-session',
      token: 'another-token',
      userAgent: 'Other device',
    }
    sdk.listSessions
      .mockResolvedValueOnce({ data: [current, other], error: null })
      .mockResolvedValue({ data: [current], error: null })
    sdk.revokeSession.mockResolvedValue({ data: { status: true }, error: null })
    mount('/admin/seguranca')
    expect(await screen.findByText('Other device')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Encerrar sessão$/ }))
    await waitFor(() =>
      expect(screen.queryByText('Other device')).not.toBeInTheDocument()
    )
    expect(screen.getByText('Current browser')).toBeInTheDocument()
    expect(sdk.revokeSession).toHaveBeenCalledWith(
      expect.objectContaining({ token: 'another-token' })
    )
    fireEvent.click(screen.getByRole('button', { name: 'Sair desta sessão' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
    expect(screen.queryByText('Current browser')).not.toBeInTheDocument()
  })
  it('ignores an older session probe that finishes after a new sign-in', async () => {
    setupFetch()
    let finishOld: ((value: unknown) => void) | undefined
    sdk.getSession.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finishOld = resolve
        })
    )
    function GoToLogin() {
      const navigate = useNavigate()
      return (
        <button onClick={() => navigate('/admin/login')}>Open login</button>
      )
    }
    render(
      <LazyMotion features={domAnimation} strict>
        <MemoryRouter initialEntries={['/admin']}>
          <GoToLogin />
          <AdminApp />
        </MemoryRouter>
      </LazyMotion>
    )
    await waitFor(() => expect(finishOld).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Open login' }))
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(
      await screen.findByRole('heading', { name: 'Visão geral' })
    ).toBeInTheDocument()
    await act(async () => {
      finishOld!({
        data: {
          ...validSession,
          user: { ...validSession.user, id: 'old-user', role: 'user' },
        },
        error: null,
      })
    })
    expect(
      screen.getByRole('heading', { name: 'Visão geral' })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Acesso restrito' })
    ).not.toBeInTheDocument()
  })
  it('removes security details and returns to login when a security action reports an expired session', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session'
        ? response({
            ...validSession,
            user: { ...validSession.user, twoFactorEnabled: false },
          })
        : undefined
    )
    sdk.twoFactor.enable.mockResolvedValue({
      data: null,
      error: { code: 'UNAUTHORIZED', status: 401 },
    })
    mount('/admin/seguranca')
    fireEvent.change(await screen.findByLabelText('Senha atual'), {
      target: { value: 'current-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ativar autenticador' }))
    expect(
      await screen.findByLabelText('Senha', { exact: true })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Segurança da conta' })
    ).not.toBeInTheDocument()
  })
  it.each([
    ['MFA_SETUP_REQUIRED', 'Segurança da conta'],
    ['FORBIDDEN', 'Acesso restrito'],
  ])(
    'obeys the backend CRM guard even for an initially approved session: %s',
    async (error, title) => {
      setupFetch((path) =>
        path.startsWith('/api/admin/leads?')
          ? response(
              {
                error:
                  error === 'MFA_SETUP_REQUIRED'
                    ? 'Configure a autenticação em duas etapas.'
                    : 'Acesso não permitido.',
                code: error,
              },
              403
            )
          : undefined
      )
      mount('/admin')
      expect(
        await screen.findByRole('heading', { name: title })
      ).toBeInTheDocument()
      expect(
        screen.queryByRole('link', { name: 'Cadastros' })
      ).not.toBeInTheDocument()
    }
  )
  it('routes an initial null session to a normal login without claiming expiration or preserved drafts', async () => {
    setupFetch((path) =>
      path === '/api/auth/get-session' ? response(null) : undefined
    )
    mount('/admin')
    expect(
      await screen.findByLabelText('E-mail', { exact: true })
    ).toBeInTheDocument()
    expect(screen.queryByText(/Sua sessão expirou/)).not.toBeInTheDocument()
    expect(screen.queryByText(/rascunhos/)).not.toBeInTheDocument()
  })
  it('reveals the complete login immediately when a field receives focus during entrance', async () => {
    setupFetch()
    mount('/admin/login')
    const email = screen.getByRole('textbox', { name: 'E-mail' })
    act(() => email.focus())
    await waitFor(() => {
      expect(email).toHaveFocus()
      expect(screen.getByRole('region', { name: 'Entrar' })).toHaveStyle({
        opacity: '1',
        transform: 'none',
      })
    })
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })

  it('shows the login without hidden entrance frames when reduced motion is preferred', () => {
    setupFetch()
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener() {},
      removeEventListener() {},
    }))
    mount('/admin/login')
    expect(screen.getByRole('region', { name: 'Entrar' })).toHaveStyle({
      opacity: '1',
      transform: 'none',
    })
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })

  it('opens one tracking page from the sidebar and filters its four real statuses', async () => {
    setupFetch((path) => {
      if (!path.startsWith('/api/admin/leads?')) return undefined
      const status = new URL(path, 'https://example.test').searchParams.get(
        'status'
      )
      const items = !status || status === 'new' ? [lead] : []
      return response({ items, total: items.length, page: 1, counts })
    })
    mount('/admin')
    const navigation = await screen.findByRole('navigation', {
      name: 'Navegação administrativa',
    })
    fireEvent.click(
      within(navigation).getByRole('link', { name: 'Acompanhamento' })
    )
    const selector = await screen.findByRole('combobox', { name: 'Status' })
    expect(selector).toHaveValue('')
    expect(within(selector).getAllByRole('option')).toHaveLength(5)
    expect(
      screen.queryByRole('navigation', { name: 'Status do acompanhamento' })
    ).not.toBeInTheDocument()
    fireEvent.change(selector, { target: { value: 'contacted' } })
    expect(
      await screen.findByText('Nenhum contato encontrado')
    ).toBeInTheDocument()
    expect(selector).toHaveValue('contacted')
    expect(
      within(navigation).getByRole('link', { name: 'Acompanhamento' })
    ).toHaveAttribute('aria-current', 'page')
  })

  it('opens the overview first and navigates to the contact register through the sidebar', async () => {
    setupFetch()
    mount('/admin')
    expect(
      await screen.findByRole('heading', { name: 'Visão geral' })
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Buscar')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Cadastros' }))
    expect(await screen.findByLabelText('Buscar')).toBeInTheDocument()
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
  })

  it('logs in through the SDK and backend session and renders actual empty state', async () => {
    setupFetch((path) =>
      path.startsWith('/api/admin/leads?')
        ? response({
            items: [],
            total: 0,
            page: 1,
            counts: { new: 0, contacted: 0, demo_scheduled: 0, closed: 0 },
          })
        : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(
      await screen.findByText('Nenhum cadastro recebido')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()
  })

  it('shows lead details, preserves a note draft after version conflict and can save it', async () => {
    let savedNote = false
    setupFetch((path, init) => {
      if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH')
        return response({ error: 'VERSION_CONFLICT' }, 409)
      if (path === '/api/admin/leads/lead-1/notes' && init?.method === 'POST') {
        if (
          JSON.parse(String(init.body)).text !== 'Ligar amanhã' ||
          init.credentials !== 'same-origin'
        )
          return response({}, 400)
        savedNote = true
        return response(
          {
            id: 'note-1',
            text: 'Ligar amanhã',
            author: 'admin@example.com',
            createdAt: '2026-10-15T13:00:00.000Z',
          },
          201
        )
      }
      if (path === '/api/admin/leads/lead-1')
        return response({
          lead,
          notes: savedNote
            ? [
                {
                  id: 'note-1',
                  text: 'Ligar amanhã',
                  author: 'admin@example.com',
                  createdAt: '2026-10-15T13:00:00.000Z',
                },
              ]
            : [],
        })
    })
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    const panel = await screen.findByRole('dialog', {
      name: 'Contato de Ana Souza',
    })
    expect(within(panel).getByText('E-mail repetido')).toBeInTheDocument()
    fireEvent.change(within(panel).getByLabelText('Nova anotação'), {
      target: { value: 'Ligar amanhã' },
    })
    fireEvent.change(within(panel).getByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(
      within(panel).getByRole('button', { name: 'Salvar status' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'atualizado por outra pessoa'
    )
    expect(within(panel).getByLabelText('Nova anotação')).toHaveValue(
      'Ligar amanhã'
    )
    fireEvent.click(
      within(panel).getByRole('button', { name: 'Adicionar anotação' })
    )
    await waitFor(() =>
      expect(within(panel).getByLabelText('Nova anotação')).toHaveValue('')
    )
    expect(within(panel).getByText('Ligar amanhã')).toBeInTheDocument()
  })

  it.each([false, true])(
    'removes private details on expiry and restores drafts only to the same user; identity changed: %s',
    async (differentUser) => {
      let expired = false
      let signedInAgain = false
      setupFetch((path) => {
        if (path === '/api/admin/leads/lead-1/notes') {
          expired = true
          return response({}, 401)
        }
        if (path === '/api/auth/get-session' && expired)
          return response({}, 401)
        if (path === '/api/auth/get-session' && signedInAgain && differentUser)
          return response({
            ...validSession,
            user: {
              ...validSession.user,
              id: 'another-admin',
              email: 'another@example.com',
            },
          })
        if (path === '/api/auth/sign-in/email') {
          expired = false
          signedInAgain = true
          return response({
            user: validSession.user,
            token: 'new-token',
            redirect: false,
          })
        }
      })
      mount()
      fireEvent.click(
        await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      )
      fireEvent.change(await screen.findByLabelText('Nova anotação'), {
        target: { value: 'Rascunho protegido' },
      })
      fireEvent.click(
        screen.getByRole('button', { name: 'Adicionar anotação' })
      )
      expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
      expect(screen.queryByText('ana@example.com')).not.toBeInTheDocument()
      fireEvent.change(screen.getByLabelText('E-mail'), {
        target: { value: 'admin@example.com' },
      })
      fireEvent.change(screen.getByLabelText('Senha'), {
        target: { value: 'password' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
      fireEvent.click(await screen.findByRole('link', { name: 'Cadastros' }))
      fireEvent.click(
        await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      )
      expect(await screen.findByLabelText('Nova anotação')).toHaveValue(
        differentUser ? '' : 'Rascunho protegido'
      )
    }
  )
  it('announces invalid credentials and clears the password for another attempt', async () => {
    setupFetch((path) =>
      path === '/api/auth/sign-in/email' ? response({}, 401) : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'wrong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'E-mail ou senha incorretos'
    )
    expect(screen.getByLabelText('Senha')).toHaveValue('')
    await waitFor(() => expect(screen.getByLabelText('Senha')).toHaveFocus())
    expect(screen.getByLabelText('Senha')).toHaveAttribute(
      'aria-invalid',
      'true'
    )
    expect(screen.getByLabelText('Senha')).toHaveAccessibleDescription(
      'E-mail ou senha incorretos. Tente novamente.'
    )
  })

  it('keeps a retry target focused after a login service error without marking credentials invalid', async () => {
    setupFetch((path) =>
      path === '/api/auth/sign-in/email' ? response({}, 503) : undefined
    )
    mount('/admin/login')
    fireEvent.change(await screen.findByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    await waitFor(() => expect(screen.getByLabelText('Senha')).toHaveFocus())
    expect(screen.getByLabelText('Senha')).not.toHaveAttribute(
      'aria-invalid',
      'true'
    )
  })

  it('retries a failed list request and displays only the returned records', async () => {
    let failed = true
    setupFetch((path) => {
      if (path.startsWith('/api/admin/leads?') && failed) {
        failed = false
        return response({}, 503)
      }
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir'
    )
    expect(
      screen.queryByRole('button', { name: 'Ver contato de Ana Souza' })
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
  })

  it('applies search, status, dates and page while retaining the real status counts', async () => {
    setupFetch((path) => {
      if (!path.startsWith('/api/admin/leads?')) return undefined
      const query = new URL(path, 'https://example.test').searchParams
      if (query.get('page') === '2')
        return response({
          items: [{ ...lead, id: 'lead-26', name: 'Bruno Lima' }],
          total: 26,
          page: 2,
          counts: { ...counts, contacted: 26 },
        })
      if (
        query.get('q') === 'Ana' &&
        query.get('status') === 'contacted' &&
        query.get('from') === '2026-10-01' &&
        query.get('to') === '2026-10-15'
      )
        return response({
          items: [{ ...lead, status: 'contacted' }],
          total: 26,
          page: 1,
          counts: { ...counts, contacted: 26 },
        })
      return response({ items: [lead], total: 1, page: 1, counts })
    })
    mount()
    await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    fireEvent.change(screen.getByLabelText('Buscar'), {
      target: { value: 'Ana' },
    })
    fireEvent.change(screen.getByLabelText('Status'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Filtros' }))
    fireEvent.change(screen.getByLabelText('De'), {
      target: { value: '2026-10-01' },
    })
    fireEvent.change(screen.getByLabelText('Até'), {
      target: { value: '2026-10-15' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Filtrar contatos' }))
    expect(await screen.findByText('1–25 de 26 contatos')).toBeInTheDocument()
    expect(screen.getByLabelText('Status')).toHaveValue('contacted')
    expect(screen.getByRole('link', { name: 'Cadastros' })).toHaveAttribute(
      'aria-current',
      'page'
    )
    fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Bruno Lima' })
    ).toBeInTheDocument()
    expect(screen.getByText('26–26 de 26 contatos')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próxima →' })).toBeDisabled()
  })

  it('allows background navigation with inline details and returns focus after Escape', async () => {
    setupFetch()
    mount()
    const trigger = await screen.findByRole('button', {
      name: 'Ver contato de Ana Souza',
    })
    trigger.focus()
    fireEvent.click(trigger)
    const close = await screen.findByRole('button', {
      name: 'Fechar detalhes',
    })
    expect(close).toHaveFocus()
    fireEvent.change(await screen.findByLabelText('Nova anotação'), {
      target: { value: 'Um próximo passo' },
    })
    const save = screen.getByRole('button', { name: 'Adicionar anotação' })
    save.focus()
    fireEvent.keyDown(save, { key: 'Tab' })
    expect(save).toHaveFocus()
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'false')
    expect(screen.getByRole('link', { name: 'Cadastros' })).toBeInTheDocument()
    fireEvent.keyDown(close, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
  it('aborts replaced list queries and prevents their late responses replacing current results', async () => {
    let completeOld: ((value: Response) => void) | undefined
    let oldSignal: AbortSignal | undefined
    setupFetch()
    const original = globalThis.fetch
    vi.stubGlobal(
      'fetch',
      async (input: string | URL | Request, init?: RequestInit) => {
        if (String(input) === '/api/admin/leads?page=1') {
          oldSignal = init?.signal ?? undefined
          return new Promise<Response>((resolve) => {
            completeOld = resolve
          })
        }
        return original(input, init)
      }
    )
    mount()
    await waitFor(() => expect(completeOld).toBeDefined())
    fireEvent.change(screen.getByLabelText('Buscar'), {
      target: { value: 'Atual' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Filtrar contatos' }))
    expect(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
    expect(oldSignal?.aborted).toBe(true)
    await act(async () => {
      completeOld!(
        response({
          items: [{ ...lead, name: 'Resposta antiga' }],
          total: 1,
          page: 1,
          counts,
        })
      )
    })
    await waitFor(() =>
      expect(
        screen.queryByRole('button', {
          name: 'Ver contato de Resposta antiga',
        })
      ).not.toBeInTheDocument()
    )
    expect(
      screen.getByRole('button', { name: 'Ver contato de Ana Souza' })
    ).toBeInTheDocument()
  })

  it('logs out through the SDK, removes private details and clears drafts before the next login', async () => {
    setupFetch((path, init) => {
      if (path === '/api/auth/sign-out')
        return init?.method === 'POST'
          ? response({ success: true })
          : response({}, 403)
    })
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Nova anotação'), {
      target: { value: 'Rascunho anterior' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Fechar detalhes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(await screen.findByLabelText('Senha')).toBeInTheDocument()
    expect(screen.queryByText('ana@example.com')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.click(await screen.findByRole('link', { name: 'Cadastros' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    expect(await screen.findByLabelText('Nova anotação')).toHaveValue('')
  })
  it('returns to a valid first page when a status edit removes the last match on page two', async () => {
    let changed = false
    setupFetch((path, init) => {
      if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH') {
        changed = true
        return response({ ...lead, status: 'contacted', version: 2 })
      }
      if (path.startsWith('/api/admin/leads?')) {
        const page = Number(
          new URL(path, 'https://example.test').searchParams.get('page')
        )
        const firstPage = Array.from({ length: 25 }, (_, index) => ({
          ...lead,
          id: `first-${index}`,
          name:
            index === 0 ? 'Contato da primeira página' : `Contato ${index + 1}`,
        }))
        const items = page === 2 ? (changed ? [] : [lead]) : firstPage
        return response({
          items,
          total: changed ? 25 : 26,
          page,
          counts: {
            ...counts,
            new: changed ? 25 : 26,
            contacted: changed ? 1 : 0,
          },
        })
      }
    })
    mount('/admin/acompanhamento?status=new')
    await screen.findByText('1–25 de 26 contatos')
    fireEvent.click(screen.getByRole('button', { name: 'Próxima →' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar status' }))
    await screen.findByText('Status atualizado.')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar detalhes' }))
    expect(await screen.findByText('1–25 de 25 contatos')).toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: 'Ver contato de Contato da primeira página',
      })
    ).toBeInTheDocument()
    expect(
      screen.queryByText('Nenhum contato encontrado')
    ).not.toBeInTheDocument()
    expect(screen.getByText('Página 1')).toBeInTheDocument()
  })

  it.each([false, true])(
    'restores focus after status refresh when the lead is filtered out: %s',
    async (filteredOut) => {
      let changed = false
      let completeRefresh: (() => void) | undefined
      setupFetch((path, init) => {
        if (path === '/api/admin/leads/lead-1' && init?.method === 'PATCH') {
          changed = true
          return response({ ...lead, status: 'contacted', version: 2 })
        }
        if (path.startsWith('/api/admin/leads?')) {
          const items =
            changed && filteredOut
              ? []
              : [{ ...lead, status: changed ? 'contacted' : 'new' }]
          const result = response({
            items,
            total: items.length,
            page: 1,
            counts: {
              new: changed ? 0 : 1,
              contacted: changed ? 1 : 0,
              demo_scheduled: 0,
              closed: 0,
            },
          })
          return changed
            ? new Promise<Response>((resolve) => {
                completeRefresh = () => resolve(result)
              })
            : result
        }
      })
      mount()
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      if (filteredOut) {
        fireEvent.change(screen.getByLabelText('Status'), {
          target: { value: 'new' },
        })
        await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
      }
      const original = screen.getByRole('button', {
        name: 'Ver contato de Ana Souza',
      })
      original.focus()
      fireEvent.click(original)
      fireEvent.change(await screen.findByLabelText('Status do contato'), {
        target: { value: 'contacted' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Salvar status' }))
      await screen.findByText('Status atualizado.')
      await waitFor(() => {
        expect(completeRefresh).toBeDefined()
        expect(original.isConnected).toBe(false)
      })
      await act(async () => {
        completeRefresh!()
      })
      if (filteredOut) await screen.findByText('Nenhum contato encontrado')
      else
        await waitFor(() =>
          expect(
            within(screen.getByRole('table')).getByText('Em contato')
          ).toBeInTheDocument()
        )
      expect(original.isConnected).toBe(false)
      fireEvent.keyDown(
        screen.getByRole('button', { name: 'Fechar detalhes' }),
        { key: 'Escape' }
      )
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      if (filteredOut)
        expect(
          screen.getByRole('heading', { name: 'Todos os contatos 0' })
        ).toHaveFocus()
      else
        expect(
          screen.getByRole('button', { name: 'Ver contato de Ana Souza' })
        ).toHaveFocus()
    }
  )

  it('preserves an empty note draft when changing status before writing a note', async () => {
    setupFetch()
    mount()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Ver contato de Ana Souza' })
    )
    fireEvent.change(await screen.findByLabelText('Status do contato'), {
      target: { value: 'contacted' },
    })
    expect(screen.getByLabelText('Nova anotação')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Salvar status' })).toBeEnabled()
  })
})
