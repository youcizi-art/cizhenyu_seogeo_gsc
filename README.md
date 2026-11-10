# seogeo-gsc（全局工具）

Google Search Console 的 MCP 服务 + CLI（真实查询词、点击、展现、排名、sitemap）。

## 凭据

默认读机器上的 ADC：`%APPDATA%\gcloud\application_default_credentials.json`。
若 `C:\scripts\seogeo-auth-config\gsc_adc.json` 存在，则优先用它（交付客户时放客户自己的 ADC）。

**必须含 scope `https://www.googleapis.com/auth/webmasters.readonly`。**
第一次用若报 `403 insufficient scope`，执行（会弹浏览器授权）：

```powershell
& 'C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe' `
  'U:\seogeo\workflow\seogeo\scripts\google_ads_auth.py' `
  -c "C:\scripts\seogeo-auth-config\client_secret.json" `
  --scope "https://www.googleapis.com/auth/webmasters.readonly" `
  --manual-start
```

拿到回调 URL 后：

```powershell
... google_ads_auth.py -c "...client_secret.json" --manual-finish "<回调 URL>"
```

> 该授权会同时保留 `adwords` scope，因此 Google Ads 关键词能力不受影响。

## CLI

```powershell
python server.py list
python server.py gsc_sites
python server.py gsc_top_queries  --json "{\"site_url\":\"sc-domain:example.com\",\"days\":28}"
python server.py gsc_top_pages    --json "{\"site_url\":\"sc-domain:example.com\"}"
python server.py gsc_page_queries --json "{\"site_url\":\"sc-domain:example.com\",\"page_url\":\"https://example.com/products/star5\"}"
python server.py gsc_breakdown    --json "{\"site_url\":\"sc-domain:example.com\"}"
python server.py gsc_sitemaps     --json "{\"site_url\":\"sc-domain:example.com\"}"
```

`site_url` 用 GSC 里的原样值：域名属性写 `sc-domain:example.com`，URL 前缀属性写 `https://example.com/`。

## MCP 挂载

```yaml
- id: mcp-seogeo-gsc
  name: "@deepseek-ai/dsh-mcp-client"
  config:
    serverName: seogeo_gsc
    transport: stdio
    command: "C:/Users/Administrator/AppData/Local/Python/pythoncore-3.14-64/python.exe"
    args: ["C:/scripts/seogeo-gsc/server.py"]
    cwd: "C:/scripts/seogeo-gsc"
    failOnStartupError: false
    toolCallTimeoutMs: 120000
```

## 在流程里的位置

- 步骤 1/3：有站客户用 `gsc_top_queries` 拿真实查询词，补 autocomplete 覆盖不到的搜索。
- 步骤 7：效果复盘的主数据源（点击/展现/排名变化）。
- 上线验收：`gsc_sitemaps` + 收录诊断。

## Windows PowerShell 注意

PowerShell 调原生程序会吃掉内层双引号，`--json '{"a":"b"}'` 常失败。三种可靠写法：

```powershell
# 1) 用简单参数（推荐）
python server.py dfs_search_intent --keywords "oem nail lamp,gel nail lamp"

# 2) 用参数文件
python server.py dfs_serp_google --args-file args.json

# 3) 转义内层引号
python server.py dfs_keyword_difficulty --json '{\"keywords\":[\"uv nail lamp\"]}'
```
