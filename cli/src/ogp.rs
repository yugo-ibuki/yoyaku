use std::{collections::HashMap, io::Read, time::Duration};

use anyhow::{Result, bail};
use reqwest::{blocking::Client, header::CONTENT_TYPE, redirect::Policy};
use scraper::{Html, Selector};
use url::Url;

use crate::Ogp;

const MAX_HTML_BYTES: u64 = 2_000_000;
const REPOSITORY_URL_ENV: &str = "YOYAKU_REPOSITORY_URL";

pub fn parse_ogp(html: &str, base_url: &Url) -> Result<Ogp> {
    let document = Html::parse_document(html);
    let meta_selector = Selector::parse("meta").expect("valid meta selector");
    let title_selector = Selector::parse("title").expect("valid title selector");
    let mut metadata = HashMap::new();

    for element in document.select(&meta_selector) {
        let Some(key) = element
            .value()
            .attr("property")
            .or_else(|| element.value().attr("name"))
        else {
            continue;
        };
        let Some(content) = element
            .value()
            .attr("content")
            .map(str::trim)
            .filter(|value| !value.is_empty())
        else {
            continue;
        };
        metadata
            .entry(key.to_ascii_lowercase())
            .or_insert_with(|| content.to_owned());
    }

    let title = metadata
        .get("og:title")
        .or_else(|| metadata.get("twitter:title"))
        .cloned()
        .or_else(|| {
            document
                .select(&title_selector)
                .next()
                .map(|element| element.text().collect::<String>().trim().to_owned())
                .filter(|value| !value.is_empty())
        });
    let description = metadata
        .get("og:description")
        .or_else(|| metadata.get("twitter:description"))
        .or_else(|| metadata.get("description"))
        .cloned();
    let image_url = metadata
        .get("og:image")
        .or_else(|| metadata.get("twitter:image"))
        .and_then(|value| base_url.join(value).ok())
        .filter(|url| matches!(url.scheme(), "http" | "https"))
        .map(Into::into);

    Ok(Ogp {
        image_url,
        title,
        description,
    })
}

pub fn fetch_ogp(url: &Url) -> Result<Ogp> {
    let repository_url = std::env::var(REPOSITORY_URL_ENV).ok();
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .redirect(Policy::limited(5))
        .user_agent(user_agent_for_repository(repository_url.as_deref()))
        .build()?;
    let response = client.get(url.clone()).send()?.error_for_status()?;
    if let Some(content_type) = response
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        && !content_type.contains("text/html")
        && !content_type.contains("application/xhtml+xml")
    {
        bail!("HTMLではない応答です: {content_type}");
    }

    let mut body = String::new();
    response
        .take(MAX_HTML_BYTES + 1)
        .read_to_string(&mut body)?;
    if body.len() as u64 > MAX_HTML_BYTES {
        bail!("HTMLが上限の{MAX_HTML_BYTES}バイトを超えています");
    }
    parse_ogp(&body, url)
}

fn user_agent_for_repository(repository_url: Option<&str>) -> String {
    repository_url
        .map(str::trim)
        .filter(|value| value.starts_with("https://") || value.starts_with("http://"))
        .map_or_else(
            || "yoyaku/0.1".to_owned(),
            |value| format!("yoyaku/0.1 (+{value})"),
        )
}

#[cfg(test)]
mod tests {
    use super::user_agent_for_repository;

    #[test]
    fn user_agent_uses_the_repository_url_only_when_configured() {
        assert_eq!(user_agent_for_repository(None), "yoyaku/0.1");
        assert_eq!(
            user_agent_for_repository(Some("https://github.com/example/yoyaku")),
            "yoyaku/0.1 (+https://github.com/example/yoyaku)"
        );
    }
}
