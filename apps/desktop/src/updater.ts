import { relaunch } from "@tauri-apps/plugin-process";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { useCallback, useEffect, useState } from "react";

export type UpdaterPhase = "idle" | "available" | "installing" | "relaunching";

export interface UpdaterState {
  phase: UpdaterPhase;
  version: string | null;
  install: () => Promise<void>;
}

function isPackagedDesktop(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

export function useDesktopUpdater(): UpdaterState {
  const [update, setUpdate] = useState<Update | null>(null);
  const [phase, setPhase] = useState<UpdaterPhase>("idle");

  useEffect(() => {
    if (!isPackagedDesktop()) return;
    let active = true;
    void check({ timeout: 10_000 })
      .then((candidate) => {
        if (!active || !candidate) return;
        setUpdate(candidate);
        setPhase("available");
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const install = useCallback(async () => {
    if (!update || phase !== "available") return;
    setPhase("installing");
    try {
      await update.downloadAndInstall();
      setPhase("relaunching");
      await relaunch();
    } catch {
      setPhase("available");
    }
  }, [phase, update]);

  return { phase, version: update?.version ?? null, install };
}
