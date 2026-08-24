use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Emitter, Manager, RunEvent, State, WebviewWindow, WindowEvent};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt as AutostartManagerExt};
use tauri_plugin_notification::NotificationExt;
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
    keep_running_on_close: Mutex<bool>,
    explicit_quit: AtomicBool,
    pending_route: Mutex<Option<String>>,
}

fn random_session_token() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|value| format!("{value:02x}")).collect()
}

fn translations() -> HashMap<String, String> {
    let locale = sys_locale::get_locale().unwrap_or_else(|| "en".into());
    let source = if locale.to_lowercase().starts_with("he") {
        include_str!("../i18n/he.json")
    } else {
        include_str!("../i18n/en.json")
    };
    serde_json::from_str(source).expect("valid embedded tray translations")
}

fn show_main(window: &WebviewWindow) {
    let _ = window.show();
    let _ = window.unminimize();
    let _ = window.set_focus();
}

fn navigate(app: &tauri::AppHandle, route: &str) {
    if let Some(window) = app.get_webview_window("main") {
        show_main(&window);
    }
    if let Some(state) = app.try_state::<EngineState>() {
        if let Ok(mut pending) = state.pending_route.lock() {
            *pending = Some(route.to_string());
        }
    }
    let _ = app.emit("mellowyak:navigate", route);
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

#[tauri::command]
fn set_keep_running_on_close(enabled: bool, state: State<'_, EngineState>) -> Result<(), String> {
    *state
        .keep_running_on_close
        .lock()
        .map_err(|_| "DESKTOP_STATE_UNAVAILABLE")? = enabled;
    Ok(())
}

#[tauri::command]
fn take_pending_route(state: State<'_, EngineState>) -> Option<String> {
    state
        .pending_route
        .lock()
        .ok()
        .and_then(|mut route| route.take())
}

#[tauri::command]
fn get_start_at_login(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn set_start_at_login(app: tauri::AppHandle, enabled: bool) -> Result<bool, String> {
    let manager = app.autolaunch();
    if enabled {
        manager.enable()
    } else {
        manager.disable()
    }
    .map_err(|error| error.to_string())?;
    manager.is_enabled().map_err(|error| error.to_string())
}

#[tauri::command]
fn show_native_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
    route: String,
) -> Result<(), String> {
    if let Some(state) = app.try_state::<EngineState>() {
        if let Ok(mut pending) = state.pending_route.lock() {
            *pending = Some(route);
        }
    }
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|error| error.to_string())
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
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                show_main(&window);
            }
        }))
        .plugin(
            tauri_plugin_autostart::Builder::new()
                .macos_launcher(MacosLauncher::LaunchAgent)
                .build(),
        )
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            engine_bootstrap,
            set_keep_running_on_close,
            take_pending_route,
            get_start_at_login,
            set_start_at_login,
            show_native_notification
        ])
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if let Some(state) = window.try_state::<EngineState>() {
                    let keep_running = state
                        .keep_running_on_close
                        .lock()
                        .map(|value| *value)
                        .unwrap_or(true);
                    if keep_running && !state.explicit_quit.load(Ordering::SeqCst) {
                        api.prevent_close();
                        let _ = window.hide();
                    }
                }
            }
        })
        .setup(|app| {
            let strings = translations();
            let menu = MenuBuilder::new(app)
                .item(&MenuItemBuilder::with_id("open", &strings["tray.open"]).build(app)?)
                .item(
                    &MenuItemBuilder::with_id("status", &strings["tray.status"])
                        .enabled(false)
                        .build(app)?,
                )
                .separator()
                .item(&MenuItemBuilder::with_id("alerts", &strings["tray.alerts"]).build(app)?)
                .item(
                    &MenuItemBuilder::with_id("quiet-hour", &strings["tray.quietHour"])
                        .build(app)?,
                )
                .item(
                    &MenuItemBuilder::with_id("quiet-tomorrow", &strings["tray.quietTomorrow"])
                        .build(app)?,
                )
                .item(
                    &MenuItemBuilder::with_id("quiet-end", &strings["tray.endQuiet"])
                        .build(app)?,
                )
                .separator()
                .item(
                    &MenuItemBuilder::with_id("settings", &strings["tray.settings"]).build(app)?,
                )
                .item(&MenuItemBuilder::with_id("quit", &strings["tray.quit"]).build(app)?)
                .build()?;
            let mut tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip(&strings["tray.tooltip"])
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => navigate(app, "home"),
                    "alerts" => navigate(app, "alerts"),
                    "settings" => navigate(app, "settings"),
                    "quiet-hour" => {
                        let _ = app.emit("mellowyak:quiet", "one_hour");
                    }
                    "quiet-tomorrow" => {
                        let _ = app.emit("mellowyak:quiet", "until_tomorrow");
                    }
                    "quiet-end" => {
                        let _ = app.emit("mellowyak:quiet", "off");
                    }
                    "quit" => {
                        if let Some(state) = app.try_state::<EngineState>() {
                            state.explicit_quit.store(true, Ordering::SeqCst);
                        }
                        stop_engine(app);
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        navigate(tray.app_handle(), "home");
                    }
                });
            if let Some(icon) = app.default_window_icon().cloned() {
                tray = tray.icon(icon);
            }
            tray.build(app)?;

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
                        keep_running_on_close: Mutex::new(true),
                        explicit_quit: AtomicBool::new(false),
                        pending_route: Mutex::new(None),
                    });
                    return Ok(());
                }
            };
            app.manage(EngineState {
                bootstrap: Mutex::new(None),
                child: Mutex::new(Some(child)),
                startup_error: Mutex::new(None),
                keep_running_on_close: Mutex::new(true),
                explicit_quit: AtomicBool::new(false),
                pending_route: Mutex::new(None),
            });
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    let result = match event {
                        CommandEvent::Stdout(bytes) => serde_json::from_str::<SidecarHandshake>(
                            String::from_utf8_lossy(&bytes).trim(),
                        )
                        .map_err(|_| "SIDECAR_HANDSHAKE_INVALID".to_string()),
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
                                fail_engine_start(&state, "SIDECAR_HANDSHAKE_REJECTED".into())
                            }
                            Err(message) => fail_engine_start(&state, message),
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
