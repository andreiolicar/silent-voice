import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ChatRequest, ChatStreamEvent } from '../../../shared/chat'
import type { ChatTransport } from './chat-client'
import { ChatWidget } from './ChatWidget'
function controlledTransport() {
  const calls: {
    request: ChatRequest
    signal: AbortSignal
    emit: (event: ChatStreamEvent) => void
    resolve: () => void
    reject: (error: Error) => void
  }[] = []
  const transport: ChatTransport = (request, signal, emit) =>
    new Promise<void>((resolve, reject) => {
      calls.push({ request, signal, emit, resolve, reject })
    })
  return { transport, calls }
}
async function open() {
  await userEvent.click(
    screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
  )
  return await screen.findByRole(
    'textbox',
    { name: 'Sua mensagem' },
    { timeout: 5000 }
  )
}
afterEach(() => vi.unstubAllGlobals())
describe('public chatbot widget', () => {
  it('clears the welcome screen when a conversation starts and restores it only for a new conversation', async () => {
    const { transport } = controlledTransport()
    render(<ChatWidget transport={transport} />)
    const composer = await open()
    const welcome = screen.getByRole('heading', { level: 3 })
    expect(welcome).toBeVisible()
    await userEvent.type(composer, 'Como funciona?{Enter}')
    expect(welcome).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Solicitar demonstração' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Nova conversa' }))
    expect(screen.getByRole('heading', { level: 3 })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Solicitar demonstração' })).toBeEnabled()
  })

  it('waits for the intro, opens on demand, focuses composer and restores focus with Escape', async () => {
    const { rerender } = render(<ChatWidget ready={false} />)
    expect(screen.queryByRole('button')).toBeNull()
    rerender(<ChatWidget ready />)
    expect(screen.queryByRole('dialog')).toBeNull()
    const composer = await open()
    expect(
      screen.getByRole('dialog', { name: 'Assistente Silent Voice' })
    ).toHaveAttribute('aria-modal', 'false')
    expect(composer).toHaveFocus()
    fireEvent.keyDown(composer, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(
      screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
    ).toHaveFocus()
    expect(
      screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
    ).toHaveAttribute('aria-expanded', 'false')
  })
  it('keeps messages and generation alive while minimized; resets and ignores late responses', async () => {
    const { transport, calls } = controlledTransport()
    render(<ChatWidget transport={transport} />)
    const composer = await open()
    await userEvent.type(composer, 'Como funciona?{Enter}')
    expect(await screen.findByText('Como funciona?')).toBeVisible()
    await userEvent.click(
      screen.getByRole('button', { name: 'Minimizar assistente' })
    )
    expect(calls[0].signal.aborted).toBe(false)
    expect(document.getElementById('silent-voice-chat-panel')).toHaveAttribute(
      'hidden'
    )
    expect(document.getElementById('silent-voice-chat-panel')).toHaveAttribute(
      'inert'
    )
    await act(async () => {
      calls[0].emit({
        type: 'delta',
        requestId: calls[0].request.requestId,
        text: 'root = Answer("O dispositivo", [Text("Veja a explicação.")])',
      })
      calls[0].emit({
        type: 'done',
        requestId: calls[0].request.requestId,
        finishReason: 'stop',
      })
      calls[0].resolve()
    })
    await open()
    expect(screen.getByText('Veja a explicação.')).toBeVisible()
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Sua mensagem' }),
      'Outra dúvida{Enter}'
    )
    await userEvent.click(screen.getByRole('button', { name: 'Nova conversa' }))
    expect(calls[1].signal.aborted).toBe(true)
    await act(async () => {
      calls[1].emit({
        type: 'delta',
        requestId: calls[1].request.requestId,
        text: 'root = Answer("Tarde", [Text("Callback obsoleto")])',
      })
      calls[1].resolve()
    })
    expect(screen.queryByText('Como funciona?')).toBeNull()
    expect(screen.queryByText('Callback obsoleto')).toBeNull()
  })
  it.each(['stop','error','length'] as const)('preserves visible partial blocks after %s and when starting another question',async ending=>{
    const {transport,calls}=controlledTransport()
    const {container}=render(<ChatWidget transport={transport}/>)
    await userEvent.type(await open(),'Como funciona?{Enter}')
    await act(async()=>calls[0].emit({type:'delta',requestId:calls[0].request.requestId,text:'root = Answer("Como funciona", [Text("O sensor detecta sinais musculares'}))
    expect(screen.getByText('O sensor detecta sinais musculares')).toBeVisible()
    if(ending==='stop'){
      await userEvent.click(screen.getByRole('button',{name:'Parar resposta'}))
    }else if(ending==='error'){
      await act(async()=>calls[0].reject(new Error('network loss')))
    }else{
      await act(async()=>{calls[0].emit({type:'done',requestId:calls[0].request.requestId,finishReason:'length'});calls[0].resolve()})
    }
    expect(screen.getByText('O sensor detecta sinais musculares')).toBeVisible()
    expect(screen.queryByText(/Não foi possível exibir esta resposta/)).toBeNull()
    expect(container.querySelector('[aria-busy="true"]')).toBeNull()
    expect(screen.queryByRole('button',{name:'Parar resposta'})).toBeNull()
    if(ending==='stop')expect(screen.getByText(/Resposta interrompida. Você pode/)).toBeVisible()
    else expect(screen.getByRole('alert')).toBeVisible()
    await userEvent.type(screen.getByRole('textbox',{name:'Sua mensagem'}),'Outra pergunta{Enter}')
    expect(screen.getByText('O sensor detecta sinais musculares')).toBeVisible()
  })
  it('supports Shift+Enter and IME without sending; sends plain Enter and keeps contact reachable on error', async () => {
    const { transport, calls } = controlledTransport()
    render(<ChatWidget transport={transport} />)
    const composer = await open()
    await userEvent.type(composer, 'Olá')
    fireEvent.keyDown(composer, { key: 'Enter', isComposing: true })
    expect(calls).toHaveLength(0)
    await userEvent.keyboard('{Shift>}{Enter}{/Shift}')
    expect(composer).toHaveValue('Olá\n')
    expect(calls).toHaveLength(0)
    await userEvent.keyboard('{Enter}')
    expect(calls).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Parar resposta' })).toBeVisible()
    await act(async () => calls[0].reject(new Error('unavailable')))
    expect(await screen.findByRole('alert')).toBeVisible()
    await userEvent.click(
      screen.getByRole('button', { name: 'Rever pergunta' })
    )
    expect(screen.getByRole('textbox', { name: 'Sua mensagem' })).toHaveValue(
      'Olá'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Falar com a equipe' })
    )
    expect(screen.getByLabelText('Nome')).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'contato@silentvoice.com.br' })
    ).toBeVisible()
  })
  it('only follows streamed output while the visitor is already near the bottom', async () => {
    const { transport, calls } = controlledTransport()
    render(<ChatWidget transport={transport} />)
    await userEvent.type(await open(), 'Como funciona?{Enter}')
    const viewport = document.querySelector('.sv-chat-scroll') as HTMLDivElement
    Object.defineProperties(viewport, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 200 },
    })
    viewport.scrollTop = 100
    fireEvent.scroll(viewport)
    await act(async () =>
      calls[0].emit({
        type: 'delta',
        requestId: calls[0].request.requestId,
        text: 'root = Answer("Produto", [Text("Primeira parte',
      })
    )
    expect(viewport.scrollTop).toBe(100)
    viewport.scrollTop = 800
    fireEvent.scroll(viewport)
    await act(async () =>
      calls[0].emit({
        type: 'delta',
        requestId: calls[0].request.requestId,
        text: ' da resposta.")])',
      })
    )
    expect(viewport.scrollTop).toBe(1000)
  })
  it('keeps a pending lead registration alive while minimized without sending its fields to the AI', async () => {
    let complete!: (response: Response) => void
    const fetcher = vi.fn(
      (_url: string, _init: RequestInit) =>
        new Promise<Response>((resolve) => {
          complete = resolve
        })
    )
    vi.stubGlobal('fetch', fetcher)
    const { transport, calls } = controlledTransport()
    render(<ChatWidget transport={transport} />)
    await open()
    await userEvent.click(
      screen.getByRole('button', { name: 'Falar com a equipe' })
    )
    await userEvent.type(screen.getByLabelText('Nome'), 'Maria Silva')
    await userEvent.type(screen.getByLabelText('E-mail'), 'maria@example.com')
    await userEvent.type(
      screen.getByLabelText('Objetivo do contato'),
      'Gostaria de conhecer o dispositivo.'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Registrar interesse' })
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Minimizar assistente' })
    )
    expect(fetcher.mock.calls[0][1].signal?.aborted).toBe(false)
    await act(async () =>
      complete(
        new Response(
          JSON.stringify({
            id: 'receipt-1',
            createdAt: '2026-10-15T12:00:00.000Z',
          }),
          { status: 201 }
        )
      )
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
    )
    expect(
      await screen.findByText('Seu interesse foi registrado.')
    ).toBeVisible()
    expect(calls).toHaveLength(0)
  })
  it('focuses the confirmed contact receipt after reopening and after returning from chat',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'receipt-1',createdAt:'2026-10-15T12:00:00.000Z'}),{status:201})))
    render(<ChatWidget/>)
    await open()
    await userEvent.click(screen.getByRole('button',{name:'Falar com a equipe'}))
    await userEvent.type(screen.getByLabelText('Nome'),'Maria Silva')
    await userEvent.type(screen.getByLabelText('E-mail'),'maria@example.com')
    await userEvent.type(screen.getByLabelText('Objetivo do contato'),'Quero conhecer o dispositivo.')
    await userEvent.click(screen.getByRole('button',{name:'Registrar interesse'}))
    const receipt=await screen.findByRole('heading',{name:'Seu interesse foi registrado.'})
    await userEvent.click(screen.getByRole('button',{name:'Minimizar assistente'}))
    await userEvent.click(screen.getByRole('button',{name:'Abrir assistente Silent Voice'}))
    expect(receipt).toHaveFocus()
    await userEvent.click(screen.getByRole('button',{name:'Voltar à conversa'}))
    await userEvent.click(screen.getByRole('button',{name:'Falar com a equipe'}))
    expect(receipt).toHaveFocus()
  })
  it('preserves the contact form across chat and minimize, and clears it on a new conversation', async () => {
    render(<ChatWidget />)
    await open()
    await userEvent.click(
      screen.getByRole('button', { name: 'Falar com a equipe' })
    )
    await userEvent.type(screen.getByLabelText('Nome'), 'Maria')
    await userEvent.click(
      screen.getByRole('button', { name: 'Voltar à conversa' })
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Falar com a equipe' })
    )
    expect(screen.getByLabelText('Nome')).toHaveValue('Maria')
    await userEvent.click(
      screen.getByRole('button', { name: 'Minimizar assistente' })
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Abrir assistente Silent Voice' })
    )
    await waitFor(() => expect(screen.getByLabelText('Nome')).toBeVisible())
    expect(screen.getByLabelText('Nome')).toHaveValue('Maria')
    await userEvent.click(screen.getByRole('button', { name: 'Nova conversa' }))
    await userEvent.click(
      screen.getByRole('button', { name: 'Falar com a equipe' })
    )
    expect(screen.getByLabelText('Nome')).toHaveValue('')
  })
})
