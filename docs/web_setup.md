# Web版セットアップ

## 必要環境

Python 3.10以降を使用します。

```bash
python -m pip install -r requirements-web.txt
```

## 起動方法

### Windowsの通常利用

```bat
start_web.bat
```

`start_web.bat`は依存関係を確認してWeb APIとブラウザを起動するランチャーです。起動時の
「Show all logs?」に`y`と答えると、LLM、Embedding、判定、発言者分類のログを表示します。
llama.cppは自動起動せず、URL、モデル、シナリオ、APIキーも保持・変更しません。

### 端末から起動

```bash
python web_api.py
```

詳細ログを表示する場合:

```bash
python web_api.py --debug-all
```

Uvicornを直接使用する場合:

```bash
python -m uvicorn web_api:app --host 127.0.0.1 --port 8000
```

ブラウザで <http://127.0.0.1:8000> を開きます。`start_web.bat`と`python web_api.py`を同時に
実行する必要はありません。

> [!WARNING]
> 認証、TLS、永続化を備えた外部公開用サーバーではありません。インターネットへ公開しないでください。

## 初回設定

画面上部の「接続設定」で、シナリオ、Chat、Embeddingを確認します。接続テスト、設定保存、
ゲーム開始の順に進みます。

* **Chat Provider:** `llama_cpp`、`openai_compatible`、`none`
* **Chat Base URL:** 既定値は`http://127.0.0.1:8080/v1`
* **Chat Model:** 既定値は`local-model`
* **Embedding Base URL:** 既定値は`http://127.0.0.1:8081/v1`
* **Embedding Model:** 既定値は`local-embedding`
* **API Key:** API提供者が要求する場合のみ入力。ChatとEmbeddingで独立

接続テストは画面の未保存値を使いますが、ゲームセッションや履歴は作成しません。設定変更は
進行中のゲームには適用されず、次に開始するゲームから有効です。

## 保存範囲

一般設定はUTF-8 JSONで次の場所へ保存します。

* Windows: `%LOCALAPPDATA%\ChatTtrpgGm\settings.json`
* その他: `$XDG_CONFIG_HOME/chat-ttrpg-gm/settings.json`または`~/.config/chat-ttrpg-gm/settings.json`

APIキーは設定ファイルへ保存せず、Pythonプロセスのメモリだけに保持します。ゲームセッションも
メモリ内だけにあり、API停止・再起動時に失われます。

## 設定の優先順位

1. CLIの明示引数
2. 環境変数
3. WebからPythonプロセスへ渡したAPIキー
4. `settings.json`
5. Pythonエンジンの既定値

環境変数がWeb UIの保存値を上書きする場合があります。詳しくは
[LLM / Embedding設定](llm_configuration.md)と[トラブルシューティング](troubleshooting.md)を
参照してください。

## Web/APIテスト

macOS/Linux:

```bash
LLM_PROVIDER=none EMBEDDING_PROVIDER=none python -m unittest discover -s tests -p "test*.py"
```

Windows PowerShell:

```powershell
$env:LLM_PROVIDER="none"
$env:EMBEDDING_PROVIDER="none"
python -m unittest discover -s tests -p "test*.py"
```
