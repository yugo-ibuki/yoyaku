use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};
use yoyaku::{build_index_file, enrich_file_with, fetch_ogp, load_articles, validate_collection};

#[derive(Debug, Parser)]
#[command(name = "yoyaku", version, about = "記事要約データを検証・生成します")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// 記事JSONを検証する
    Validate {
        #[arg(long, default_value = "content/articles")]
        content_dir: PathBuf,
    },
    /// 配信用の記事索引を生成する
    Build {
        #[arg(long, default_value = "content/articles")]
        content_dir: PathBuf,
        #[arg(long, default_value = "public/data/articles.json")]
        output: PathBuf,
    },
    /// URLからOGPを取得して記事JSONへ保存する
    Enrich { file: PathBuf },
}

fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Validate { content_dir } => {
            let articles = load_articles(&content_dir)?;
            validate_collection(&articles)?;
            println!("{}件の記事を検証しました", articles.len());
        }
        Command::Build {
            content_dir,
            output,
        } => {
            let count = build_index_file(&content_dir, &output)?;
            println!("{}件の記事から{}を生成しました", count, output.display());
        }
        Command::Enrich { file } => {
            let article = enrich_file_with(&file, fetch_ogp)?;
            println!("{}のOGPを更新しました", article.id);
        }
    }
    Ok(())
}

fn main() -> Result<()> {
    run(Cli::parse())
}
