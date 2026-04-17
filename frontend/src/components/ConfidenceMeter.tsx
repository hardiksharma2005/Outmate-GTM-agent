import { useEffect, useRef } from 'react'

interface ConfidenceMeterProps {
  value: number  // 0.0 to 1.0
  size?: number
}

export function ConfidenceMeter({ value, size = 160 }: ConfidenceMeterProps) {
  const animRef = useRef<number>(0)
  const currentRef = useRef<number>(0)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const pct = Math.max(0, Math.min(1, value))
  const label =
    pct >= 0.75 ? 'High' :
    pct >= 0.5  ? 'Good' :
    pct >= 0.3  ? 'Fair' : 'Low'
  const color =
    pct >= 0.6 ? '#22c55e' :
    pct >= 0.35 ? '#f59e0b' : '#ef4444'

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const target = pct
    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = (size / 2 + 24) * dpr
    canvas.style.width = size + 'px'
    canvas.style.height = (size / 2 + 24) + 'px'
    ctx.scale(dpr, dpr)

    const cx = size / 2
    const cy = size / 2
    const r = size / 2 - 14
    const startAngle = Math.PI
    const endAngle = 2 * Math.PI

    function draw(current: number) {
      ctx!.clearRect(0, 0, size, size)

      // Background arc
      ctx!.beginPath()
      ctx!.arc(cx, cy, r, startAngle, endAngle)
      ctx!.strokeStyle = '#1e293b'
      ctx!.lineWidth = 14
      ctx!.lineCap = 'round'
      ctx!.stroke()

      // Value arc
      const arcEnd = startAngle + current * Math.PI
      ctx!.beginPath()
      ctx!.arc(cx, cy, r, startAngle, arcEnd)
      ctx!.strokeStyle = color
      ctx!.lineWidth = 14
      ctx!.lineCap = 'round'
      ctx!.stroke()

      // Center text
      ctx!.fillStyle = color
      ctx!.font = `bold ${size * 0.18}px system-ui`
      ctx!.textAlign = 'center'
      ctx!.textBaseline = 'middle'
      ctx!.fillText(`${Math.round(current * 100)}%`, cx, cy - 10)

      ctx!.fillStyle = '#94a3b8'
      ctx!.font = `${size * 0.1}px system-ui`
      ctx!.fillText(label, cx, cy + 12)
    }

    cancelAnimationFrame(animRef.current)
    const duration = 600
    const start = performance.now()
    const from = currentRef.current

    function animate(now: number) {
      const elapsed = now - start
      const progress = Math.min(1, elapsed / duration)
      const eased = 1 - Math.pow(1 - progress, 3)  // ease-out cubic
      const current = from + (target - from) * eased
      currentRef.current = current
      draw(current)
      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate)
      }
    }

    animRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animRef.current)
  }, [pct, color, label, size])

  return (
    <div className="confidence-meter" title={`Confidence: ${Math.round(pct * 100)}%`}>
      <canvas ref={canvasRef} />
      <div className="confidence-label">Confidence</div>
    </div>
  )
}
