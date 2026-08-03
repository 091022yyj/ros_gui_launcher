import { useRef, useEffect, useState } from "react";

/**
 * 基于 requestAnimationFrame 的动画 Hook
 * 自动适配显示器刷新率（60/120/144/240Hz+）
 * @param callback 每帧回调，接收 deltaTime（毫秒）
 * @param deps 依赖数组
 */
export function useAnimationFrame(
  callback: (deltaTime: number) => void,
  deps: React.DependencyList = []
) {
  const requestRef = useRef<number | undefined>(undefined);
  const previousTimeRef = useRef<number | undefined>(undefined);
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const animate = (time: number) => {
      if (previousTimeRef.current !== undefined) {
        const deltaTime = time - previousTimeRef.current;
        callbackRef.current(deltaTime);
      }
      previousTimeRef.current = time;
      requestRef.current = requestAnimationFrame(animate);
    };

    requestRef.current = requestAnimationFrame(animate);
    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, deps);
}

/** 弹簧物理动画（帧率无关） */
export function usePhysicsAnimation(
  target: number,
  tension = 300,
  friction = 30,
  mass = 1.0
) {
  const state = useRef({ current: target, velocity: 0, target });

  useEffect(() => {
    state.current.target = target;
  }, [target]);

  useAnimationFrame((deltaTime) => {
    const dt = deltaTime / 1000;
    const { current, velocity } = state.current;
    const displacement = current - state.current.target;
    const springForce = -tension * displacement;
    const dampingForce = -friction * velocity;
    const acceleration = (springForce + dampingForce) / mass;
    state.current.velocity += acceleration * dt;
    state.current.current += state.current.velocity * dt;
  });

  return state.current.current;
}

/** 实时FPS显示 */
export function useFPS() {
  const [fps, setFps] = useState(0);
  const counter = useRef({ frames: 0, lastTime: 0 });

  useAnimationFrame((deltaTime) => {
    counter.current.frames++;
    counter.current.lastTime += deltaTime;
    if (counter.current.lastTime >= 1000) {
      setFps(counter.current.frames);
      counter.current.frames = 0;
      counter.current.lastTime = 0;
    }
  });

  return fps;
}
