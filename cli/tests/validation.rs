use yoyaku::{Article, Ogp, build_index, validate_article, validate_collection};

fn fixture(id: &str, url: &str) -> Article {
    Article {
        id: id.to_owned(),
        url: url.to_owned(),
        title: "記事タイトル".to_owned(),
        source: "Zenn".to_owned(),
        genre: "Web開発".to_owned(),
        technologies: vec!["Rust".to_owned()],
        reading_minutes: 8,
        created_at: "2026-08-14".to_owned(),
        updated_at: "2026-08-15".to_owned(),
        summary: vec!["記事の要約".to_owned()],
        ogp: Some(Ogp::default()),
    }
}

#[test]
fn accepts_a_valid_article() {
    assert!(validate_article(&fixture("article-a", "https://example.com/a")).is_ok());
}

#[test]
fn rejects_an_updated_date_before_created_date() {
    let mut article = fixture("article-a", "https://example.com/a");
    article.updated_at = "2026-08-13".to_owned();

    let error = validate_article(&article).unwrap_err();

    assert!(error.to_string().contains("updated_at"));
}

#[test]
fn rejects_duplicate_ids_and_urls() {
    let article = fixture("article-a", "https://example.com/a");

    let error = validate_collection(&[article.clone(), article]).unwrap_err();

    assert!(error.to_string().contains("重複"));
}

#[test]
fn builds_sorted_articles_and_unique_facets() {
    let older = fixture("older", "https://example.com/older");
    let mut newer = fixture("newer", "https://example.com/newer");
    newer.updated_at = "2026-08-16".to_owned();
    newer.genre = "API設計".to_owned();
    newer.technologies = vec!["Hono".to_owned(), "Rust".to_owned()];

    let index = build_index(vec![older, newer]);

    assert_eq!(index.articles[0].id, "newer");
    assert_eq!(index.facets.genres, vec!["API設計", "Web開発"]);
    assert_eq!(index.facets.technologies, vec!["Hono", "Rust"]);
    assert_eq!(index.facets.sources, vec!["Zenn"]);
}
