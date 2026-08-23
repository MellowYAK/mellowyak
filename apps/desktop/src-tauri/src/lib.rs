use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::sync::{mpsc, Mutex};
use std::time::Duration;
use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

#[derive(Clone, Deserialize, Serialize)]
struct SidecarHandshake {
    schema: String,
    host: String,
    port: u16,
    mode: String,
}

#[derive(Clone, Serialize)]
struct EngineBootstrap {
    host: String,
    port: u16,
    token: String,
}

struct EngineState {
    bootstrap: EngineBootstrap,
    child: Mutex<Option<CommandChild>>,
}

fn random_session_token() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|value| format!("{value:02x}")).collect()
}

#[tauri::command]
fn engine_bootstrap(state: State<'_, EngineState>) -> EngineBootstrap {
    state.bootstrap.clone()
}

fn stop_engine(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<EngineState>() {
        if let Ok(mut child_slot) = state.child.lock() {
            if let Some(child) = child_slot.take() {
                let _ = child.kill();
            }
        }
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![engine_bootstrap])
        .setup(|app| {
            let token = random_session_token();
            let parent_pid = std::process::id().to_string();
            let command = app
                .shell()
                .sidecar("mellowyak-engine")?
                .env("MELLOWYAK_SESSION_TOKEN", &token)
                .env("MELLOWYAK_PARENT_PID", parent_pid)
                .env("MELLOWYAK_BIND_HOST", "127.0.0.1")
                .env(
                    "MELLOWYAK_ALLOWED_ORIGINS",
                    "tauri://localhost,http://tauri.localhost,http://localhost:1420,http://127.0.0.1:1420",
                );
            let (mut events, child) = command.spawn()?;
            let (handshake_tx, handshake_rx) = mpsc::sync_channel::<Result<SidecarHandshake, String>>(1);

            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    match event {
                        CommandEvent::Stdout(bytes) => {
                            let line = String::from_utf8_lossy(&bytes);
                            let parsed = serde_json::from_str::<SidecarHandshake>(line.trim())
                                .map_err(|_| "SIDECAR_HANDSHAKE_INVALID".to_string());
                            let _ = handshake_tx.send(parsed);
                            break;
                        }
                        CommandEvent::Error(message) => {
                            let _ = handshake_tx.send(Err(format!("SIDECAR_START_ERROR:{message}")));
                            break;
                        }
                        CommandEvent::Terminated(_) => {
                            let _ = handshake_tx.send(Err("SIDECAR_EXITED_BEFORE_HANDSHAKE".into()));
                            break;
                        }
                        _ => {}
                    }
                }
            });

            let handshake = handshake_rx
                .recv_timeout(Duration::from_secs(20))
                .map_err(|_| "SIDECAR_HANDSHAKE_TIMEOUT")??;
            if handshake.schema != "mellowyak.sidecar.handshake.v1"
                || handshake.mode != "local"
                || handshake.host != "127.0.0.1"
                || handshake.port == 0
            {
                let _ = child.kill();
                return Err("SIDECAR_HANDSHAKE_REJECTED".into());
            }
            app.manage(EngineState {
                bootstrap: EngineBootstrap {
                    host: handshake.host,
                    port: handshake.port,
                    token,
                },
                child: Mutex::new(Some(child)),
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build MellowYak desktop application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_engine(app_handle);
        }
    });
}
