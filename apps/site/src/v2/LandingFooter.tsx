import { Typography } from '@silent-voice/web-ui/Typography'

export function LandingFooter() {
  return (
    <footer className="v2-footer">
      <Typography as="span" variant="caption">
        © {new Date().getFullYear()} Silent Voice. Todos os direitos reservados.
      </Typography>
    </footer>
  )
}
