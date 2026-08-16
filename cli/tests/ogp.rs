use url::Url;
use yoyaku::parse_ogp;

#[test]
fn parses_property_and_name_metadata_and_resolves_relative_images() {
    let html = r#"
        <html><head>
          <meta property="og:title" content="記事タイトル">
          <meta name="description" content="通常の説明">
          <meta property="og:description" content="OGPの説明">
          <meta property="og:image" content="/images/og.png">
        </head></html>
    "#;
    let base = Url::parse("https://example.com/articles/post").unwrap();

    let ogp = parse_ogp(html, &base).unwrap();

    assert_eq!(ogp.title.as_deref(), Some("記事タイトル"));
    assert_eq!(ogp.description.as_deref(), Some("OGPの説明"));
    assert_eq!(
        ogp.image_url.as_deref(),
        Some("https://example.com/images/og.png")
    );
}

#[test]
fn falls_back_to_title_and_description_metadata() {
    let html = r#"<html><head><title>HTMLタイトル</title><meta name="description" content="説明"></head></html>"#;
    let base = Url::parse("https://example.com/post").unwrap();

    let ogp = parse_ogp(html, &base).unwrap();

    assert_eq!(ogp.title.as_deref(), Some("HTMLタイトル"));
    assert_eq!(ogp.description.as_deref(), Some("説明"));
    assert_eq!(ogp.image_url, None);
}

#[test]
fn ignores_non_http_image_urls() {
    let html = r#"<meta property="og:image" content="javascript:alert(1)">"#;
    let base = Url::parse("https://example.com/post").unwrap();

    let ogp = parse_ogp(html, &base).unwrap();

    assert_eq!(ogp.image_url, None);
}
