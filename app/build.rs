use std::{env, fs, path::PathBuf};

const TOPCOAT_RUNTIME_VERSION: &str = "0.5.0";

fn main() {
    println!("cargo:rerun-if-env-changed=CARGO_HOME");

    let cargo_home = env::var_os("CARGO_HOME").map_or_else(
        || {
            env::var_os("HOME")
                .map(PathBuf::from)
                .map(|home| home.join(".cargo"))
                .expect("CARGO_HOME and HOME are both unavailable")
        },
        PathBuf::from,
    );
    let registry_sources = cargo_home.join("registry/src");
    let package_name = format!("topcoat-runtime-{TOPCOAT_RUNTIME_VERSION}");

    let runtime_script = fs::read_dir(&registry_sources)
        .unwrap_or_else(|error| {
            panic!(
                "cannot read Cargo registry sources at {}: {error}",
                registry_sources.display()
            )
        })
        .filter_map(Result::ok)
        .map(|registry| {
            registry
                .path()
                .join(&package_name)
                .join("browser/dist/index.js")
        })
        .find(|path| path.is_file())
        .unwrap_or_else(|| {
            panic!(
                "Topcoat Runtime {TOPCOAT_RUNTIME_VERSION} browser script was not found below {}; run `cargo fetch` and retry",
                registry_sources.display()
            )
        });

    println!("cargo:rerun-if-changed={}", runtime_script.display());
    println!(
        "cargo:rustc-env=TOPCOAT_RUNTIME_JS={}",
        runtime_script.display()
    );
}
