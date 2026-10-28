const dateFormat = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
})
export function formatAdminDate(value: string) {
  return dateFormat.format(new Date(value))
}
