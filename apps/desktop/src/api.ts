import { invoke } from "@tauri-apps/api/core";
import type { paths } from "./generated/api";

export type Health = paths["/health"]["get"]["responses"][200]["content"]["application/json"];
export type Readiness = paths["/readiness"]["get"]["responses"][200]["content"]["application/json"];
export type Installation = paths["/installation"]["get"]["responses"][200]["content"]["application/json"];
export type Privacy = paths["/settings/privacy"]["get"]["responses"][200]["content"]["application/json"];
export type StoragePaths = paths["/storage/paths"]["get"]["responses"][200]["content"]["application/json"];

export interface EngineBootstrap {
  host: "127.0.0.1" | "::1";
  port: number;
  token: string;
}
export interface SetupSnapshot {
  health: Health;
  readiness: Readiness;
  installation: Installation;
  privacy: Privacy;
  storage: StoragePaths;
}

let bootstrapPromise: Promise<EngineBootstrap> | undefined;

function bootstrap(): Promise<EngineBootstrap> {
  bootstrapPromise ??= invoke<EngineBootstrap>("engine_bootstrap");
  return bootstrapPromise;
}

async function engineFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const connection = await bootstrap();
  const response = await fetch(`http://${connection.host}:${connection.port}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${connection.token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`LOCAL_ENGINE_${response.status}`);
  }
  return (await response.json()) as T;
}

export async function loadSetupSnapshot(): Promise<SetupSnapshot> {
  const [health, readiness, installation, privacy, storage] = await Promise.all([
    engineFetch<Health>("/health"),
    engineFetch<Readiness>("/readiness"),
    engineFetch<Installation>("/installation"),
    engineFetch<Privacy>("/settings/privacy"),
    engineFetch<StoragePaths>("/storage/paths"),
  ]);
  return { health, readiness, installation, privacy, storage };
}

export async function openDataFolder(): Promise<void> {
  await engineFetch("/system/open-data-folder", { method: "POST", body: "{}" });
}

export function resetBootstrapForTests(): void {
  bootstrapPromise = undefined;
}
