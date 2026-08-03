import { useRef, useState } from "react";
import { useAnimationFrame, useFPS } from "../hooks/useAnimationFrame";

interface DataPoint {
  time: number;
  value: number;
}

/** 实时图表(自适应帧率Canvas) */
export function RealtimeChart({
  color = "#0071e3",
  label = "CPU",
}: {
  color?: string;
  label?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dataRef = useRef<DataPoint[]>([]);
  const [fps, setFps] = useState(0);
  const counter = useRef({ frames: 0, lastTime: 0 });
  const [value, setValue] = useState(0);

  useAnimationFrame((deltaTime) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    counter.current.frames++;
    counter.current.lastTime += deltaTime;
    if (counter.current.lastTime >= 1000) {
      setFps(counter.current.frames);
      counter.current.frames = 0;
      counter.current.lastTime = 0;
    }

    // 模拟数据
    const now = Date.now();
    const v = Math.sin(now / 800) * 25 + 35 + Math.random() * 5;
    setValue(v);
    dataRef.current.push({ time: now, value: v });
    if (dataRef.current.length > 200) dataRef.current.shift();

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    // 渐变填充
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, `${color}4D`);
    gradient.addColorStop(1, `${color}00`);

    const data = dataRef.current;
    if (data.length < 2) return;
    const stepX = width / (data.length - 1);

    ctx.beginPath();
    ctx.moveTo(0, height);
    for (let i = 0; i < data.length; i++) {
      const x = i * stepX;
      const y = height - (data[i].value / 100) * height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.lineTo(width, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // 平滑曲线
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = i * stepX;
      const y = height - (data[i].value / 100) * height;
      if (i === 0) ctx.moveTo(x, y);
      else {
        const prevX = (i - 1) * stepX;
        const prevY = height - (data[i - 1].value / 100) * height;
        const cp1x = prevX + stepX / 2;
        const cp2x = x - stepX / 2;
        ctx.bezierCurveTo(cp1x, prevY, cp2x, y, x, y);
      }
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.stroke();
  });

  return (
    <div className="relative glass p-4 rounded-2xl">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-[--text-secondary]">{label}</span>
        <span className="text-lg font-bold" style={{ color }}>
          {value.toFixed(1)}%
        </span>
      </div>
      <canvas ref={canvasRef} width={560} height={160} className="w-full rounded-xl" />
      <div className="absolute top-2 right-2 text-xs text-[--text-tertiary]">
        {fps} FPS
      </div>
    </div>
  );
}
