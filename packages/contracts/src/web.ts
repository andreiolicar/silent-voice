/** Public entrypoints remain stable when the two web builds are published together. */
export function documentForPath(pathname: string): 'admin/index.html' | 'index.html' {
  const path = new URL(pathname, 'http://localhost').pathname
  return /^\/(?:admin|conta)(?:\/|$)/.test(path) ? 'admin/index.html' : 'index.html'
}
