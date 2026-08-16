use std::cmp::Ordering;

use unicode_normalization::UnicodeNormalization;
use yoyaku::{Article, ArticleIndex};

const MAX_QUERY_CHARS: usize = 200;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SearchQuery {
    pub keyword: String,
    pub genre: String,
    pub technology: String,
    pub source: String,
    pub created_from: String,
    pub created_to: String,
    pub max_minutes: String,
    pub sort: String,
}

impl SearchQuery {
    pub fn active_conditions(&self) -> Vec<String> {
        let mut conditions = Vec::new();
        let keyword = limited(self.keyword.trim());
        if !keyword.is_empty() {
            conditions.push(format!("検索: {keyword}"));
        }
        for value in [&self.genre, &self.technology, &self.source] {
            let value = limited(value.trim());
            if !value.is_empty() {
                conditions.push(value);
            }
        }
        if let Some(date) = valid_date(&self.created_from) {
            conditions.push(format!("作成日 {date}〜"));
        }
        if let Some(date) = valid_date(&self.created_to) {
            conditions.push(format!("作成日 〜{date}"));
        }
        if let Some(minutes) = max_minutes(&self.max_minutes) {
            conditions.push(format!("{minutes}分以内"));
        }
        conditions
    }
}

pub fn search_articles<'a>(index: &'a ArticleIndex, query: &SearchQuery) -> Vec<&'a Article> {
    let keyword = normalize(&query.keyword);
    let genre = limited(query.genre.trim());
    let technology = limited(query.technology.trim());
    let source = limited(query.source.trim());
    let created_from = valid_date(&query.created_from);
    let created_to = valid_date(&query.created_to);
    let max_minutes = max_minutes(&query.max_minutes);

    let mut matches = index
        .articles
        .iter()
        .filter(|article| {
            (keyword.is_empty() || normalize(&searchable_text(article)).contains(&keyword))
                && (genre.is_empty() || article.genre == genre)
                && (technology.is_empty()
                    || article
                        .technologies
                        .iter()
                        .any(|candidate| candidate == &technology))
                && (source.is_empty() || article.source == source)
                && created_from.is_none_or(|date| article.created_at.as_str() >= date)
                && created_to.is_none_or(|date| article.created_at.as_str() <= date)
                && max_minutes.is_none_or(|minutes| article.reading_minutes <= minutes)
        })
        .collect::<Vec<_>>();

    matches.sort_by(|left, right| compare_articles(left, right, &query.sort));
    matches
}

fn limited(value: &str) -> String {
    value.chars().take(MAX_QUERY_CHARS).collect()
}

fn normalize(value: &str) -> String {
    limited(value.trim())
        .nfkc()
        .flat_map(char::to_lowercase)
        .collect()
}

fn searchable_text(article: &Article) -> String {
    format!(
        "{} {} {} {} {}",
        article.title,
        article.summary.join(" "),
        article.source,
        article.genre,
        article.technologies.join(" ")
    )
}

fn max_minutes(value: &str) -> Option<u16> {
    match value.parse::<u16>().ok() {
        Some(5 | 10 | 15 | 30) => value.parse().ok(),
        _ => None,
    }
}

fn valid_date(value: &str) -> Option<&str> {
    let bytes = value.as_bytes();
    if bytes.len() != 10
        || bytes[4] != b'-'
        || bytes[7] != b'-'
        || bytes
            .iter()
            .enumerate()
            .any(|(index, byte)| index != 4 && index != 7 && !byte.is_ascii_digit())
    {
        return None;
    }

    let year = value[0..4].parse::<u16>().ok()?;
    let month = value[5..7].parse::<u8>().ok()?;
    let day = value[8..10].parse::<u8>().ok()?;
    let leap_year =
        year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let max_day = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap_year => 29,
        2 => 28,
        _ => return None,
    };

    (day > 0 && day <= max_day).then_some(value)
}

fn compare_articles(left: &Article, right: &Article, sort: &str) -> Ordering {
    match sort {
        "created-desc" => right
            .created_at
            .cmp(&left.created_at)
            .then_with(|| left.id.cmp(&right.id)),
        "title-asc" => left
            .title
            .cmp(&right.title)
            .then_with(|| left.id.cmp(&right.id)),
        _ => right
            .updated_at
            .cmp(&left.updated_at)
            .then_with(|| left.id.cmp(&right.id)),
    }
}

#[cfg(test)]
mod tests {
    use yoyaku::{Article, ArticleFacets, ArticleIndex};

    use super::{SearchQuery, search_articles};

    #[allow(clippy::too_many_arguments)]
    fn article(
        id: &str,
        title: &str,
        source: &str,
        genre: &str,
        technologies: &[&str],
        reading_minutes: u16,
        created_at: &str,
        updated_at: &str,
    ) -> Article {
        Article {
            id: id.to_owned(),
            url: format!("https://example.com/{id}"),
            title: title.to_owned(),
            source: source.to_owned(),
            genre: genre.to_owned(),
            technologies: technologies
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
            reading_minutes,
            created_at: created_at.to_owned(),
            updated_at: updated_at.to_owned(),
            summary: vec![format!("{title}の詳しい要約")],
            ogp: None,
        }
    }

    fn fixture() -> ArticleIndex {
        ArticleIndex {
            generated_at: "2026-08-16T00:00:00Z".to_owned(),
            articles: vec![
                article(
                    "rust-workers",
                    "RustでWorkersを動かす",
                    "Zenn",
                    "Web開発",
                    &["Rust", "WebAssembly"],
                    8,
                    "2026-08-14",
                    "2026-08-16",
                ),
                article(
                    "hono-api",
                    "小さなEdge API",
                    "Qiita",
                    "API設計",
                    &["Hono", "TypeScript"],
                    5,
                    "2026-08-12",
                    "2026-08-15",
                ),
            ],
            facets: ArticleFacets::default(),
        }
    }

    fn ids(articles: Vec<&Article>) -> Vec<&str> {
        articles
            .into_iter()
            .map(|article| article.id.as_str())
            .collect()
    }

    #[test]
    fn default_query_returns_articles_by_latest_update() {
        assert_eq!(
            ids(search_articles(&fixture(), &SearchQuery::default())),
            ["rust-workers", "hono-api"]
        );
    }

    #[test]
    fn normalizes_nfkc_keyword_and_searches_all_text_fields() {
        let query = SearchQuery {
            keyword: " ＲＵＳＴ ".to_owned(),
            ..SearchQuery::default()
        };

        assert_eq!(ids(search_articles(&fixture(), &query)), ["rust-workers"]);
    }

    #[test]
    fn applies_every_filter_as_and_conditions() {
        let query = SearchQuery {
            keyword: "Workers".to_owned(),
            genre: "Web開発".to_owned(),
            technology: "Rust".to_owned(),
            source: "Zenn".to_owned(),
            created_from: "2026-08-14".to_owned(),
            created_to: "2026-08-14".to_owned(),
            max_minutes: "10".to_owned(),
            sort: "created-desc".to_owned(),
        };

        assert_eq!(ids(search_articles(&fixture(), &query)), ["rust-workers"]);
    }

    #[test]
    fn supports_created_date_and_title_sorting() {
        let mut query = SearchQuery {
            sort: "created-desc".to_owned(),
            ..SearchQuery::default()
        };
        assert_eq!(
            ids(search_articles(&fixture(), &query)),
            ["rust-workers", "hono-api"]
        );

        query.sort = "title-asc".to_owned();
        assert_eq!(
            ids(search_articles(&fixture(), &query)),
            ["rust-workers", "hono-api"]
        );
    }

    #[test]
    fn ignores_invalid_dates_minutes_and_sort_values() {
        let query = SearchQuery {
            created_from: "not-a-date".to_owned(),
            created_to: "2026-99-99".to_owned(),
            max_minutes: "forever".to_owned(),
            sort: "unknown".to_owned(),
            ..SearchQuery::default()
        };

        assert_eq!(
            ids(search_articles(&fixture(), &query)),
            ["rust-workers", "hono-api"]
        );
    }
}
