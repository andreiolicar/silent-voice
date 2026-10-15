import { lazy, Suspense } from 'react'
import { BrowserRouter, useLocation } from 'react-router-dom'
import { LazyMotion, domAnimation } from 'motion/react'
import { LandingPage } from './LandingPage'

const AdminApp = lazy(() =>
  import('./features/admin/AdminApp').then((module) => ({
    default: module.AdminApp,
  }))
)

function Page() {
  const { pathname } = useLocation()
  return /^\/admin(?:\/|$)/.test(pathname) ? <AdminApp /> : <LandingPage />
}

export function App() {
  return (
    <LazyMotion features={domAnimation} strict>
      <BrowserRouter>
        <Suspense fallback={<p role="status">Carregando…</p>}>
          <Page />
        </Suspense>
      </BrowserRouter>
    </LazyMotion>
  )
}
