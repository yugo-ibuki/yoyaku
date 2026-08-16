use topcoat::{
    asset::{AssetConfig, Manifest},
    runtime::SCRIPT,
};

pub fn script() -> &'static str {
    include_str!(env!("TOPCOAT_RUNTIME_JS"))
}

pub fn config() -> AssetConfig {
    let manifest = Manifest::parse(&format!(
        r#"version = 1

[[assets]]
id = {}
file = "topcoat-runtime.js"
hash = "embedded"
content_type = "text/javascript; charset=utf-8"
"#,
        SCRIPT.id().as_u64()
    ))
    .expect("embedded Topcoat Runtime manifest must be valid");

    AssetConfig::hosted_at("/assets", manifest)
}
