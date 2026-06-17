// src/utils/exportExcel.ts
// Exportación sin dependencias externas.
// Genera un CSV con BOM UTF-8 — Excel lo abre directamente con encoding correcto.

export function exportToExcel(
  rows: Record<string, unknown>[],
  filename: string,
  _sheetName?: string,   // se acepta para mantener compatibilidad de llamada
): void {
  if (rows.length === 0) return

  const headers = Object.keys(rows[0])

  const escape = (value: unknown): string => {
    const str = value === null || value === undefined ? '' : String(value)
    // Envolver en comillas si contiene coma, comilla doble o salto de línea
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  const lines = [
    headers.map(escape).join(','),
    ...rows.map(row => headers.map(h => escape(row[h])).join(',')),
  ]

  // BOM UTF-8 (\uFEFF) para que Excel reconozca el encoding automáticamente
  const csvContent = '\uFEFF' + lines.join('\r\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href     = url
  link.download = `${filename}.csv`
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
