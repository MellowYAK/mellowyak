import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { useEffect, useRef, useState } from "react";

export type LocalEventType =
  | "runtime_detection_started"
  | "runtime_detected"
  | "runtime_profile_validated"
  | "runtime_started"
  | "runtime_stopped"
  | "runtime_failed"
  | "episode_opened"
  | "episode_stabilized"
  | "snapshot_created"
  | "snapshot_reused"
  | "snapshot_failed"
  | "milestone_accepted"
  | "probe_queued"
  | "probe_started"
  | "probe_retrying"
  | "probe_passed"
  | "probe_failed"
  | "probe_inconclusive"
  | "signal_classified"
  | "confirmed_regression"
  | "repair_workspace_created"
  | "repair_workspace_deleted";

export interface LocalProductEvent {
  id?: string;
  type: LocalEventType;
  project_id?: string;
  correlation_id?: string;
  occurred_at?: string;
  payload?: Record<string, unknown>;
}

const EVENT_CHANNEL = "mellowyak:local-event";

export function useLocalEvents(projectId?: string, onEvent?: (event: LocalProductEvent) => void) {
  const [latest, setLatest] = useState<LocalProductEvent | null>(null);
  const callback = useRef(onEvent);

  useEffect(() => { callback.current = onEvent; }, [onEvent]);

  useEffect(() => {
    let active = true;
    let cleanup: UnlistenFn | undefined;
    void listen<LocalProductEvent>(EVENT_CHANNEL, ({ payload }) => {
      if (!active || (projectId && payload.project_id && payload.project_id !== projectId)) return;
      setLatest(payload);
      callback.current?.(payload);
    }).then((unlisten) => {
      if (active) cleanup = unlisten;
      else unlisten();
    }).catch(() => undefined);
    return () => { active = false; cleanup?.(); };
  }, [projectId]);

  return latest;
}
