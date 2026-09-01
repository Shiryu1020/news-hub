# news-hub

自分専用のニュース集約サイト。複数のAPIから情報を集めて1ページに表示する。

## 仕組み

- `sources/` : 1API = 1ファイルのプラグイン形式。`fetch(config) -> list[Item]` を実装するだけで新しいソースを追加できる
- `sources.yaml` : どのソースを有効にするか、APIキーなどのパラメータを管理
- `build.py` : 全ソースを取得 → `data/items.json` に正規化データを出力 → `templates/index.html.j2` から `docs/index.html` を生成
- `.github/workflows/deploy.yml` : 毎日自動でビルドし、GitHub Pages にデプロイ(無料)

## セットアップ(初回のみ)

```bash
pip install -r requirements.txt
python build.py       # docs/index.html が生成される
```

ブラウザで `docs/index.html` を開けばローカルでプレビューできる。

## 新しいソースの追加方法

1. `sources/<name>.py` を作成し、以下を実装する

   ```python
   from .base import Item

   def fetch(config: dict) -> list[Item]:
       ...
       return [Item(source="<name>", title=..., url=..., published_at=...)]
   ```

2. `sources.yaml` に登録する

   ```yaml
   sources:
     <name>:
       enabled: true
       module: sources.<name>
   ```

3. `python build.py` で確認

定量データは `Item.metrics` (dict)、定性的な補足情報(関連ニュースなど)は `Item.related_links` に入れる。

## GitHub Pages への公開手順(初回のみ)

1. GitHub に public リポジトリを作成し、このフォルダをpush
2. リポジトリの Settings → Pages → Source を「GitHub Actions」に設定
3. Actions タブで `Build and Deploy News Hub` を一度手動実行(workflow_dispatch)
4. 以降は毎日07:00 JSTに自動更新される

## 現在実装済みのソース

- NASA APOD (今日の天体写真) : DEMO_KEYで動作。本格運用時は api.nasa.gov で無料キー取得推奨
- 株価 (日経平均・S&P500) : yfinanceで価格・前日比を取得し、Google News RSSの関連見出しをGemini API(無料枠)で「なぜ動いたか」の2〜3文サマリに要約

## AI要約(Gemini)のセットアップ

1. https://aistudio.google.com/apikey で無料APIキーを発行(Googleアカウントのみ、クレジットカード不要)
2. ローカルで試す場合は環境変数 `GEMINI_API_KEY` にセットして `python build.py`
3. GitHub Actionsで動かす場合は、リポジトリの Settings → Secrets and variables → Actions で `GEMINI_API_KEY` を登録

`GEMINI_API_KEY` が無い場合は自動的に「関連見出しをそのまま使う」フォールバックになる(エラーにはならない)。

## 今後追加予定

- 警察・防犯情報
- 不動産取引価格情報(国土交通省 不動産情報ライブラリAPI)
