use topcoat::router::Body as TopcoatBody;
use worker::{Context, Env, HttpRequest, event};

use crate::{REPOSITORY_URL_ENV, SiteConfig};

#[event(fetch)]
async fn fetch(
    request: HttpRequest,
    env: Env,
    _ctx: Context,
) -> worker::Result<topcoat::router::Response> {
    let index = serde_json::from_str(crate::ARTICLE_INDEX).map_err(|error| {
        worker::Error::RustError(format!("invalid embedded article index: {error}"))
    })?;
    let repository_url = env
        .var(REPOSITORY_URL_ENV)
        .ok()
        .map(|value| value.to_string());
    let router = crate::router_with_config(index, SiteConfig::new(repository_url));
    Ok(router.handle(request.map(TopcoatBody::new)).await)
}
