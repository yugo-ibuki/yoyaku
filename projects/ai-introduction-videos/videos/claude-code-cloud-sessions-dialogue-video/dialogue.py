from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Turn:
    id: int
    speaker_id: str
    speaker_label: str
    cards: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(card.replace("|", "") for card in self.cards)


TURNS = (
    Turn(1, "left_student", "生徒", ("先生、ノートパソコンを閉じても、", "Claude Codeが|働き続けるって本当？")),
    Turn(2, "right_teacher", "先生", ("本当です。クラウドセッションは、|手元のパソコンではなく、", "クラウド側の環境で動きます。", "だから、ふたを閉じても|処理は続きます。")),
    Turn(3, "left_student", "生徒", ("料理を注文して、私は出かけても、|厨房では作り続けてくれる感じ？",)),
    Turn(4, "right_teacher", "先生", ("いい例えですね。途中の様子は、", "デスクトップ、ブラウザ、|スマホから確認でき、", "別の端末でも同じセッションを|続けて操作できます。")),
    Turn(5, "left_student", "生徒", ("じゃあ、始める前に|何を用意すればいいんですか？",)),
    Turn(6, "right_teacher", "先生", ("通常は、アクセスできるGitHubの|リポジトリを選び、", "デスクトップなら実行先をローカルから|クラウド環境へ切り替えて指示します。")),
    Turn(7, "left_student", "生徒", ("私のパソコンだけにある設定や、|作りかけのファイルも見えるの？",)),
    Turn(8, "right_teacher", "先生", ("通常はGitHubから|複製して始まるので、", "リポジトリにコミットした|ものを使います。", "手元だけの設定やスクリプトは|自動では入りません。", "ただし、ターミナルから|手元のリポジトリを", "送る経路もあるので、|開始方法は確認しましょう。")),
    Turn(9, "left_student", "生徒", ("クラウドの作業場所は、|自分向けに整えられるんですか？",)),
    Turn(10, "right_teacher", "先生", ("はい。クラウド環境という保存設定で、|ネットワークの範囲、環境変数、", "起動前に走らせる|セットアップスクリプトを", "用途ごとに決められます。")),
    Turn(11, "left_student", "生徒", ("インターネットには、|最初からどこへでも行けるの？",)),
    Turn(12, "right_teacher", "先生", ("初期のTrustedは、|GitHubや", "主なパッケージ配布元などに|絞られます。", "ニュースやブログを調べる仕事なら、|必要な接続先を許可する設定にします。", "必要な行き先だけにすると、", "外部サイトを扱う作業にも|向いています。")),
    Turn(13, "left_student", "生徒", ("見ていない間に動かすなら、|便利なぶん心配もありますね。",)),
    Turn(14, "right_teacher", "先生", ("そうですね。接続先を絞るだけで|作業が正しいとは限りません。", "終わったら会話、変更内容、|テスト結果を見て、", "意図どおりか人が|確かめましょう。")),
    Turn(15, "left_student", "生徒", ("まとめると、パソコンを閉じても動き、|どの端末からでも追いかけられる。", "その代わり、GitHubに置くものと|クラウド環境を先に整えるんですね。")),
    Turn(16, "right_teacher", "先生", ("そのとおり。|クラウドセッションは、", "席を離れても仕事を進められる|仕組みです。", "リポジトリ、接続先、|実行準備をそろえ、", "最後の確認までを|一組で考えましょう。")),
)


def validate_script() -> None:
    expected = list(range(1, 17))
    if [turn.id for turn in TURNS] != expected:
        raise ValueError("turn IDs must be consecutive from 1 to 16")
    if [turn.speaker_id for turn in TURNS] != ["left_student", "right_teacher"] * 8:
        raise ValueError("the 16 turns must alternate left student and right teacher")
    labels = {turn.speaker_label for turn in TURNS}
    if labels != {"生徒", "先生"}:
        raise ValueError(f"unexpected visible labels: {labels}")
    for turn in TURNS:
        if not turn.cards or not turn.text:
            raise ValueError(f"turn {turn.id} is empty")
        for card in turn.cards:
            lines = card.split("|")
            if len(lines) > 2 or any(not line or len(line) > 18 for line in lines):
                raise ValueError(f"turn {turn.id} has a non-caption-safe card: {card}")


validate_script()
