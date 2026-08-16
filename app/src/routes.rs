use topcoat::{
    Result,
    context::{Cx, app_context},
    router::{Body, Response, RouterBuilder, route},
};
use yoyaku::ArticleIndex;

const CSS: &str = include_str!("../web/style.css");

fn response(
    content_type: &'static str,
    cache_control: &'static str,
    body: String,
) -> Result<Response> {
    Ok(Response::builder()
        .header("Content-Type", content_type)
        .header("Cache-Control", cache_control)
        .body(Body::from(body))?)
}

#[route(GET "/api/health")]
async fn health() -> Result<Response> {
    response(
        "application/json; charset=utf-8",
        "no-store",
        r#"{"ok":true}"#.to_owned(),
    )
}

#[route(GET "/api/articles")]
async fn articles(cx: &Cx) -> Result<Response> {
    response(
        "application/json; charset=utf-8",
        "public, max-age=300",
        serde_json::to_string(app_context::<ArticleIndex>(cx))?,
    )
}

#[route(GET "/assets/style.css")]
async fn style() -> Result<Response> {
    response("text/css; charset=utf-8", "no-cache", CSS.to_owned())
}

#[route(GET "/assets/topcoat-runtime.js")]
async fn topcoat_runtime() -> Result<Response> {
    response(
        "text/javascript; charset=utf-8",
        "public, max-age=3600",
        crate::runtime_asset::script().to_owned(),
    )
}

pub(crate) fn register(builder: RouterBuilder) -> RouterBuilder {
    builder
        .route(health)
        .route(articles)
        .route(style)
        .route(topcoat_runtime)
}
