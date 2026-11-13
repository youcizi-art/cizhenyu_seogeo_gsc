# seogeo-gsc（Google Search Console MCP）

真实查询词、点击、展现、排名、sitemap。凭据由词真语 Deploy 注入，**禁止把密钥写进代码**。

## 客户配置教程（Deploy）

在 Deploy「凭证 / GSC」按引导操作；完整步骤与官方链接见软件内「配置教程」。摘要如下：

1. [Search Console](https://search.google.com/search-console) 验证站点，授权账号有权限  
2. Cloud 项目启用 [Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)  
3. [创建 OAuth 桌面客户端](https://console.cloud.google.com/apis/credentials)  
4. 用 gcloud 生成 ADC（**必须含** `webmasters.readonly`）：

```powershell
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
```

5. 将 `%APPDATA%\gcloud\application_default_credentials.json` 的**绝对路径**填入 Deploy「ADC JSON 路径」并保存  
6. 安装启用 GSC 后调用 `gsc_sites` 验证  

官方入门：[Search Console API Getting Started](https://developers.google.com/webmaster-tools/v1/how-tos/getting-started)  
ADC 说明：[Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)

## 凭据读取优先级（工具运行时）

1. 进程环境 `GOOGLE_APPLICATION_CREDENTIALS`（Deploy 从 vault 注入）  
2. `CIZHENYU_AUTH_DIR` / `SEOGEO_AUTH_DIR` 下 `google/gsc_adc.json`、`gsc_adc.json`  
3. vault 元数据 `google/gsc.json` 里的 `credentialsPath`  
4. 回退 `%APPDATA%\gcloud\application_default_credentials.json`

ADC 必须是 `type=authorized_user` 且含 `refresh_token`。缺 scope 时报 `403`：删掉旧 ADC 按上面 scopes 重授权。

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

`site_url` 用 GSC 里的原样值：域名属性 `sc-domain:example.com`，URL 前缀 `https://example.com/`。

## MCP

由 Deploy 导出/同步；本地调试时设置 `CIZHENYU_AUTH_DIR` 指向工作目录 `credentials`。
