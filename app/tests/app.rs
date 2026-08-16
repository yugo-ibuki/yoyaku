use topcoat::router::{Body, Request, to_bytes};
use yoyaku::{Article, ArticleFacets, ArticleIndex, Ogp};
use yoyaku_app::{SiteConfig, router, router_with_config, router_with_index};

fn fixture_index() -> ArticleIndex {
    ArticleIndex {
        generated_at: "2026-08-16T00:00:00Z".to_owned(),
        articles: vec![Article {
            id: "rust-workers".to_owned(),
            url: "https://example.com/rust".to_owned(),
            title: "Cloudflare WorkersでRustを動かす".to_owned(),
            source: "Zenn".to_owned(),
            genre: "Web開発".to_owned(),
            technologies: vec!["Rust".to_owned(), "WebAssembly".to_owned()],
            reading_minutes: 8,
            created_at: "2026-08-14".to_owned(),
            updated_at: "2026-08-15".to_owned(),
            summary: vec!["概要です。".to_owned(), "詳しい説明です。".to_owned()],
            ogp: Some(Ogp {
                image_url: Some("https://example.com/og.png".to_owned()),
                ..Ogp::default()
            }),
        }],
        facets: ArticleFacets {
            genres: vec!["Web開発".to_owned()],
            technologies: vec!["Rust".to_owned(), "WebAssembly".to_owned()],
            sources: vec!["Zenn".to_owned()],
        },
    }
}

#[tokio::test]
async fn renders_the_article_archive_with_topcoat_runtime() {
    let response = router_with_index(fixture_index())
        .handle(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await;
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();

    assert!(html.starts_with("<!DOCTYPE html>"), "{html}");
    assert!(html.contains("Yoyaku"), "{html}");
    assert!(html.contains("article-grid"), "{html}");
    assert!(html.contains("Cloudflare WorkersでRustを動かす"), "{html}");
    assert!(html.contains("詳しい説明です。"), "{html}");
    assert!(html.contains("id=\"search-form\""), "{html}");
    assert!(html.contains("/assets/topcoat-runtime.js"), "{html}");
    assert!(html.contains("/assets/style.css?v=2"), "{html}");
    assert!(html.contains("::topcoat::scope::start"), "{html}");
    assert!(html.contains("href=\"#article-rust-workers\""), "{html}");
    assert!(html.contains("role=\"dialog\""), "{html}");
    assert!(!html.contains("/assets/main.js"), "{html}");
    assert!(!html.contains("data-search="), "{html}");
    assert!(!html.contains("<template"), "{html}");
}

#[tokio::test]
async fn topcoat_router_serves_the_home_page() {
    let response = router_with_index(fixture_index())
        .handle(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await;
    let status = response.status();
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();

    assert_eq!(status, 200);
    assert!(html.contains("Yoyaku"), "{html}");
}

#[tokio::test]
async fn repository_link_comes_from_site_config() {
    let response = router_with_config(
        fixture_index(),
        SiteConfig::new(Some("https://github.com/example/yoyaku".to_owned())),
    )
    .handle(Request::builder().uri("/").body(Body::empty()).unwrap())
    .await;
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();

    assert!(html.contains("https://github.com/example/yoyaku"), "{html}");

    let response = router_with_index(fixture_index())
        .handle(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await;
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let html = String::from_utf8(body.to_vec()).unwrap();

    assert!(!html.contains("GitHub リポジトリ"), "{html}");
}

async fn get(path: &str) -> (http::StatusCode, http::HeaderMap, String) {
    let response = router_with_index(fixture_index())
        .handle(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await;
    let status = response.status();
    let headers = response.headers().clone();
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    (status, headers, String::from_utf8(body.to_vec()).unwrap())
}

#[tokio::test]
async fn serves_health_and_article_json() {
    let (health_status, health_headers, health_body) = get("/api/health").await;
    let (articles_status, articles_headers, articles_body) = get("/api/articles").await;

    assert_eq!(health_status, 200);
    assert_eq!(
        health_headers.get("content-type").unwrap(),
        "application/json; charset=utf-8"
    );
    assert_eq!(health_body, r#"{"ok":true}"#);
    assert_eq!(articles_status, 200);
    assert_eq!(
        articles_headers.get("cache-control").unwrap(),
        "public, max-age=300"
    );
    assert!(articles_body.contains("rust-workers"), "{articles_body}");
}

#[tokio::test]
async fn serves_browser_assets_with_explicit_content_types() {
    let (css_status, css_headers, css_body) = get("/assets/style.css").await;
    let (runtime_status, runtime_headers, runtime_body) = get("/assets/topcoat-runtime.js").await;
    let (main_status, _, _) = get("/assets/main.js").await;
    let (filter_status, _, _) = get("/assets/filter.js").await;

    assert_eq!(css_status, 200);
    assert_eq!(
        css_headers.get("content-type").unwrap(),
        "text/css; charset=utf-8"
    );
    assert_eq!(css_headers.get("cache-control").unwrap(), "no-cache");
    assert!(css_body.contains(".article-grid"), "{css_body}");
    assert_eq!(runtime_status, 200);
    assert_eq!(
        runtime_headers.get("content-type").unwrap(),
        "text/javascript; charset=utf-8"
    );
    assert!(runtime_body.contains("data-topcoat-bind"), "{runtime_body}");
    assert_eq!(main_status, 404);
    assert_eq!(filter_status, 404);
}

#[tokio::test]
async fn embedded_article_index_builds_the_production_router() {
    let response = router()
        .unwrap()
        .handle(
            Request::builder()
                .uri("/api/articles")
                .body(Body::empty())
                .unwrap(),
        )
        .await;
    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(json["articles"].is_array());
    assert!(json["facets"]["genres"].is_array());
}
