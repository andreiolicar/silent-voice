import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import * as m from 'motion/react-m'
import { useEntrance } from '../entrance'
import { heroBackdropShapePath, heroBackdropMarkPath, heroBackdropViewBox } from './hero-backdrop-paths'
import './hero-artwork.css'
import { notifyHeroReady, useIntroState } from '../intro/IntroProvider'

// Figma geometry expressed within the 695 × 771 artwork, so its layers scale together.
function box(x: number, y: number, width: number, height: number): CSSProperties {
  return { left: `${x / 695 * 100}%`, top: `${y / 771 * 100}%`, width: `${width / 695 * 100}%`, height: `${height / 771 * 100}%` }
}

// Nodes and their connectors share the artwork's coordinate system.
const conversationBox = [479, 280, 172, 102] as const
const hubBox = [542, 430, 46, 46] as const
const communicationNodes = [
  { frame: [600, 521, 30, 30], icon: 'lucide-message-circle-check.svg', nodeId: '30:13', entrance: 'rightNode' },
  { frame: [550, 536, 30, 30], icon: 'lucide-speech.svg', nodeId: '30:10', entrance: 'middleNode' },
  { frame: [500, 521, 30, 30], icon: 'lucide-house1.svg', nodeId: '30:14', entrance: 'leftNode' },
] as const

const axisX = hubBox[0] + hubBox[2] / 2
const hubBottom = hubBox[1] + hubBox[3]
const branchY = hubBottom + 20
const bendY = branchY + 7
const [rightNode, middleNode, leftNode] = communicationNodes
const leftX = leftNode.frame[0] + leftNode.frame[2] / 2
const rightX = rightNode.frame[0] + rightNode.frame[2] / 2
const upperConnector = `M ${conversationBox[0] + conversationBox[2] / 2} ${conversationBox[1] + conversationBox[3]} V ${hubBox[1]}`
const lowerConnectors = [
  `M ${axisX} ${hubBottom} V ${middleNode.frame[1]}`,
  `M ${axisX} ${branchY} Q ${axisX} ${bendY} ${axisX - 7} ${bendY} H ${leftX + 7} Q ${leftX} ${bendY} ${leftX} ${bendY + 7} V ${leftNode.frame[1]}`,
  `M ${axisX} ${branchY} Q ${axisX} ${bendY} ${axisX + 7} ${bendY} H ${rightX - 7} Q ${rightX} ${bendY} ${rightX} ${bendY + 7} V ${rightNode.frame[1]}`,
].join(' ')

export function HeroArtwork() {
  const artwork = useRef<HTMLDivElement>(null)
  const [ready, setReady] = useState(false)
  const intro = useIntroState()
  // The intro's resource deadline also releases artwork whose decode is slow.
  const enter = useEntrance(ready || intro.ready)

  useEffect(() => {
    let mounted = true
    const images = Array.from(artwork.current!.querySelectorAll('img'))

    Promise.all(images.map(image => image.decode().catch(() => undefined))).then(() => {
      if (mounted) {
        setReady(true)
        notifyHeroReady()
      }
    })

    return () => { mounted = false }
  }, [])

  return (
    <div ref={artwork} className="hero-artwork relative shrink-0 select-none" role="img" aria-label="Mulher segurando um celular com o aplicativo Silent Voice, acompanhada de gráficos e símbolos de comunicação assistiva." data-node-id="23:64">
      <m.svg className="scene-layer" style={box(45, 26, 650, 607.36)} viewBox={heroBackdropViewBox} preserveAspectRatio="none" aria-hidden="true" focusable="false" data-node-id="23:62" {...enter('backdrop')}>
        <path d={heroBackdropShapePath} fill="var(--color-brand)" fillRule="evenodd" />
        <path d={heroBackdropMarkPath} fill="var(--color-surface)" fillRule="evenodd" />
      </m.svg>
      <m.img className="scene-layer" style={box(0, 33.570175, 240, 171.929825)} src="/assets/stability-card2.svg" alt="" data-node-id="45:19" {...enter('card')} />
      <m.div className="scene-layer overflow-hidden" style={box(89, 0, 562, 771)} data-node-id="23:63" {...enter('portrait')}>
        <img className="hero-artwork__woman" src="/assets/woman-hero.png" alt="" fetchPriority="high" />
      </m.div>

      <m.div className="scene-layer artwork-menu" style={box(67, 508.5, 44, 176)} data-node-id="23:116" {...enter('artworkMenu')}>
        <div className="artwork-menu__active"><img src="/assets/lucide-house.svg" alt="" /></div>
        <img className="artwork-menu__icon" src="/assets/lucide-hard-drive.svg" alt="" />
        <img className="artwork-menu__icon" src="/assets/lucide-audio-lines.svg" alt="" />
        <img className="artwork-menu__icon" src="/assets/lucide-settings.svg" alt="" />
      </m.div>

      <svg className="scene-layer artwork-connectors" viewBox="0 0 695 771" fill="none" stroke="var(--color-surface)" strokeWidth="0.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
        <m.path d={upperConnector} {...enter('upperLine')} />
        <m.path d={lowerConnectors} {...enter('branches')} />
      </svg>

      {communicationNodes.map(({ frame, icon, nodeId, entrance }) => (
        <m.div key={nodeId} className="scene-layer glass-circle" style={box(frame[0], frame[1], frame[2], frame[3])} data-node-id={nodeId} {...enter(entrance)}><img src={`/assets/${icon}`} alt="" /></m.div>
      ))}

      <m.div className="scene-layer glass-square" style={box(...hubBox)} data-node-id="29:154" {...enter('hub')}><img src="/assets/icon-white1.png" alt="" /></m.div>
      <m.div className="scene-layer artwork-conversation overflow-hidden" style={box(...conversationBox)} data-node-id="29:158" {...enter('conversation')}>
        <img src="/assets/main.png" alt="" />
      </m.div>
    </div>
  )
}
