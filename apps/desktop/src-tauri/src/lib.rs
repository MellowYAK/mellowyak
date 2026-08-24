use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
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
    bootstrap: Mutex<Option<EngineBootstrap>>,
    child: Mutex<Option<CommandChild>>,
    startup_error: Mutex<Option<String>>,
}

fn random_session_token() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|value| format!("{value:02x}")).collect()
}

#[tauri::command]
fn engine_bootstrap(state: State<'_, EngineState>) -> Result<EngineBootstrap, String> {
    if let Ok(bootstrap) = state.bootstrap.lock() {
        if let Some(value) = bootstrap.as_ref() {
            return Ok(value.clone());
        }
    }
    if let Ok(startup_error) = state.startup_error.lock() {
        if let Some(value) = startup_error.as_ref() {
            return Err(value.clone());
        }
    }
    Err("ENGINE_STARTING".into())
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

fn fail_engine_start(state: &EngineState, message: String) {
    if let Ok(mut error) = state.startup_error.lock() {
        *error = Some(message);
    }
    if let Ok(mut child_slot) = state.child.lock() {
        if let Some(child) = child_slot.take() {
            let _ = child.kill();
        }
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
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
            let (mut events, child) = match command.spawn() {
                Ok(value) => value,
                Err(error) => {
                    app.manage(EngineState {
                        bootstrap: Mutex::new(None),
                        child: Mutex::new(None),
                        startup_error: Mutex::new(Some(format!("SIDECAR_START_ERROR:{error}"))),
                    });
                    return Ok(());
                }
            };
            app.manage(EngineState {
                bootstrap: Mutex::new(None),
                child: Mutex::new(Some(child)),
                startup_error: Mutex::new(None),
            });
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    let result = match event {
                        CommandEvent::Stdout(bytes) => {
                            let line = String::from_utf8_lossy(&bytes);
                            serde_json::from_str::<SidecarHandshake>(line.trim())
                                .map_err(|_| "SIDECAR_HANDSHAKE_INVALID".to_string())
                        }
                        CommandEvent::Error(message) => {
                            Err(format!("SIDECAR_START_ERROR:{message}"))
                        }
                        CommandEvent::Terminated(_) => {
                            Err("SIDECAR_EXITED_BEFORE_HANDSHAKE".into())
                        }
                        _ => continue,
                    };
                    if let Some(state) = app_handle.try_state::<EngineState>() {
                        match result {
                            Ok(handshake)
                                if handshake.schema == "mellowyak.sidecar.handshake.v1"
                                    && handshake.mode == "local"
                                    && handshake.host == "127.0.0.1"
                                    && handshake.port > 0 =>
                            {
                                if let Ok(mut bootstrap) = state.bootstrap.lock() {
                                    *bootstrap = Some(EngineBootstrap {
                                        host: handshake.host,
                                        port: handshake.port,
                                        token,
                                    });
                                }
                            }
                            Ok(_) => {
                                fail_engine_start(&state, "SIDECAR_HANDSHAKE_REJECTED".into());
                            }
                            Err(message) => {
                                fail_engine_start(&state, message);
                            }
                        }
                    }
                    break;
                }
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
