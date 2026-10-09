import * as m from 'motion/react-m'
import { useId, useState } from 'react'
import { useTransform } from 'motion/react'
import type { MotionValue } from 'motion/react'
import { useDeviceSequence } from './useDeviceSequence'
import { ShowcaseBackdrop } from '../ShowcaseBackdrop'
import { sampleDeviceGuide, type sampleSequence } from './sequence'
import geometry from './geometry.json'
import './exploded-device-media.css'

type Layer = typeof geometry.layers[number]
type Pose = ReturnType<typeof sampleSequence>
const svgOrigin = { originX: 0, originY: 0, transformBox: 'view-box' } as const
const housing = geometry.layers.find(layer => layer.kind === 'housing')!
const movingLayers = geometry.layers.filter(layer => layer.kind !== 'housing')
const componentNames: Record<string, string> = {
  'raspberry-pi': 'Raspberry Pi Zero 2 W',
  esp32: 'ESP32-S3 N16R8',
  myoware: 'MyoWare 2',
}

function DeviceComponentLabel({ layer }: { layer: Layer }) {
  const [left, top, right] = layer.bounds
  const x = ((left + right) / 2 + layer.offset[0]) * geometry.scale + geometry.openTranslate[0]
  const y = (top + layer.offset[1]) * geometry.scale + geometry.openTranslate[1]

  return (
    <span className="integrated-device-media__label" aria-hidden="true"
      data-device-label={layer.id} style={{ left: `${x / 648 * 100}%`, top: `${y / 440 * 100}%` }}>
      {componentNames[layer.id]}
    </span>
  )
}

function DeviceGuide({ guide, pose }: {
  guide: typeof geometry.guides[number]
  pose: MotionValue<Pose>
}) {
  const cover = movingLayers.find(layer => layer.id === guide.coverId)!
  const line = useTransform(pose, value => sampleDeviceGuide(guide, cover.offset, value.covers))
  const x2 = useTransform(line, value => value.x2)
  const y2 = useTransform(line, value => value.y2)
  const opacity = useTransform(line, value => value.opacity)

  return (
    <m.line data-device-guide={guide.id}
      x1={guide.housingAnchor[0]} y1={guide.housingAnchor[1]} x2={x2} y2={y2}
      stroke="var(--color-device-guide)" strokeWidth="1" strokeDasharray="3 4"
      strokeLinecap="round" vectorEffect="non-scaling-stroke"
      pointerEvents="none" style={{ opacity }} />
  )
}

function DeviceLayer({ layer, pose, fail, onHover }: {
  layer: Layer
  pose: MotionValue<Pose>
  fail: () => void
  onHover?: (id: string | null) => void
}) {
  const transform = useTransform(pose, value => {
    const progress = layer.kind === 'cover' ? value.covers : layer.kind === 'component' ? value.components : 0
    return `translate(${layer.offset[0] * progress}px, ${layer.offset[1] * progress}px)`
  })
  const shadowOpacity = useTransform(pose, value => layer.kind === 'cover' ? value.covers * .06 : 0)
  const [left, , right, bottom] = layer.bounds
  return (
    <m.g data-device-layer={layer.id} style={{ ...svgOrigin, transform }}>
      {layer.kind === 'cover' && (
        <m.ellipse className="integrated-device-media__shadow"
          cx={(left + right) / 2} cy={bottom - 5} rx={(right - left) * .38} ry="8"
          fill="var(--color-text)" style={{ opacity: shadowOpacity }} />
      )}
      <image href={layer.url} width="648" height="440" onError={fail} />
      <path className="integrated-device-media__hit" data-device-hit={layer.id}
        d={layer.hitPath} fill="transparent" fillRule="evenodd"
        onPointerEnter={event => { if (event.pointerType === 'mouse') onHover?.(layer.id) }}
        onPointerLeave={() => onHover?.(null)} />
    </m.g>
  )
}

export function ExplodedDeviceMedia({ entranceReady, skipEntrance = false }: {
  entranceReady: boolean
  skipEntrance?: boolean
}) {
  const { stage, status, decoded, pose, riseTransform, centerTransform, toggleExpanded, fail } =
    useDeviceSequence(entranceReady, skipEntrance)
  const [hoveredComponent, setHoveredComponent] = useState<string | null>(null)
  const descriptionId = useId()
  const activeComponent = status.phase === 'open'
    ? movingLayers.find(layer => layer.kind === 'component' && layer.id === hoveredComponent)
    : undefined

  function toggleDevice() {
    setHoveredComponent(null)
    toggleExpanded()
  }

  return (
    <figure className="integrated-device-media" aria-label="Dispositivo Silent Voice com carcaça integrada e componentes internos.">
      <div ref={stage} className="integrated-device-media__stage" data-phase={status.phase}
        onPointerLeave={() => setHoveredComponent(null)}>
        <ShowcaseBackdrop />
        <div className="integrated-device-media__canvas">
          {status.error ? (
            <img className="integrated-device-media__fallback" src="/assets/device-interactive/closed.webp"
              width="1296" height="880" alt="Dispositivo Silent Voice fechado. Visualização estática." />
          ) : (
            <button type="button" className="integrated-device-media__interaction" onClick={toggleDevice}
              onKeyDown={event => { if (event.key === 'Escape') setHoveredComponent(null) }}
              aria-describedby={status.phase === 'open' ? descriptionId : undefined}
              aria-label={status.expanded ? 'Fechar dispositivo Silent Voice' : 'Abrir dispositivo Silent Voice'}
              aria-expanded={status.expanded} aria-disabled={!status.canInteract}>
              <svg viewBox="0 0 648 440" aria-hidden="true" focusable="false">
                {decoded && (
                  <m.g data-device-rise style={{ ...svgOrigin, transform: riseTransform }}>
                    <m.g data-device-center style={{ ...svgOrigin, transform: centerTransform }}>
                      <DeviceLayer layer={housing} pose={pose} fail={fail} />
                      <g data-device-guides pointerEvents="none">
                        {geometry.guides.map(guide => <DeviceGuide key={guide.id} guide={guide} pose={pose} />)}
                      </g>
                      {movingLayers.map(layer => <DeviceLayer key={layer.id} layer={layer} pose={pose} fail={fail}
                        onHover={layer.kind === 'component' ? setHoveredComponent : undefined} />)}
                    </m.g>
                  </m.g>
                )}
              </svg>
            </button>
          )}
          {activeComponent && <DeviceComponentLabel layer={activeComponent} />}
        </div>
        {status.phase === 'open' && (
          <span id={descriptionId} className="sr-only">
            Componentes internos: {Object.values(componentNames).join(', ')}.
          </span>
        )}
      </div>
    </figure>
  )
}
