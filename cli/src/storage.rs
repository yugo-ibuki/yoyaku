use std::{fs, path::Path};

use anyhow::{Context, Result};
use serde::Serialize;
use url::Url;

use crate::{Article, Ogp, build_index, validate_article, validate_collection};

pub fn load_articles(content_dir: &Path) -> Result<Vec<Article>> {
    let mut paths = fs::read_dir(content_dir)
        .with_context(|| format!("記事ディレクトリを開けません: {}", content_dir.display()))?
        .filter_map(|entry| entry.ok().map(|value| value.path()))
        .filter(|path| {
            path.extension()
                .is_some_and(|extension| extension == "json")
        })
        .collect::<Vec<_>>();
    paths.sort();

    paths
        .into_iter()
        .map(|path| {
            let bytes =
                fs::read(&path).with_context(|| format!("記事を読めません: {}", path.display()))?;
            serde_json::from_slice(&bytes)
                .with_context(|| format!("記事JSONが不正です: {}", path.display()))
        })
        .collect()
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("出力先を作成できません: {}", parent.display()))?;
    }
    let bytes = serde_json::to_vec_pretty(value)?;
    let temporary = path.with_extension("json.tmp");
    fs::write(&temporary, [bytes.as_slice(), b"\n"].concat())
        .with_context(|| format!("一時ファイルへ書き込めません: {}", temporary.display()))?;
    fs::rename(&temporary, path)
        .with_context(|| format!("出力を確定できません: {}", path.display()))?;
    Ok(())
}

pub fn build_index_file(content_dir: &Path, output: &Path) -> Result<usize> {
    let articles = load_articles(content_dir)?;
    validate_collection(&articles)?;
    let count = articles.len();
    write_json(output, &build_index(articles))?;
    Ok(count)
}

pub fn enrich_file_with<F>(path: &Path, fetcher: F) -> Result<Article>
where
    F: FnOnce(&Url) -> Result<Ogp>,
{
    let bytes = fs::read(path).with_context(|| format!("記事を読めません: {}", path.display()))?;
    let mut article: Article = serde_json::from_slice(&bytes)
        .with_context(|| format!("記事JSONが不正です: {}", path.display()))?;
    validate_article(&article)?;
    let url = Url::parse(&article.url)?;
    article.ogp = Some(fetcher(&url)?);
    write_json(path, &article)?;
    Ok(article)
}
