// Topcoat 0.5 shards expose each reactive signal as a typed argument.
#![allow(clippy::too_many_arguments)]

use topcoat::{
    Result,
    context::{Cx, app_context},
    router::page,
    runtime::{Event, shard},
    view::view,
};
use yoyaku::{Article, ArticleIndex};

use crate::{
    config::{HEADER_TITLE, SiteConfig, TITLE},
    search::{SearchQuery, search_articles},
};

#[page("/")]
pub async fn home(cx: &Cx) -> Result {
    render_home(
        cx,
        app_context::<ArticleIndex>(cx),
        app_context::<SiteConfig>(cx),
    )
    .await
}

async fn render_home(cx: &Cx, index: &ArticleIndex, config: &SiteConfig) -> Result {
    let total = index.articles.len();
    view! {
        cx =>
        <!DOCTYPE html>
        <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="description" content="Gitで管理する記事要約アーカイブ">
                <title>(TITLE)</title>
                <link rel="stylesheet" href="/assets/style.css?v=2">
                topcoat::runtime::script()
            </head>
            <body>
                signal keyword = String::new();
                signal genre = String::new();
                signal technology = String::new();
                signal source = String::new();
                signal created_from = String::new();
                signal created_to = String::new();
                signal max_minutes = String::new();
                signal sort = String::from("updated-desc");

                <div class="app-shell">
                    <header class="site-header">
                        <div class="site-name">(HEADER_TITLE)</div>
                        <div class="header-meta">
                            <span data-total-count="">(format!("収録 {total}件"))</span>
                            if let Some(repository_url) = config.repository_url() {
                                <a href=(repository_url) target="_blank" rel="noopener noreferrer">
                                    "GitHub リポジトリ ↗"
                                </a>
                            }
                        </div>
                    </header>

                    <section class="lead"><h1>(TITLE)</h1></section>

                    <div class="layout">
                        <aside class="sidebar" aria-label="記事検索">
                            <div class="sidebar-heading">
                                <strong>"記事を探す"</strong>
                                <span data-filter-count="">(format!("{total}件"))</span>
                            </div>
                            <form id="search-form">
                                <label class="search-box">
                                    <span aria-hidden="true">"⌕"</span>
                                    <input
                                        id="keyword"
                                        name="keyword"
                                        type="search"
                                        placeholder="キーワードを入力"
                                        autocomplete="off"
                                        :value=$(keyword.get())
                                        @input=$(|event: Event| keyword.set(event.target.value))
                                    >
                                </label>

                                <label class="field">"ジャンル"
                                    <select
                                        id="genre"
                                        name="genre"
                                        :value=$(genre.get())
                                        @change=$(|event: Event| genre.set(event.target.value))
                                    >
                                        <option value="">"すべて"</option>
                                        for value in &index.facets.genres {
                                            <option value=(value.as_str())>(value.as_str())</option>
                                        }
                                    </select>
                                </label>
                                <label class="field">"使用技術"
                                    <select
                                        id="technology"
                                        name="technology"
                                        :value=$(technology.get())
                                        @change=$(|event: Event| technology.set(event.target.value))
                                    >
                                        <option value="">"すべて"</option>
                                        for value in &index.facets.technologies {
                                            <option value=(value.as_str())>(value.as_str())</option>
                                        }
                                    </select>
                                </label>
                                <label class="field">"掲載元"
                                    <select
                                        id="source"
                                        name="source"
                                        :value=$(source.get())
                                        @change=$(|event: Event| source.set(event.target.value))
                                    >
                                        <option value="">"すべて"</option>
                                        for value in &index.facets.sources {
                                            <option value=(value.as_str())>(value.as_str())</option>
                                        }
                                    </select>
                                </label>

                                <fieldset class="date-field">
                                    <legend>"作成日"</legend>
                                    <div class="date-range">
                                        <input
                                            id="created-from"
                                            name="createdFrom"
                                            type="date"
                                            aria-label="作成日の開始"
                                            :value=$(created_from.get())
                                            @change=$(|event: Event| created_from.set(event.target.value))
                                        >
                                        <span>"—"</span>
                                        <input
                                            id="created-to"
                                            name="createdTo"
                                            type="date"
                                            aria-label="作成日の終了"
                                            :value=$(created_to.get())
                                            @change=$(|event: Event| created_to.set(event.target.value))
                                        >
                                    </div>
                                </fieldset>

                                <label class="field">"読了時間"
                                    <select
                                        id="max-minutes"
                                        name="maxMinutes"
                                        :value=$(max_minutes.get())
                                        @change=$(|event: Event| max_minutes.set(event.target.value))
                                    >
                                        <option value="">"指定なし"</option>
                                        <option value="5">"5分以内"</option>
                                        <option value="10">"10分以内"</option>
                                        <option value="15">"15分以内"</option>
                                        <option value="30">"30分以内"</option>
                                    </select>
                                </label>

                                <button
                                    class="reset-button"
                                    type="button"
                                    @click=$(|_event: Event| {
                                        keyword.set("".to_owned());
                                        genre.set("".to_owned());
                                        technology.set("".to_owned());
                                        source.set("".to_owned());
                                        created_from.set("".to_owned());
                                        created_to.set("".to_owned());
                                        max_minutes.set("".to_owned());
                                        sort.set("updated-desc".to_owned());
                                    })
                                >
                                    "条件をすべて解除"
                                </button>
                            </form>
                        </aside>

                        <main class="content">
                            <div class="content-heading">
                                <h2>"該当する記事"</h2>
                                <label class="sort-field">
                                    <span class="sr-only">"並び順"</span>
                                    <select
                                        id="sort"
                                        name="sort"
                                        :value=$(sort.get())
                                        @change=$(|event: Event| sort.set(event.target.value))
                                    >
                                        <option value="updated-desc">"更新日の新しい順"</option>
                                        <option value="created-desc">"作成日の新しい順"</option>
                                        <option value="title-asc">"タイトル順"</option>
                                    </select>
                                </label>
                            </div>
                            article_results(
                                keyword: $(keyword.get()),
                                genre: $(genre.get()),
                                technology: $(technology.get()),
                                source: $(source.get()),
                                created_from: $(created_from.get()),
                                created_to: $(created_to.get()),
                                max_minutes: $(max_minutes.get()),
                                sort: $(sort.get()),
                            )
                        </main>
                    </div>
                </div>
            </body>
        </html>
    }
}

#[shard]
pub(crate) async fn article_results(
    cx: &Cx,
    keyword: String,
    genre: String,
    technology: String,
    source: String,
    created_from: String,
    created_to: String,
    max_minutes: String,
    sort: String,
) -> Result {
    let index = app_context::<ArticleIndex>(cx);
    let query = SearchQuery {
        keyword,
        genre,
        technology,
        source,
        created_from,
        created_to,
        max_minutes,
        sort,
    };
    let articles = search_articles(index, &query);
    let matched = articles.len();
    let total = index.articles.len();
    let conditions = query.active_conditions();
    let notice = if total == 0 {
        Some("記事がまだありません。")
    } else if matched == 0 {
        Some("条件に合う記事がありません。")
    } else {
        None
    };

    view! {
        <div class="result-status">
            <span data-result-count="">(format!("{matched} / {total}件"))</span>
        </div>
        <div class="active-conditions result-conditions" aria-live="polite">
            for condition in conditions {
                <span>(condition)</span>
            }
        </div>
        if let Some(message) = notice {
            <div class="notice" role="status">(message)</div>
        }
        <div class="article-grid" data-article-grid="">
            for article in &articles {
                article_item(article: article)
            }
        </div>
        for article in articles {
            article_dialog(article: article)
        }
    }
}

#[topcoat::view::component]
async fn article_item(article: &Article) -> Result {
    let modal_id = format!("article-{}", article.id);
    let aria_label = format!("{}の要約を開く", article.title);
    let created_at = article.created_at.as_str();
    let updated_at = article.updated_at.as_str();

    view! {
        <article class="article-item">
            <a class="article-card" href=(format!("#{modal_id}")) aria-label=(aria_label)>
                <div class="visual">
                    <div class="visual-fallback">
                        <span class="visual-source">(article.source.as_str())</span>
                        <strong class="visual-title">
                            (article.ogp.as_ref().and_then(|ogp| ogp.title.as_deref()).unwrap_or(&article.title))
                        </strong>
                        <span class="visual-tech">
                            (article.technologies.iter().take(3).cloned().collect::<Vec<_>>().join("　/　"))
                        </span>
                    </div>
                    if let Some(image_url) = article.ogp.as_ref().and_then(|ogp| ogp.image_url.as_deref()) {
                        <img class="visual-image" src=(image_url) alt="" loading="lazy">
                    }
                </div>
                <div class="card-meta">
                    <span class="card-genre">(article.genre.as_str())</span>
                    <span>(format!("読了 {}分", article.reading_minutes))</span>
                </div>
                <h3 class="title">(article.title.as_str())</h3>
                <p class="card-summary">(article.summary.first().map_or("", String::as_str))</p>
                <div class="tags">
                    for value in &article.technologies {
                        <span>(value.as_str())</span>
                    }
                </div>
                <div class="dates">
                    <span>(format!("作成 {}", format_date(created_at)))</span>
                    <span>(format!("更新 {}", format_date(updated_at)))</span>
                </div>
            </a>
        </article>
    }
}

#[topcoat::view::component]
async fn article_dialog(article: &Article) -> Result {
    let modal_id = format!("article-{}", article.id);
    let title_id = format!("{modal_id}-title");

    view! {
        <div class="article-dialog" id=(modal_id)>
            <a class="dialog-backdrop" href="#" aria-label="要約を閉じる"></a>
            <section class="dialog-panel" role="dialog" aria-modal="true" aria-labelledby=(title_id.as_str())>
                <div class="dialog-heading">
                    <span>"記事の要約"</span>
                    <a href="#" class="dialog-close" aria-label="閉じる">"×"</a>
                </div>
                <div class="dialog-body">
                    <div class="dialog-meta">
                        <span>(article.genre.as_str())</span>
                        <span>(format!("読了 {}分", article.reading_minutes))</span>
                        <span>(article.source.as_str())</span>
                    </div>
                    <h2 class="dialog-title" id=(title_id)>(article.title.as_str())</h2>
                    <div class="dialog-tags">
                        for value in &article.technologies {
                            <span>(value.as_str())</span>
                        }
                    </div>
                    <div class="dialog-source-row">
                        <div class="dialog-dates">
                            <span>(format!("作成 {}", format_date(&article.created_at)))</span>
                            <span>(format!("更新 {}", format_date(&article.updated_at)))</span>
                        </div>
                        <a class="source-link" href=(article.url.as_str()) target="_blank" rel="noopener noreferrer">
                            "元記事を開く ↗"
                        </a>
                    </div>
                    <h3 class="summary-label">"要約"</h3>
                    <div class="dialog-summary">
                        for (index, paragraph) in article.summary.iter().enumerate() {
                            <p if index >= 2 { class="dialog-summary-line" }>(paragraph.as_str())</p>
                        }
                    </div>
                </div>
            </section>
        </div>
    }
}

fn format_date(date: &str) -> String {
    date.replace('-', ".")
}
