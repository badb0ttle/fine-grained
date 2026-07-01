/**
 * ParticleBackground - 动态粒子背景动画（Canvas 2D）
 * 
 * 功能：
 *   - 在 fixed 全屏 Canvas 上绘制随机粒子网络
 *   - 粒子特性：随机运动 + 边缘环绕 + 鼠标排斥 + 透明度脉冲呼吸
 *   - 粒子之间根据距离绘制半透明连线（最近邻连接）
 *   - 支持暗色/亮色主题切换（粒子颜色自适应）
 *   - 鼠标交互：光标附近粒子被推开（半径 120px）
 * 
 * 技术细节：
 *   - requestAnimationFrame 驱动 60fps 动画循环
 *   - DPR（devicePixelRatio）适配，保持高清渲染
 *   - window resize 时重新初始化粒子分布
 *   - pointer-events-none 不阻挡页面交互
 */

import { useEffect, useRef, useCallback } from 'react'
import { useTheme } from './ThemeToggle'

/** Particle 粒子对象的数据结构 */
interface Particle {
  x: number        // 横向位置
  y: number        // 纵向位置
  vx: number       // 横向速度
  vy: number       // 纵向速度
  radius: number   // 粒子半径
  opacity: number  // 基础透明度
  pulse: number    // 脉冲相位（用于呼吸效果）
  pulseSpeed: number // 脉冲速度
}

function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])   // 粒子数组（避免 useState 触发重渲染）
  const mouseRef = useRef({ x: -1000, y: -1000 }) // 鼠标位置（初始在屏幕外）
  const rafRef = useRef<number>(0)              // requestAnimationFrame ID
  const { theme } = useTheme()

  /** 初始化粒子：根据画布尺寸动态计算粒子数量（最多80个） */
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

  /** Canvas 动画主逻辑 useEffect */
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let w = window.innerWidth
    let h = window.innerHeight

    /** resize 处理：重新设置 Canvas 尺寸并重新初始化粒子 */
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

    /** 鼠标移动事件：更新鼠标位置 */
    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', handleMouse)

    /** 每帧读取主题颜色（通过 DOM class 判断暗色/亮色，避免 React state 依赖） */
    const getColors = () => {
      const isDark = !document.documentElement.classList.contains('light')
      return {
        particle: isDark ? '108, 92, 231' : '100, 130, 220',   // 暗色：accent purple / 亮色：softer blue
        line: isDark ? '108, 92, 231' : '140, 160, 220',
      }
    }

    /** 动画帧循环：更新粒子位置 + 绘制粒子 + 绘制连线 */
    const animate = () => {
      ctx.clearRect(0, 0, w, h)

      const colors = getColors()
      const particles = particlesRef.current
      const mouse = mouseRef.current
      const maxDist = Math.min(w, h) * 0.18   // 连线最大距离
      const mouseRadius = 120                  // 鼠标排斥半径

      // 更新粒子位置 + 绘制粒子
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]

        // 位置更新（匀速运动）
        p.x += p.vx
        p.y += p.vy

        // 边缘环绕（超出画布后从对面重新进入）
        if (p.x < -20) p.x = w + 20
        if (p.x > w + 20) p.x = -20
        if (p.y < -20) p.y = h + 20
        if (p.y > h + 20) p.y = -20

        // 鼠标排斥力（鼠标附近粒子被推开）
        const dx = p.x - mouse.x
        const dy = p.y - mouse.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < mouseRadius) {
          const force = (mouseRadius - dist) / mouseRadius
          p.vx += (dx / dist) * force * 0.05
          p.vy += (dy / dist) * force * 0.05
          // 阻尼衰减
          p.vx *= 0.98
          p.vy *= 0.98
        }

        // 透明度脉冲呼吸效果（正弦波）
        p.pulse += p.pulseSpeed
        const pulseAlpha = p.opacity + Math.sin(p.pulse) * 0.1

        // 绘制粒子圆点
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${colors.particle}, ${pulseAlpha})`
        ctx.fill()
      }

      // 绘制粒子间连线（最近邻距离范围内绘制半透明线）
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * 0.25  // 距离越近透明度越高
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

    // 清理：取消动画帧 + 移除事件监听
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
