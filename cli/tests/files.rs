use std::fs;

use tempfile::tempdir;
use yoyaku::{Article, Ogp, build_index_file, enrich_file_with, load_articles};

fn fixture() -> Article {
    Article {
        id: "article-a".to_owned(),
        url: "https://example.com/a".to_owned(),
        title: "記事タイトル".to_owned(),
        source: "Zenn".to_owned(),
        genre: "Web開発".to_owned(),
        technologies: vec!["Rust".to_owned()],
        reading_minutes: 8,
        created_at: "2026-08-14".to_owned(),
        updated_at: "2026-08-15".to_owned(),
        summary: vec!["元の要約".to_owned()],
        ogp: None,
    }
}

#[test]
fn loads_json_files_and_writes_a_valid_index() {
    let temporary = tempdir().unwrap();
    let content = temporary.path().join("content");
    let output = temporary.path().join("public/data/articles.json");
    fs::create_dir_all(&content).unwrap();
    fs::write(
        content.join("article.json"),
        serde_json::to_vec_pretty(&fixture()).unwrap(),
    )
    .unwrap();

    let articles = load_articles(&content).unwrap();
    let count = build_index_file(&content, &output).unwrap();
    let index: serde_json::Value = serde_json::from_slice(&fs::read(output).unwrap()).unwrap();

    assert_eq!(articles.len(), 1);
    assert_eq!(count, 1);
    assert_eq!(index["articles"][0]["id"], "article-a");
}

#[test]
fn enriches_only_the_ogp_field() {
    let temporary = tempdir().unwrap();
    let path = temporary.path().join("article.json");
    fs::write(&path, serde_json::to_vec_pretty(&fixture()).unwrap()).unwrap();

    let enriched = enrich_file_with(&path, |_| {
        Ok(Ogp {
            image_url: Some("https://example.com/og.png".to_owned()),
            title: Some("OGPタイトル".to_owned()),
            description: None,
        })
    })
    .unwrap();
    let saved: Article = serde_json::from_slice(&fs::read(path).unwrap()).unwrap();

    assert_eq!(enriched.summary, vec!["元の要約"]);
    assert_eq!(saved.ogp.unwrap().title.as_deref(), Some("OGPタイトル"));
}
