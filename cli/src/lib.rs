#[cfg(feature = "cli")]
mod index;
pub mod model;
#[cfg(feature = "cli")]
mod ogp;
#[cfg(feature = "cli")]
mod storage;
#[cfg(feature = "cli")]
mod validate;

#[cfg(feature = "cli")]
pub use index::build_index;
pub use model::{Article, ArticleFacets, ArticleIndex, Ogp};
#[cfg(feature = "cli")]
pub use ogp::{fetch_ogp, parse_ogp};
#[cfg(feature = "cli")]
pub use storage::{build_index_file, enrich_file_with, load_articles};
#[cfg(feature = "cli")]
pub use validate::{validate_article, validate_collection};
