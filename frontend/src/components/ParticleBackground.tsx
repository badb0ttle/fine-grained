import { useEffect, useRef, useCallback } from 'react'
import { useTheme } from './ThemeToggle'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  opacity: number
  pulse: number
  pulseSpeed: number
}

function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const rafRef = useRef<number>(0)
  const { theme } = useTheme()

  const initParticles = useCallback((width: number, height: number) => {
    const count = Math.min(Math.floor((width * height) / 12000), 80)
    const particles: Particle[] = []
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 2.5 + 1.2,
        opacity: Math.random() * 0.5 + 0.3,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.02 + 0.005,
      })
    }
    particlesRef.current = particles
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let w = window.innerWidth
    let h = window.innerHeight

    const resize = () => {
      w = window.innerWidth
      h = window.innerHeight
      const dpr = window.devicePixelRatio || 1
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
      ctx.scale(dpr, dpr)
      initParticles(w, h)
      mouseRef.current = { x: -1000, y: -1000 }
    }

    resize()
    window.addEventListener('resize', resize)

    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', handleMouse)

    // Read CSS variable colors once per frame to react to theme changes
    const getColors = () => {
      const isDark = !document.documentElement.classList.contains('light')
      return {
        particle: isDark ? '108, 92, 231' : '100, 130, 220',   // accent purple / softer blue
        line: isDark ? '108, 92, 231' : '140, 160, 220',
      }
    }

    const animate = () => {
      ctx.clearRect(0, 0, w, h)

      const colors = getColors()
      const particles = particlesRef.current
      const mouse = mouseRef.current
      const maxDist = Math.min(w, h) * 0.18
      const mouseRadius = 120

      // Update & draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]

        // Move
        p.x += p.vx
        p.y += p.vy

        // Wrap around edges
        if (p.x < -20) p.x = w + 20
        if (p.x > w + 20) p.x = -20
        if (p.y < -20) p.y = h + 20
        if (p.y > h + 20) p.y = -20

        // Mouse repulsion
        const dx = p.x - mouse.x
        const dy = p.y - mouse.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < mouseRadius) {
          const force = (mouseRadius - dist) / mouseRadius
          p.vx += (dx / dist) * force * 0.05
          p.vy += (dy / dist) * force * 0.05
          // Dampen
          p.vx *= 0.98
          p.vy *= 0.98
        }

        // Pulse
        p.pulse += p.pulseSpeed
        const pulseAlpha = p.opacity + Math.sin(p.pulse) * 0.1

        // Draw particle
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${colors.particle}, ${pulseAlpha})`
        ctx.fill()
      }

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * 0.25
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(${colors.line}, ${alpha})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      rafRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', handleMouse)
    }
  }, [initParticles])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none"
      style={{ opacity: theme === 'dark' ? 0.85 : 0.55 }}
      aria-hidden="true"
    />
  )
}

export default ParticleBackground
