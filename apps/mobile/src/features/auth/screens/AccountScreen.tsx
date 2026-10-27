import { useEffect, useRef, useState } from 'react';
import { Linking, View } from 'react-native';
import { useRouter } from 'expo-router';
import * as Clipboard from 'expo-clipboard';
import QRCode from 'react-native-qrcode-svg';
import { AppText, Button, Card } from '@/components/ui';
import { TextField } from '@/components/ui/TextField';
import { validateCredentials } from '@/domain/auth/policy';
import { AuthLayout } from '../components/AuthLayout';
import { authClient } from '../client';
import { useAuth } from '../AuthProvider';

type RemoteSession = {
  id: string;
  token: string;
  expiresAt: Date;
  userAgent?: string | null;
};
export default function AccountScreen({
  security = false,
}: {
  security?: boolean;
}) {
  const router = useRouter();
  const { session, offline, logout, runAuthAction } = useAuth();
  const [password, setPassword] = useState('');
  const [next, setNext] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [code, setCode] = useState('');
  const [uri, setUri] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const [codesSaved, setCodesSaved] = useState(false);
  const [sessions, setSessions] = useState<RemoteSession[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const busy = useRef(false);
  async function run(action: () => Promise<void>) {
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    setError('');
    setMessage('');
    try {
      await action();
    } catch {
      setError(
        'Não foi possível concluir. Confira sua senha, o código e a conexão.',
      );
    } finally {
      busy.current = false;
      setPending(false);
      setPassword('');
      setNext('');
      setConfirmation('');
      setCode('');
    }
  }
  async function loadSessions() {
    const result = await runAuthAction(() => authClient.listSessions(), {
      scope: 'account',
      invalidateOnUnauthorized: true,
    });
    if (result.error) throw result.error;
    setSessions(result.data || []);
  }
  useEffect(() => {
    if (!security || offline) return;
    let active = true;
    void runAuthAction(() => authClient.listSessions(), {
      scope: 'account',
      invalidateOnUnauthorized: true,
    })
      .then((result) => {
        if (!active) return;
        if (result.error) {
          setError('Não foi possível carregar as sessões.');
        } else setSessions(result.data || []);
      })
      .catch(() => {
        if (active) setError('Não foi possível carregar as sessões.');
      });
    return () => {
      active = false;
    };
  }, [security, offline, runAuthAction]);
  const manualKey = uri ? new URL(uri).searchParams.get('secret') || '' : '';
  return (
    <AuthLayout
      title={security ? 'Segurança da conta' : 'Meu perfil'}
      subtitle={
        offline
          ? 'Modo offline: a identidade local permite usar os recursos locais. Alterações de conta precisam de conexão.'
          : undefined
      }
    >
      {!security ? (
        <>
          <Card>
            <AppText variant="cardTitle">{session?.user.name}</AppText>
            <AppText>{session?.user.email}</AppText>
            <AppText>E-mail verificado</AppText>
          </Card>
          <Button
            label="Segurança e sessões"
            onPress={() => router.push('/account/security')}
          />
        </>
      ) : (
        <>
          <AppText variant="cardTitle">Alterar senha</AppText>
          <TextField
            label="Senha atual"
            secureTextEntry
            autoComplete="current-password"
            value={password}
            onChangeText={setPassword}
            editable={!pending && !offline}
          />
          <TextField
            label="Nova senha (12 a 128 caracteres)"
            secureTextEntry
            autoComplete="new-password"
            value={next}
            onChangeText={setNext}
            editable={!pending && !offline}
          />
          <TextField
            label="Confirme a nova senha"
            secureTextEntry
            autoComplete="new-password"
            value={confirmation}
            onChangeText={setConfirmation}
            editable={!pending && !offline}
          />
          <Button
            label="Alterar senha"
            loading={pending}
            disabled={offline || !password || Boolean(uri)}
            onPress={() =>
              void run(async () => {
                const validation = validateCredentials(
                  'valid@example.com',
                  next,
                  confirmation,
                );
                if (validation) {
                  setError(validation);
                  return;
                }
                const result = await runAuthAction(
                  () =>
                    authClient.changePassword({
                      currentPassword: password,
                      newPassword: next,
                      revokeOtherSessions: true,
                    }),
                  {
                    scope: 'account',
                    invalidateOnUnauthorized: true,
                    sessionEffect: (result) =>
                      result.error ? 'none' : 'refresh',
                  },
                );
                if (result.error) throw result.error;
                setMessage(
                  'Senha atualizada. As outras sessões foram encerradas.',
                );
                await loadSessions();
              })
            }
          />
          <AppText variant="cardTitle">Autenticador em duas etapas</AppText>
          <AppText>
            Informe sua senha atual acima para configurar o autenticador. Após
            confirmar, guarde os códigos de recuperação e entre novamente.
          </AppText>
          {!uri && !session?.user.twoFactorEnabled ? (
            <Button
              label="Configurar autenticador"
              disabled={offline || !password}
              loading={pending}
              onPress={() =>
                void run(async () => {
                  const result = await runAuthAction(
                    () =>
                      authClient.twoFactor.enable({
                        password,
                      }),
                    { scope: 'account', invalidateOnUnauthorized: true },
                  );
                  if (result.error) throw result.error;
                  if (result.data && 'totpURI' in result.data) {
                    setUri(result.data.totpURI);
                    setCodes(result.data.backupCodes);
                    setCodesSaved(false);
                  }
                })
              }
            />
          ) : uri ? (
            <Card>
              <View style={{ gap: 16 }}>
                <AppText>
                  Leia este QR com seu autenticador ou copie a chave manual.
                  Estes dados são secretos.
                </AppText>
                <View
                  accessible
                  accessibilityLabel="QR do autenticador; a chave manual está disponível abaixo"
                  style={{ alignItems: 'center' }}
                >
                  <QRCode value={uri} size={200} />
                </View>
                <AppText selectable>{manualKey}</AppText>
                <Button
                  label="Copiar chave manual"
                  variant="ghost"
                  onPress={() => void Clipboard.setStringAsync(manualKey)}
                />
                <Button
                  label="Abrir autenticador"
                  variant="ghost"
                  onPress={() =>
                    void Linking.openURL(uri).catch(() =>
                      setError(
                        'Nenhum autenticador disponível. Use a chave manual.',
                      ),
                    )
                  }
                />
                {!codesSaved ? (
                  <AppText>
                    Guarde os códigos abaixo antes de confirmar.
                  </AppText>
                ) : (
                  <>
                    <TextField
                      label="Código de 6 dígitos"
                      value={code}
                      onChangeText={setCode}
                      keyboardType="number-pad"
                      autoComplete="one-time-code"
                    />
                    <Button
                      label="Confirmar autenticador"
                      loading={pending}
                      onPress={() =>
                        void run(async () => {
                          if (!/^\d{6}$/.test(code)) {
                            setError('Informe os 6 dígitos.');
                            return;
                          }
                          const result = await runAuthAction(
                            () =>
                              authClient.twoFactor.verifyTotp({
                                code,
                              }),
                            {
                              scope: 'account',
                              invalidateOnUnauthorized: true,
                            },
                          );
                          if (result.error) throw result.error;
                          setUri('');
                          setCodes([]);
                          await logout();
                          router.replace('/auth/login?completed=mfa');
                        })
                      }
                    />
                  </>
                )}
              </View>
            </Card>
          ) : (
            <>
              <AppText>Autenticador ativado.</AppText>
              <Button
                label="Desativar autenticador"
                variant="danger"
                disabled={offline || !password}
                loading={pending}
                onPress={() =>
                  void run(async () => {
                    const result = await runAuthAction(
                      () =>
                        authClient.twoFactor.disable({
                          password,
                        }),
                      { scope: 'account', invalidateOnUnauthorized: true },
                    );
                    if (result.error) throw result.error;
                    await logout();
                    router.replace('/auth/login?completed=mfa');
                  })
                }
              />
            </>
          )}
          {uri && codes.length ? (
            <Card>
              <AppText variant="cardTitle">
                Guarde seus códigos de recuperação
              </AppText>
              <AppText>
                Cada código pode ser usado uma vez. Eles não serão salvos no
                aplicativo.
              </AppText>
              {codes.map((item) => (
                <AppText selectable key={item}>
                  {item}
                </AppText>
              ))}
              <Button
                label="Copiar códigos"
                variant="ghost"
                onPress={() => void Clipboard.setStringAsync(codes.join('\n'))}
              />
              <Button
                label={
                  codesSaved
                    ? 'Códigos guardados'
                    : 'Guardei os códigos de recuperação'
                }
                disabled={codesSaved}
                onPress={() => setCodesSaved(true)}
              />
            </Card>
          ) : null}
          <AppText variant="cardTitle">Sessões conectadas</AppText>
          <Button
            label="Atualizar sessões"
            variant="ghost"
            disabled={offline}
            loading={pending}
            onPress={() => void run(loadSessions)}
          />
          {sessions.map((item) => (
            <Card key={item.id}>
              <AppText>{item.userAgent || 'Dispositivo'}</AppText>
              <AppText>
                Expira em {new Date(item.expiresAt).toLocaleString('pt-BR')}
              </AppText>
              <Button
                label="Encerrar esta sessão"
                variant="danger"
                disabled={offline}
                loading={pending}
                onPress={() =>
                  void run(async () => {
                    const result = await runAuthAction(
                      () =>
                        authClient.revokeSession({
                          token: item.token,
                        }),
                      {
                        scope: 'account',
                        invalidateOnUnauthorized: true,
                        sessionEffect: (result) =>
                          result.error ? 'none' : 'refresh',
                      },
                    );
                    if (result.error) throw result.error;
                    await loadSessions();
                  })
                }
              />
            </Card>
          ))}
        </>
      )}
      {error ? (
        <AppText accessibilityRole="alert" tone="error">
          {error}
        </AppText>
      ) : null}
      {message ? (
        <AppText accessibilityLiveRegion="polite">{message}</AppText>
      ) : null}
      <Button
        label="Sair da conta"
        variant="danger"
        onPress={() => {
          void logout();
          router.replace('/auth/login');
        }}
        disabled={pending}
      />
      <Button
        label="Voltar"
        variant="ghost"
        onPress={() => router.replace('/(main)/settings')}
      />
    </AuthLayout>
  );
}
