import { useEffect } from 'react'
import { Typography } from '@silent-voice/web-ui/Typography'
import { ExplodedDeviceMedia } from '../components/device-integrated/ExplodedDeviceMedia'
import geometry from '../components/device-integrated/geometry.json'
import { notifyHeroReady, useIntroState } from '../intro/IntroProvider'
import './product-hero.css'

/** First product-led opening; the original device sequence owns its interaction. */
export function ProductHero() {
  const intro = useIntroState()

  useEffect(() => {
    let mounted = true
    // Release the intro once the actual device layers are ready, including failures.
    // The intro's existing deadline remains the fallback for a slow connection.
    Promise.all(geometry.layers.map(({ url }) => {
      const image = new Image()
      image.src = url
      return image.decode().catch(() => undefined)
    })).then(() => { if (mounted) notifyHeroReady() })
    return () => { mounted = false }
  }, [])

  return (
    <section className="v2-product-hero" id="inicio" aria-labelledby="product-heading"
      data-ready={intro.ready} data-immediate={intro.immediate}>
      <div className="v2-product-copy">
        <Typography as="h1" variant="h1" id="product-heading" data-reveal="0">
          O que você quer dizer merece ser ouvido.
        </Typography>
        <Typography as="p" variant="body" className="v2-product-description" data-reveal="1">
          Uma neckband que conecta sinais, contexto e inteligência para abrir novas possibilidades de comunicação.
        </Typography>
        <a className="v2-button v2-button--gradient" href="#lista" data-reveal="2">
          Faça parte dessa nova voz
        </a>
      </div>

      <div className="v2-product-showcase">
        <div className="v2-product-glow" aria-hidden="true" />
        <div className="v2-product-orbits" aria-hidden="true"><i /><i /><i /></div>
        <ExplodedDeviceMedia entranceReady={intro.ready} skipEntrance={intro.immediate} />
      </div>
    </section>
  )
}
