#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;

/// 后端进程(全局单例)
static BACKEND: Mutex<Option<Child>> = Mutex::new(None);

fn main() {
    let app = tauri::Builder::default()
        .setup(|_app| {
            // 应用启动时自动拉起本地Python后端(localhost:8000)
            let backend_dir = std::path::Path::new("python_backend");
            let child = Command::new("python3")
                .args(["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"])
                .current_dir(backend_dir)
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn();

            match child {
                Ok(c) => {
                    *BACKEND.lock().unwrap() = Some(c);
                    println!("[backend] Python后端已启动 (http://127.0.0.1:8000)");
                }
                Err(e) => {
                    println!("[backend] 后端启动失败: {}", e);
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 运行循环: 应用退出时杀掉后端
    app.run(|_app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            let child = BACKEND.lock().unwrap().take();
            if let Some(mut child) = child {
                let _ = child.kill();
                let _ = child.wait();
                println!("[backend] Python后端已停止");
            }
        }
    });
}
