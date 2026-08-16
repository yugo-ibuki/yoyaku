use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Default, Deserialize, PartialEq, Eq, Serialize)]
pub struct Ogp {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct Article {
    pub id: String,
    pub url: String,
    pub title: String,
    pub source: String,
    pub genre: String,
    pub technologies: Vec<String>,
    pub reading_minutes: u16,
    pub created_at: String,
    pub updated_at: String,
    pub summary: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ogp: Option<Ogp>,
}

#[derive(Clone, Debug, Default, Deserialize, PartialEq, Eq, Serialize)]
pub struct ArticleFacets {
    pub genres: Vec<String>,
    pub technologies: Vec<String>,
    pub sources: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct ArticleIndex {
    pub generated_at: String,
    pub articles: Vec<Article>,
    pub facets: ArticleFacets,
}
