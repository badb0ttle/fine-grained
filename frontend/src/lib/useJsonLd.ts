import { useEffect } from 'react'

/**
 * Inject JSON-LD structured data into the page <head>.
 * Automatically cleans up on unmount.
 */
export function useJsonLd(schema: Record<string, unknown> | null) {
  useEffect(() => {
    if (!schema) return

    const script = document.createElement('script')
    script.type = 'application/ld+json'
    script.textContent = JSON.stringify(schema)
    document.head.appendChild(script)

    return () => {
      document.head.removeChild(script)
    }
  }, [schema])
}
