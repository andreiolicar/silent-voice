import { useRef, useState } from 'react';
import { useLocalSearchParams, useRouter, type Href } from 'expo-router';
import { AppText, Button } from '@/components/ui';
import { TextField } from '@/components/ui/TextField';
import { validateCredentials } from '@/domain/auth/policy';
import { useAuth } from '../AuthProvider';
import { authClient } from '../client';
import { AuthLayout } from '../components/AuthLayout';

type Mode =
  | 'login'
  | 'register'
  | 'verify-email'
  | 'forgot-password'
  | 'reset-password'
  | 'two-factor'
  | 'email-confirmed';
const titles: Record<Mode, string> = {
  login: 'Bem-vindo de volta',
  register: 'Crie sua conta',
  'verify-email': 'Verifique seu e-mail',
  'forgot-password': 'Recuperar senha',
  'reset-password': 'Defina uma nova senha',
  'two-factor': 'Verificação em duas etapas',
  'email-confirmed': 'E-mail confirmado',
};
const VERIFY =
  'https://www.silentvoice.com.br/conta/email-confirmado?destino=app';
const RESET =
  'https://www.silentvoice.com.br/conta/redefinir-senha?destino=app';
export default function AuthScreen({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { refresh, runAuthAction } = useAuth();
  const params = useLocalSearchParams<{
    token?: string;
    email?: string;
    completed?: string;
  }>();
  const [name, setName] = useState('');
  const [email, setEmail] = useState(params.email || '');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [code, setCode] = useState('');
  const [backup, setBackup] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState(
    params.completed === 'mfa' ? 'Segurança atualizada. Entre novamente.' : '',
  );
  const [error, setError] = useState('');
  const busy = useRef(false);
  const go = (path: string) => router.push(path as Href);
  async function submit() {
    if (busy.current) return;
    setError('');
    setMessage('');
    const credentials = mode === 'login' || mode === 'register';
    const validation = credentials
      ? validateCredentials(
          email,
          password,
          mode === 'register' ? confirmation : undefined,
        )
      : mode === 'reset-password'
        ? validateCredentials('valid@example.com', password, confirmation)
        : null;
    if (validation) {
      setError(validation);
      return;
    }
    if (mode === 'register' && (!name.trim() || name.trim().length > 100)) {
      setError('Informe seu nome (até 100 caracteres).');
      return;
    }
    if (
      (mode === 'forgot-password' || mode === 'verify-email') &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
    ) {
      setError('Informe um e-mail válido.');
      return;
    }
    if (
      mode === 'two-factor' &&
      !(backup ? code.trim().length >= 6 : /^\d{6}$/.test(code))
    ) {
      setError('Confira o código informado.');
      return;
    }
    if (mode === 'reset-password' && !params.token) {
      setError('Link inválido. Solicite um novo e-mail de recuperação.');
      return;
    }
    busy.current = true;
    setPending(true);
    try {
      if (mode === 'login') {
        const result = await runAuthAction(
          () => authClient.signIn.email({ email: email.trim(), password }),
          {
            scope: 'public',
            replaceIdentity: true,
            sessionEffect: (result) =>
              result.error
                ? 'none'
                : result.data &&
                    'twoFactorRedirect' in result.data &&
                    result.data.twoFactorRedirect
                  ? 'challenge'
                  : 'refresh',
          },
        );
        setPassword('');
        if (result.error) {
          if (result.error.code === 'EMAIL_NOT_VERIFIED') {
            router.push({
              pathname: '/auth/verify-email',
              params: { email: email.trim() },
            });
            return;
          }
          throw result.error;
        }
        if (
          result.data &&
          'twoFactorRedirect' in result.data &&
          result.data.twoFactorRedirect
        ) {
          go('/auth/two-factor');
          return;
        }
        router.replace('/permissions');
        return;
      }
      if (mode === 'register') {
        const result = await runAuthAction(
          () =>
            authClient.signUp.email({
              name: name.trim(),
              email: email.trim(),
              password,
              callbackURL: VERIFY,
            }),
          { scope: 'public' },
        );
        setPassword('');
        setConfirmation('');
        if (result.error) throw result.error;
        router.replace({
          pathname: '/auth/verify-email',
          params: { email: email.trim() },
        });
        return;
      }
      if (mode === 'verify-email') {
        const result = await runAuthAction(
          () =>
            authClient.sendVerificationEmail({
              email: email.trim(),
              callbackURL: VERIFY,
            }),
          { scope: 'public' },
        );
        if (result.error) throw result.error;
        setMessage(
          'Se houver uma conta elegível, enviaremos um link de verificação.',
        );
      }
      if (mode === 'forgot-password') {
        const result = await runAuthAction(
          () =>
            authClient.requestPasswordReset({
              email: email.trim(),
              redirectTo: RESET,
            }),
          { scope: 'public' },
        );
        if (result.error) throw result.error;
        setMessage(
          'Se houver uma conta com esse e-mail, enviaremos o link de recuperação.',
        );
      }
      if (mode === 'reset-password') {
        const result = await runAuthAction(
          () =>
            authClient.resetPassword({
              newPassword: password,
              token: params.token,
            }),
          {
            scope: 'public',
            sessionEffect: (result) => (result.error ? 'none' : 'refresh'),
          },
        );
        setPassword('');
        setConfirmation('');
        if (result.error) throw result.error;
        setMessage('Senha redefinida. Entre novamente com a nova senha.');
      }
      if (mode === 'two-factor') {
        const result = await runAuthAction(
          () =>
            backup
              ? authClient.twoFactor.verifyBackupCode({ code: code.trim() })
              : authClient.twoFactor.verifyTotp({ code }),
          {
            scope: 'public',
            replaceIdentity: true,
            sessionEffect: (result) => (result.error ? 'none' : 'refresh'),
          },
        );
        setCode('');
        if (result.error) throw result.error;
        router.replace('/permissions');
        return;
      }
      if (mode === 'email-confirmed') {
        await refresh();
        go('/auth/login');
      }
    } catch {
      setError(
        'Não foi possível concluir. Confira os dados e a conexão e tente novamente.',
      );
    } finally {
      busy.current = false;
      setPending(false);
    }
  }
  const showEmail = [
    'login',
    'register',
    'forgot-password',
    'verify-email',
  ].includes(mode);
  return (
    <AuthLayout
      title={titles[mode]}
      subtitle={
        mode === 'verify-email'
          ? 'Abra o link enviado ao seu e-mail. Depois volte e entre na sua conta.'
          : mode === 'email-confirmed'
            ? 'Seu e-mail foi confirmado. Você já pode entrar.'
            : undefined
      }
    >
      {mode === 'register' ? (
        <TextField
          label="Nome"
          autoComplete="name"
          autoCapitalize="words"
          value={name}
          onChangeText={setName}
          editable={!pending}
        />
      ) : null}
      {showEmail ? (
        <TextField
          label="E-mail"
          autoComplete="email"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
          editable={!pending}
        />
      ) : null}
      {['login', 'register', 'reset-password'].includes(mode) ? (
        <TextField
          label={mode === 'reset-password' ? 'Nova senha' : 'Senha'}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          editable={!pending}
        />
      ) : null}
      {mode === 'register' || mode === 'reset-password' ? (
        <>
          <AppText tone="secondary">Use 12 a 128 caracteres.</AppText>
          <TextField
            label="Confirme a senha"
            autoComplete="new-password"
            secureTextEntry
            value={confirmation}
            onChangeText={setConfirmation}
            editable={!pending}
          />
        </>
      ) : null}
      {mode === 'two-factor' ? (
        <>
          <TextField
            label={backup ? 'Código de recuperação' : 'Código do autenticador'}
            value={code}
            onChangeText={setCode}
            keyboardType={backup ? 'default' : 'number-pad'}
            autoComplete="one-time-code"
            editable={!pending}
          />
          <Button
            label={backup ? 'Usar autenticador' : 'Usar código de recuperação'}
            variant="ghost"
            onPress={() => {
              setBackup(!backup);
              setCode('');
            }}
            disabled={pending}
          />
        </>
      ) : null}
      {error ? (
        <AppText accessibilityRole="alert" tone="error">
          {error}
        </AppText>
      ) : null}
      {message ? (
        <AppText accessibilityLiveRegion="polite">{message}</AppText>
      ) : null}
      <Button
        label={
          mode === 'login'
            ? 'Entrar'
            : mode === 'register'
              ? 'Criar conta'
              : mode === 'verify-email'
                ? 'Reenviar verificação'
                : mode === 'forgot-password'
                  ? 'Enviar link'
                  : mode === 'reset-password'
                    ? 'Redefinir senha'
                    : mode === 'two-factor'
                      ? 'Verificar'
                      : 'Ir para login'
        }
        onPress={() => void submit()}
        loading={pending}
      />
      {mode === 'login' ? (
        <>
          <Button
            label="Esqueci minha senha"
            variant="ghost"
            disabled={pending}
            onPress={() => go('/auth/forgot-password')}
          />
          <Button
            label="Criar conta"
            variant="ghost"
            disabled={pending}
            onPress={() => go('/auth/register')}
          />
        </>
      ) : (
        <Button
          label="Voltar ao login"
          variant="ghost"
          disabled={pending}
          onPress={() => router.replace('/auth/login')}
        />
      )}
    </AuthLayout>
  );
}
