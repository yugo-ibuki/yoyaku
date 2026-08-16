use std::collections::BTreeSet;

use crate::{Article, ArticleFacets, ArticleIndex};

pub fn build_index(mut articles: Vec<Article>) -> ArticleIndex {
    articles.sort_by(|left, right| {
        right
            .updated_at
            .cmp(&left.updated_at)
            .then_with(|| left.id.cmp(&right.id))
    });

    let generated_at = articles
        .iter()
        .map(|article| article.updated_at.as_str())
        .max()
        .map_or_else(
            || "1970-01-01T00:00:00Z".to_owned(),
            |date| format!("{date}T00:00:00Z"),
        );
    let genres = articles
        .iter()
        .map(|article| article.genre.clone())
        .collect::<BTreeSet<_>>();
    let sources = articles
        .iter()
        .map(|article| article.source.clone())
        .collect::<BTreeSet<_>>();
    let technologies = articles
        .iter()
        .flat_map(|article| article.technologies.iter().cloned())
        .collect::<BTreeSet<_>>();

    ArticleIndex {
        generated_at,
        articles,
        facets: ArticleFacets {
            genres: genres.into_iter().collect(),
            technologies: technologies.into_iter().collect(),
            sources: sources.into_iter().collect(),
        },
    }
}
