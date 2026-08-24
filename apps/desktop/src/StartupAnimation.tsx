import { useEffect, useState } from "react";
import type { StartupStatus } from "./api";
import type { TranslationKey } from "./i18n";
import { loadingFrameDurations, loadingFrames } from "./loadingFrames";

export function StartupAnimation({ status, alt }: { status: StartupStatus; alt: string }) {
  const [frame, setFrame] = useState(0);
  const [preloaded, setPreloaded] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all(loadingFrames.map((source) => new Promise<void>((resolve) => {
      const image = new Image();
      image.onload = () => resolve();
      image.onerror = () => resolve();
      image.src = source;
    }))).then(() => active && setPreloaded(true));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (status === "ready" || status === "error") {
      setFrame(7);
      return;
    }
    if (!preloaded || reducedMotion) {
      setFrame(reducedMotion ? 1 : 0);
      return;
    }
    let timer = 0;
    let cancelled = false;
    const schedule = () => {
      if (cancelled || document.hidden) return;
      timer = window.setTimeout(() => {
        setFrame((current) => (current + 1) % loadingFrames.length);
        schedule();
      }, loadingFrameDurations[frame]);
    };
    const visibility = () => {
      window.clearTimeout(timer);
      if (!document.hidden) schedule();
    };
    schedule();
    document.addEventListener("visibilitychange", visibility);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [frame, preloaded, reducedMotion, status]);

  return <div className="startup-animation" aria-hidden="true">
    <img src={loadingFrames[frame]} alt={alt} draggable={false} />
  </div>;
}

export const startupStepKeys: Record<Exclude<StartupStatus, "ready" | "error">, TranslationKey> = {
  starting: "startup.step.services",
  loading_database: "startup.step.database",
  loading_capabilities: "startup.step.capabilities",
  discovering_projects: "startup.step.projects",
  finalizing: "startup.step.finalizing",
};
