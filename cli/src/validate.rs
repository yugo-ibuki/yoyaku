use std::collections::HashSet;

use anyhow::{Result, bail};
use chrono::NaiveDate;
use url::Url;

use crate::Article;

fn require_text(field: &str, value: &str) -> Result<()> {
    if value.trim().is_empty() {
        bail!("{field} は空にできません");
    }
    Ok(())
}

pub fn validate_article(article: &Article) -> Result<()> {
    require_text("id", &article.id)?;
    require_text("title", &article.title)?;
    require_text("source", &article.source)?;
    require_text("genre", &article.genre)?;

    if !article
        .id
        .chars()
        .all(|character| character.is_ascii_alphanumeric() || matches!(character, '-' | '_'))
    {
        bail!("id は英数字、ハイフン、アンダースコアだけを使用してください");
    }

    let url =
        Url::parse(&article.url).map_err(|error| anyhow::anyhow!("url が不正です: {error}"))?;
    if !matches!(url.scheme(), "http" | "https") {
        bail!("url は http または https で指定してください");
    }
    if article.reading_minutes == 0 {
        bail!("reading_minutes は1以上にしてください");
    }
    if article.technologies.is_empty()
        || article
            .technologies
            .iter()
            .any(|value| value.trim().is_empty())
    {
        bail!("technologies は空でない値を1件以上指定してください");
    }
    if article.summary.is_empty() || article.summary.iter().any(|value| value.trim().is_empty()) {
        bail!("summary は空でない段落を1件以上指定してください");
    }

    let created = NaiveDate::parse_from_str(&article.created_at, "%Y-%m-%d")
        .map_err(|error| anyhow::anyhow!("created_at は YYYY-MM-DD で指定してください: {error}"))?;
    let updated = NaiveDate::parse_from_str(&article.updated_at, "%Y-%m-%d")
        .map_err(|error| anyhow::anyhow!("updated_at は YYYY-MM-DD で指定してください: {error}"))?;
    if updated < created {
        bail!("updated_at は created_at 以降にしてください");
    }
    Ok(())
}

pub fn validate_collection(articles: &[Article]) -> Result<()> {
    let mut ids = HashSet::new();
    let mut urls = HashSet::new();
    for article in articles {
        validate_article(article).map_err(|error| anyhow::anyhow!("{}: {error}", article.id))?;
        if !ids.insert(article.id.as_str()) {
            bail!("id が重複しています: {}", article.id);
        }
        if !urls.insert(article.url.as_str()) {
            bail!("url が重複しています: {}", article.url);
        }
    }
    Ok(())
}
