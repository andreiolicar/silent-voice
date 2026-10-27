import { Resend } from 'resend'
export type AuthEmail = { to: string; url: string; kind: 'verify' | 'reset' | 'invite' }
export type AuthMailer = (message: AuthEmail) => Promise<void>
function escape(value: string) { return value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!)) }
export function createAuthMailer(apiKey?: string, from = 'Silent Voice <conta@silentvoice.com.br>'): AuthMailer {
  const resend = apiKey ? new Resend(apiKey) : null
  return async ({ to, url, kind }) => {
    if (!resend) throw new Error('Authentication email service is not configured')
    const title = kind === 'verify' ? 'Confirme seu e-mail' : kind === 'invite' ? 'Configure seu acesso ao Silent Voice' : 'Redefina sua senha'
    const description = kind === 'verify' ? 'Confirme seu endereço para acessar o Silent Voice.' : 'Use o link abaixo para definir sua nova senha. Se você não solicitou esta alteração, ignore este e-mail.'
    const { error } = await resend.emails.send({
      from, to, replyTo: 'contato@silentvoice.com.br', subject: `${title} — Silent Voice`,
      text: `${title}\n\n${description}\n\n${url}\n\nSilent Voice`,
      html: `<html lang="pt-BR"><body style="margin:0;background:#e4f5f3;font-family:Arial,sans-serif;color:#051B34"><main style="max-width:480px;margin:32px auto;padding:32px;background:white;border-radius:24px"><p style="color:#1AA99B;font-weight:600">Silent Voice</p><h1 style="font-size:24px">${title}</h1><p style="line-height:1.6">${description}</p><p style="margin:28px 0"><a href="${escape(url)}" style="display:inline-block;background:#1AA99B;color:white;padding:14px 24px;border-radius:999px;text-decoration:none">${title}</a></p><p style="font-size:12px;color:#64748b">Este link é temporário. Não compartilhe esta mensagem.</p></main></body></html>`,
    })
    if (error) throw new Error('Authentication email delivery failed')
  }
}
