use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
#[cfg(target_os = "macos")]
use std::io::{BufRead, BufReader};
#[cfg(target_os = "macos")]
use std::path::{Path, PathBuf};
#[cfg(target_os = "macos")]
use std::process::{Child, ChildStdout, Command, Stdio};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
#[cfg(target_os = "macos")]
use std::time::Duration;
use tauri::menu::{Menu, MenuBuilder, MenuItemBuilder};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Emitter, Manager, RunEvent, State, WebviewWindow, WindowEvent};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt as AutostartManagerExt};
#[cfg(not(target_os = "macos"))]
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
    child: Mutex<Option<ManagedChild>>,
    startup_error: Mutex<Option<String>>,
    keep_running_on_close: Mutex<bool>,
    explicit_quit: AtomicBool,
    pending_route: Mutex<Option<String>>,
    notification_route: Mutex<Option<String>>,
}

enum ManagedChild {
    Sidecar(CommandChild),
    #[cfg(target_os = "macos")]
    Macos(Child),
}

#[derive(Clone, Deserialize)]
struct TrayProjectState {
    project_id: String,
    name: String,
    monitoring_state: String,
    muted: bool,
}

#[derive(Clone, Deserialize)]
struct TrayAlertState {
    alert_id: String,
    severity: String,
}

#[derive(Clone, Deserialize)]
struct TrayStatePayload {
    state: String,
    unread_alert_count: u64,
    critical_alert_count: u64,
    active_project_count: u64,
    paused_project_count: u64,
    projects: Vec<TrayProjectState>,
    #[serde(default)]
    recent_alerts: Vec<TrayAlertState>,
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

fn translated_tray_state(strings: &HashMap<String, String>, state: &str) -> String {
    let key = match state {
        "QUIET" => "tray.state.quiet",
        "PAUSED" => "tray.state.paused",
        "ANALYZING" => "tray.state.analyzing",
        "VERIFYING" => "tray.state.verifying",
        "NEEDS_REVIEW" => "tray.state.needsReview",
        "REGRESSION_DETECTED" => "tray.state.regression",
        "APPLY_IN_PROGRESS" => "tray.state.applying",
        "RECOVERY_REQUIRED" => "tray.state.recovery",
        "ENGINE_ERROR" => "tray.state.error",
        _ => "tray.state.monitoring",
    };
    strings[key].clone()
}

fn tray_count(strings: &HashMap<String, String>, key: &str, count: u64) -> String {
    strings[key].replace("{count}", &count.to_string())
}

fn acceptance_tray_lab_state() -> Option<TrayStatePayload> {
    if std::env::var("MELLOWYAK_ACCEPTANCE_LAB").ok().as_deref() != Some("tray-notifications") {
        return None;
    }
    let requested =
        std::env::var("MELLOWYAK_TRAY_LAB_STATE").unwrap_or_else(|_| "monitoring".into());
    let (state, severities): (&str, &[&str]) = match requested.as_str() {
        "information" => ("MONITORING", &["INFO"]),
        "warning" => ("NEEDS_REVIEW", &["WARNING"]),
        "high" => ("NEEDS_REVIEW", &["HIGH"]),
        "critical" => ("REGRESSION_DETECTED", &["CRITICAL"]),
        "mixed" => (
            "REGRESSION_DETECTED",
            &["CRITICAL", "HIGH", "WARNING", "INFO"],
        ),
        "quiet" => ("QUIET", &[]),
        "paused" => ("PAUSED", &[]),
        "analyzing" => ("ANALYZING", &[]),
        "verifying" => ("VERIFYING", &[]),
        "needs-review" => ("NEEDS_REVIEW", &["WARNING"]),
        "regression" => ("REGRESSION_DETECTED", &["CRITICAL"]),
        "applying" => ("APPLY_IN_PROGRESS", &[]),
        "recovery" => ("RECOVERY_REQUIRED", &["CRITICAL"]),
        "engine-error" => ("ENGINE_ERROR", &["CRITICAL"]),
        "monitoring" => ("MONITORING", &[]),
        _ => return None,
    };
    let recent_alerts = severities
        .iter()
        .enumerate()
        .map(|(index, severity)| TrayAlertState {
            alert_id: format!("acceptance-lab-{index}"),
            severity: (*severity).into(),
        })
        .collect::<Vec<_>>();
    Some(TrayStatePayload {
        state: state.into(),
        unread_alert_count: recent_alerts.len() as u64,
        critical_alert_count: recent_alerts
            .iter()
            .filter(|alert| alert.severity == "CRITICAL")
            .count() as u64,
        active_project_count: if state == "PAUSED" { 0 } else { 1 },
        paused_project_count: if state == "PAUSED" { 1 } else { 0 },
        projects: Vec::new(),
        recent_alerts,
    })
}

fn acceptance_notification_lab_payload(
    strings: &HashMap<String, String>,
) -> Option<(String, String)> {
    if std::env::var("MELLOWYAK_ACCEPTANCE_LAB").ok().as_deref() != Some("native-notifications") {
        return None;
    }
    let requested =
        std::env::var("MELLOWYAK_NOTIFICATION_LAB_STATE").unwrap_or_else(|_| "information".into());
    let prefix = match requested.as_str() {
        "information" => "notificationLab.information",
        "warning" => "notificationLab.warning",
        "high" => "notificationLab.high",
        "regression" => "notificationLab.regression",
        "recovery" => "notificationLab.recovery",
        "engine-error" => "notificationLab.error",
        "resolved" => "notificationLab.resolved",
        _ => return None,
    };
    Some((
        strings[&format!("{prefix}.title")].clone(),
        strings[&format!("{prefix}.body")].clone(),
    ))
}

fn native_notification_lab_enabled() -> bool {
    std::env::var("MELLOWYAK_ACCEPTANCE_LAB").ok().as_deref() == Some("native-notifications")
}

#[cfg(target_os = "macos")]
fn install_application_quit_menu(
    app: &tauri::AppHandle,
    strings: &HashMap<String, String>,
) -> tauri::Result<()> {
    let Some(menu) = app.menu() else {
        return Ok(());
    };
    let Some(tauri::menu::MenuItemKind::Submenu(application_menu)) =
        menu.items()?.into_iter().next()
    else {
        return Ok(());
    };
    let item_count = application_menu.items()?.len();
    if item_count == 0 {
        return Ok(());
    }
    application_menu.remove_at(item_count - 1)?;
    let quit = MenuItemBuilder::with_id("application-quit", &strings["tray.quit"])
        .accelerator("CmdOrCtrl+Q")
        .build(app)?;
    application_menu.insert(&quit, item_count - 1)?;
    Ok(())
}

fn build_tray_menu(
    app: &tauri::AppHandle,
    strings: &HashMap<String, String>,
    state: Option<&TrayStatePayload>,
) -> tauri::Result<Menu<tauri::Wry>> {
    let status = state
        .map(|value| translated_tray_state(strings, &value.state))
        .unwrap_or_else(|| strings["tray.state.monitoring"].clone());
    let mut menu = MenuBuilder::new(app)
        .item(&MenuItemBuilder::with_id("open", &strings["tray.open"]).build(app)?)
        .item(
            &MenuItemBuilder::with_id("status", status)
                .enabled(false)
                .build(app)?,
        );
    if let Some(value) = state {
        menu = menu
            .item(
                &MenuItemBuilder::with_id(
                    "unread-count",
                    tray_count(strings, "tray.unreadCount", value.unread_alert_count),
                )
                .enabled(false)
                .build(app)?,
            )
            .item(
                &MenuItemBuilder::with_id(
                    "critical-count",
                    tray_count(strings, "tray.criticalCount", value.critical_alert_count),
                )
                .enabled(false)
                .build(app)?,
            )
            .item(
                &MenuItemBuilder::with_id(
                    "active-count",
                    tray_count(strings, "tray.activeCount", value.active_project_count),
                )
                .enabled(false)
                .build(app)?,
            )
            .item(
                &MenuItemBuilder::with_id(
                    "paused-count",
                    tray_count(strings, "tray.pausedCount", value.paused_project_count),
                )
                .enabled(false)
                .build(app)?,
            );
        for project in value.projects.iter().take(8) {
            let project_label = strings["tray.projectState"]
                .replace("{name}", &project.name)
                .replace("{state}", &project.monitoring_state);
            menu = menu
                .item(
                    &MenuItemBuilder::with_id(
                        format!("project-state:{}", project.project_id),
                        project_label,
                    )
                    .enabled(false)
                    .build(app)?,
                )
                .item(
                    &MenuItemBuilder::with_id(
                        format!("open-project:{}", project.project_id),
                        &strings["tray.openProject"],
                    )
                    .build(app)?,
                )
                .item(
                    &MenuItemBuilder::with_id(
                        format!("pause-project:{}", project.project_id),
                        if project.monitoring_state == "active" {
                            &strings["tray.pauseProject"]
                        } else {
                            &strings["tray.resumeProject"]
                        },
                    )
                    .build(app)?,
                )
                .item(
                    &MenuItemBuilder::with_id(
                        format!("mute-project:{}", project.project_id),
                        if project.muted {
                            &strings["tray.unmuteProject"]
                        } else {
                            &strings["tray.muteProject"]
                        },
                    )
                    .build(app)?,
                );
        }
        for alert in value.recent_alerts.iter().take(5) {
            let severity = match alert.severity.as_str() {
                "CRITICAL" => &strings["tray.alertSeverity.critical"],
                "HIGH" => &strings["tray.alertSeverity.high"],
                "WARNING" => &strings["tray.alertSeverity.warning"],
                _ => &strings["tray.alertSeverity.info"],
            };
            menu = menu.item(
                &MenuItemBuilder::with_id(
                    format!("recent-alert:{}", alert.alert_id),
                    strings["tray.recentAlert"].replace("{severity}", severity),
                )
                .build(app)?,
            );
        }
    }
    if native_notification_lab_enabled() {
        menu = menu.item(
            &MenuItemBuilder::with_id(
                "notification-lab-trigger",
                &strings["notificationLab.trigger"],
            )
            .build(app)?,
        );
    }
    menu.separator()
        .item(&MenuItemBuilder::with_id("alerts", &strings["tray.alerts"]).build(app)?)
        .item(&MenuItemBuilder::with_id("quiet-hour", &strings["tray.quietHour"]).build(app)?)
        .item(
            &MenuItemBuilder::with_id("quiet-tomorrow", &strings["tray.quietTomorrow"])
                .build(app)?,
        )
        .item(&MenuItemBuilder::with_id("quiet-end", &strings["tray.endQuiet"]).build(app)?)
        .item(&MenuItemBuilder::with_id("pause-all", &strings["tray.pauseAll"]).build(app)?)
        .item(&MenuItemBuilder::with_id("resume-all", &strings["tray.resumeAll"]).build(app)?)
        .separator()
        .item(&MenuItemBuilder::with_id("settings", &strings["tray.settings"]).build(app)?)
        .item(&MenuItemBuilder::with_id("quit", &strings["tray.quit"]).build(app)?)
        .build()
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
    #[cfg(target_os = "macos")]
    {
        let identifier = app.config().identifier.clone();
        let _ = notify_rust::set_application(&identifier);
        let handle = notify_rust::Notification::new()
            .summary(&title)
            .body(&body)
            .show()
            .map_err(|error| error.to_string())?;
        if let Some(state) = app.try_state::<EngineState>() {
            if let Ok(mut pending) = state.notification_route.lock() {
                *pending = Some(route.clone());
            }
        }
        let activation_app = app.clone();
        let activation_route = route.clone();
        let was_focused = app
            .get_webview_window("main")
            .and_then(|window| window.is_focused().ok())
            .unwrap_or(false);
        std::thread::spawn(move || {
            handle.wait_for_action(|action| {
                let route_app = app.clone();
                let target_route = route.clone();
                let notification_activated = action != "__closed";
                let _ = app.run_on_main_thread(move || {
                    if notification_activated {
                        if let Some(state) = route_app.try_state::<EngineState>() {
                            if let Ok(mut pending) = state.notification_route.lock() {
                                *pending = None;
                            }
                        }
                        navigate(&route_app, &target_route);
                    }
                });
            });
        });
        if !was_focused {
            std::thread::spawn(move || {
                for _ in 0..100 {
                    std::thread::sleep(Duration::from_millis(100));
                    let focused = activation_app
                        .get_webview_window("main")
                        .and_then(|window| window.is_focused().ok())
                        .unwrap_or(false);
                    if !focused {
                        continue;
                    }
                    let pending = activation_app
                        .try_state::<EngineState>()
                        .and_then(|state| take_notification_route(&state));
                    if pending.as_deref() == Some(activation_route.as_str()) {
                        let route_app = activation_app.clone();
                        let target_route = activation_route.clone();
                        let _ = activation_app
                            .run_on_main_thread(move || navigate(&route_app, &target_route));
                    }
                    return;
                }
                if let Some(state) = activation_app.try_state::<EngineState>() {
                    if let Ok(mut pending) = state.notification_route.lock() {
                        if pending.as_deref() == Some(activation_route.as_str()) {
                            *pending = None;
                        }
                    }
                }
            });
        }
        return Ok(());
    }
    #[cfg(not(target_os = "macos"))]
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|error| error.to_string())
}

fn take_notification_route(state: &EngineState) -> Option<String> {
    state
        .notification_route
        .lock()
        .ok()
        .and_then(|mut route| route.take())
}

#[tauri::command]
fn update_tray_state(app: tauri::AppHandle, state: TrayStatePayload) -> Result<(), String> {
    let strings = translations();
    let lab_state = acceptance_tray_lab_state();
    let effective_state = lab_state.as_ref().unwrap_or(&state);
    let menu = build_tray_menu(&app, &strings, Some(effective_state))
        .map_err(|error| error.to_string())?;
    let tray = app
        .tray_by_id("main-tray")
        .ok_or_else(|| "TRAY_UNAVAILABLE".to_string())?;
    tray.set_menu(Some(menu))
        .map_err(|error| error.to_string())?;
    tray.set_tooltip(Some(translated_tray_state(&strings, &state.state)))
        .map_err(|error| error.to_string())
}

fn stop_engine(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<EngineState>() {
        if let Ok(mut child_slot) = state.child.lock() {
            if let Some(child) = child_slot.take() {
                match child {
                    ManagedChild::Sidecar(child) => {
                        let _ = child.kill();
                    }
                    #[cfg(target_os = "macos")]
                    ManagedChild::Macos(mut child) => {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
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
            match child {
                ManagedChild::Sidecar(child) => {
                    let _ = child.kill();
                }
                #[cfg(target_os = "macos")]
                ManagedChild::Macos(mut child) => {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    }
}

#[cfg(target_os = "macos")]
fn macos_engine_resource(app: &tauri::AppHandle) -> Option<PathBuf> {
    let candidate = app
        .path()
        .resource_dir()
        .ok()?
        .join("engine/mellowyak-engine/mellowyak-engine");
    candidate.is_file().then_some(candidate)
}

#[cfg(target_os = "macos")]
fn spawn_macos_engine(
    path: &Path,
    token: &str,
    parent_pid: &str,
) -> Result<(Child, ChildStdout), String> {
    let mut command = Command::new(path);
    command
        .env("MELLOWYAK_SESSION_TOKEN", token)
        .env("MELLOWYAK_PARENT_PID", parent_pid)
        .env("MELLOWYAK_BIND_HOST", "127.0.0.1")
        .env(
            "MELLOWYAK_ALLOWED_ORIGINS",
            "tauri://localhost,http://tauri.localhost,http://localhost:1420,http://127.0.0.1:1420",
        );
    if let Some(app_bundle) = path
        .ancestors()
        .find(|candidate| candidate.extension().and_then(|value| value.to_str()) == Some("app"))
    {
        command.env("MELLOWYAK_APP_BUNDLE_PATH", app_bundle);
    }
    let mut child = command
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("SIDECAR_START_ERROR:{error}"))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "SIDECAR_STDOUT_UNAVAILABLE".to_string())?;
    Ok((child, stdout))
}

#[cfg(target_os = "macos")]
fn accept_macos_handshake(
    app: &tauri::AppHandle,
    stdout: ChildStdout,
    token: &str,
) -> Result<(), String> {
    let mut line = String::new();
    if BufReader::new(stdout)
        .read_line(&mut line)
        .map_err(|error| format!("SIDECAR_HANDSHAKE_IO:{error}"))?
        == 0
    {
        return Err("SIDECAR_EXITED_BEFORE_HANDSHAKE".into());
    }
    let handshake = serde_json::from_str::<SidecarHandshake>(line.trim())
        .map_err(|_| "SIDECAR_HANDSHAKE_INVALID".to_string())?;
    if handshake.schema != "mellowyak.sidecar.handshake.v1"
        || handshake.mode != "local"
        || handshake.host != "127.0.0.1"
        || handshake.port == 0
    {
        return Err("SIDECAR_HANDSHAKE_REJECTED".into());
    }
    let state = app
        .try_state::<EngineState>()
        .ok_or_else(|| "DESKTOP_STATE_UNAVAILABLE".to_string())?;
    if let Ok(mut bootstrap) = state.bootstrap.lock() {
        *bootstrap = Some(EngineBootstrap {
            host: handshake.host,
            port: handshake.port,
            token: token.to_string(),
        });
    }
    if let Ok(mut startup_error) = state.startup_error.lock() {
        *startup_error = None;
    }
    eprintln!("{}", r#"{"event":"macos_engine_handshake_ready"}"#);
    Ok(())
}

#[cfg(target_os = "macos")]
fn supervise_macos_engine(
    app: tauri::AppHandle,
    engine_path: PathBuf,
    token: String,
    parent_pid: String,
    initial_stdout: ChildStdout,
) {
    if let Err(message) = accept_macos_handshake(&app, initial_stdout, &token) {
        if let Some(state) = app.try_state::<EngineState>() {
            fail_engine_start(&state, message);
        }
        return;
    }
    let mut restarts = 0_u8;
    loop {
        std::thread::sleep(Duration::from_secs(1));
        let Some(state) = app.try_state::<EngineState>() else {
            return;
        };
        if state.explicit_quit.load(Ordering::SeqCst) {
            return;
        }
        let exited = state
            .child
            .lock()
            .ok()
            .map(|mut slot| match slot.as_mut() {
                Some(ManagedChild::Macos(child)) => match child.try_wait() {
                    Ok(Some(_)) => true,
                    Ok(None) => false,
                    Err(error) => {
                        eprintln!(
                            r#"{{"event":"macos_engine_status_error","message":{:?}}}"#,
                            error.to_string()
                        );
                        true
                    }
                },
                _ => false,
            })
            .unwrap_or(false);
        if !exited {
            continue;
        }
        if restarts >= 3 {
            eprintln!("{}", r#"{"event":"macos_engine_restart_limit"}"#);
            fail_engine_start(&state, "SIDECAR_RESTART_LIMIT_REACHED".into());
            return;
        }
        restarts += 1;
        eprintln!(r#"{{"event":"macos_engine_restart","attempt":{restarts}}}"#);
        if let Ok(mut bootstrap) = state.bootstrap.lock() {
            *bootstrap = None;
        }
        match spawn_macos_engine(&engine_path, &token, &parent_pid) {
            Ok((child, stdout)) => {
                if let Ok(mut slot) = state.child.lock() {
                    *slot = Some(ManagedChild::Macos(child));
                }
                if let Err(message) = accept_macos_handshake(&app, stdout, &token) {
                    fail_engine_start(&state, message);
                    return;
                }
            }
            Err(message) => {
                fail_engine_start(&state, message);
                return;
            }
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
            show_native_notification,
            update_tray_state
        ])
        .on_window_event(|window, event| {
            if let WindowEvent::Focused(true) = event {
                let notification_route = window
                    .try_state::<EngineState>()
                    .and_then(|state| take_notification_route(&state));
                if let Some(route) = notification_route {
                    navigate(window.app_handle(), &route);
                }
            }
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
        .on_menu_event(|app, event| {
            if event.id.as_ref() == "application-quit" {
                if let Some(state) = app.try_state::<EngineState>() {
                    state.explicit_quit.store(true, Ordering::SeqCst);
                }
                stop_engine(app);
                app.exit(0);
            }
        })
        .setup(|app| {
            let strings = translations();
            #[cfg(target_os = "macos")]
            install_application_quit_menu(app.handle(), &strings)?;
            let lab_state = acceptance_tray_lab_state();
            let menu = build_tray_menu(app.handle(), &strings, lab_state.as_ref())?;
            let mut tray = TrayIconBuilder::with_id("main-tray")
                .menu(&menu)
                .tooltip(&strings["tray.tooltip"])
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => navigate(app, "home"),
                    "alerts" => navigate(app, "alerts"),
                    "settings" => navigate(app, "settings"),
                    "notification-lab-trigger" => {
                        let strings = translations();
                        if let Some((title, body)) = acceptance_notification_lab_payload(&strings) {
                            if let Err(error) =
                                show_native_notification(app.clone(), title, body, "alerts".into())
                            {
                                eprintln!(
                                    "{}",
                                    serde_json::json!({
                                        "event": "notification_lab_delivery_failed",
                                        "error": error
                                    })
                                );
                            }
                        }
                    }
                    "pause-all" => {
                        let _ = app.emit("mellowyak:monitoring", "pause-all");
                    }
                    "resume-all" => {
                        let _ = app.emit("mellowyak:monitoring", "resume-all");
                    }
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
                    id if id.starts_with("open-project:") => {
                        navigate(app, &format!("project:{}", &id[13..]));
                    }
                    id if id.starts_with("recent-alert:") => {
                        navigate(app, &format!("alert:{}", &id[13..]));
                    }
                    id if id.starts_with("pause-project:") => {
                        let _ = app.emit("mellowyak:project-action", id);
                    }
                    id if id.starts_with("mute-project:") => {
                        let _ = app.emit("mellowyak:project-action", id);
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
            #[cfg(target_os = "macos")]
            if let Some(engine_path) = macos_engine_resource(app.handle()) {
                eprintln!("{}", r#"{"event":"macos_engine_resource_selected"}"#);
                let (child, stdout) = match spawn_macos_engine(&engine_path, &token, &parent_pid) {
                    Ok(value) => value,
                    Err(error) => {
                        eprintln!("{}", r#"{"event":"macos_engine_spawn_failed"}"#);
                        app.manage(EngineState {
                            bootstrap: Mutex::new(None),
                            child: Mutex::new(None),
                            startup_error: Mutex::new(Some(error)),
                            keep_running_on_close: Mutex::new(true),
                            explicit_quit: AtomicBool::new(false),
                            pending_route: Mutex::new(None),
                            notification_route: Mutex::new(None),
                        });
                        return Ok(());
                    }
                };
                app.manage(EngineState {
                    bootstrap: Mutex::new(None),
                    child: Mutex::new(Some(ManagedChild::Macos(child))),
                    startup_error: Mutex::new(None),
                    keep_running_on_close: Mutex::new(true),
                    explicit_quit: AtomicBool::new(false),
                    pending_route: Mutex::new(None),
                    notification_route: Mutex::new(None),
                });
                let app_handle = app.handle().clone();
                tauri::async_runtime::spawn_blocking(move || {
                    supervise_macos_engine(app_handle, engine_path, token, parent_pid, stdout);
                });
                return Ok(());
            }
            #[cfg(target_os = "macos")]
            eprintln!("{}", r#"{"event":"macos_engine_resource_missing"}"#);
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
                        notification_route: Mutex::new(None),
                    });
                    return Ok(());
                }
            };
            app.manage(EngineState {
                bootstrap: Mutex::new(None),
                child: Mutex::new(Some(ManagedChild::Sidecar(child))),
                startup_error: Mutex::new(None),
                keep_running_on_close: Mutex::new(true),
                explicit_quit: AtomicBool::new(false),
                pending_route: Mutex::new(None),
                notification_route: Mutex::new(None),
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
            if let Some(state) = app_handle.try_state::<EngineState>() {
                state.explicit_quit.store(true, Ordering::SeqCst);
            }
            stop_engine(app_handle);
        }
    });
}
