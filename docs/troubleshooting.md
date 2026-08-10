# トラブルシューティング

## 詳細ログを有効にする

```bash
python web_api.py --debug-all
```

Windowsでは`start_web.bat`起動時の「Show all logs?」に`y`と答える方法もあります。
`api_key_configured=true`は設定の有無だけを表し、APIキー本体はログへ出力されません。

## Web UIの設定と実ゲームのモデルが違う

環境変数はWeb UIの保存値より優先される場合があります。たとえば
`LLAMA_CPP_MODEL=local-model`が残っていると、Web UIでGeminiを保存しても実ゲームでは
`local-model`が使われる場合があります。

```powershell
Get-ChildItem Env: |
  Where-Object Name -Match 'LLAMA_CPP|LLM_|OPENAI_|TABLE_TURN'
```

個別確認:

```powershell
Get-ChildItem Env:LLAMA_CPP_MODEL,Env:LLM_MODEL,Env:OPENAI_MODEL `
  -ErrorAction SilentlyContinue
```

次の3つのモデル名も比較します。

```text
[BANTER_CONFIG] model=...
[TABLE_TURN_CONFIG] model=...
[TABLE_TURN_BODY] model=...
```

## 接続テストは成功するが実ゲームだけ404になる

`TABLE_TURN_CONFIG`と`TABLE_TURN_BODY`を確認します。

```text
[TABLE_TURN_CONFIG]
model=local-model

[TABLE_TURN_STATUS] 404 Not Found
```

Gemini利用時の期待値は`model=gemini-3.5-flash`です。モデル関連の環境変数が残っていないか
確認してください。

## 現在のPowerShellから上書きを解除する

ほかの用途で必要ないことを確認し、対象だけを削除します。

```powershell
Remove-Item Env:LLAMA_CPP_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:OPENAI_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:TABLE_TURN_MAX_TOKENS -ErrorAction SilentlyContinue
python web_api.py --debug-all
```

環境変数を削除したものと同じPowerShellからWeb APIを再起動してください。

新しいPowerShellで値が復活する場合は、ユーザーまたはシステム環境変数を確認します。

```powershell
[Environment]::GetEnvironmentVariable("LLAMA_CPP_MODEL", "User")
[Environment]::SetEnvironmentVariable("LLAMA_CPP_MODEL", $null, "User")
```

システム環境変数の変更には管理者権限が必要になる場合があります。

## 仲間の台詞が途中で切れる

次のログを確認します。

```text
[TABLE_TURN_TRUNCATED]
finish_reason=length
max_tokens=2048
```

`finish_reason=length`の場合、台詞が途中で切れたり、指定した仲間全員が発言できなかったりします。
`TABLE_TURN_MAX_TOKENS`が小さい値で上書きされていないか確認してください。

```powershell
Get-ChildItem Env:TABLE_TURN_MAX_TOKENS -ErrorAction SilentlyContinue
```

## 接続ログの期待例

```text
[BANTER_CONFIG]
provider=openai_compatible
model=gemini-3.5-flash
api_key_configured=true
[BANTER_STATUS] 200 OK

[EMB_CONFIG]
model=gemini-embedding-2
api_key_configured=true
[EMB_STATUS] 200 OK

[TABLE_TURN_CONFIG]
provider=openai_compatible
model=gemini-3.5-flash
api_key_configured=true
[TABLE_TURN_STATUS] 200 OK
```

仲間4名を明示したターンでは、次のような分類結果も確認できます。

```text
Table turn speaker classification:
gm=1 companion=4 npc=0 dropped=[]
```
