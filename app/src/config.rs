use http::Uri;

pub const TITLE: &str = "Yoyaku";
pub const HEADER_TITLE: &str = "要約記事録";
pub const REPOSITORY_URL_ENV: &str = "YOYAKU_REPOSITORY_URL";

#[derive(Clone, Debug, Default)]
pub struct SiteConfig {
    repository_url: Option<String>,
}

impl SiteConfig {
    pub fn new(repository_url: Option<String>) -> Self {
        Self {
            repository_url: repository_url.and_then(valid_http_url),
        }
    }

    pub fn repository_url(&self) -> Option<&str> {
        self.repository_url.as_deref()
    }
}

fn valid_http_url(value: String) -> Option<String> {
    let value = value.trim();
    let uri = value.parse::<Uri>().ok()?;
    match uri.scheme_str() {
        Some("http" | "https") if uri.authority().is_some() => Some(value.to_owned()),
        _ => None,
    }
}
