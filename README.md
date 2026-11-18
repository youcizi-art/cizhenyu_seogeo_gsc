# seogeo-gsc（Google Search Console MCP）

真实查询词、点击、展现、排名、sitemap。凭据由磁帧鱼 Deploy 注入。

## 推荐配置（Deploy 一键沿用 Ads）

1. 先完成 **Google Ads** 向导（同一 Cloud 项目 / gcloud / OAuth / ADC）  
2. 在 Search Console 用同一账号验证站点  
3. 打开 Deploy → GSC 凭证 → **一键沿用 Ads 配置**  
   - 自动：`gcloud services enable searchconsole.googleapis.com`  
   - 自动：凭证指向共用 `credentials/google/ads_adc.json`  
4. 若提示缺权限：点 **补授权**（浏览器）→ **检测结果**  
5. 安装启用 GSC 后调用 `gsc_sites` 验证  

Ads 新授权已预含 `webmasters.readonly`，多数情况无需再手动开 API 或填路径。

备用文档：

- [Search Console](https://search.google.com/search-console)  
- [Search Console API](https://developers.google.com/webmaster-tools/v1/how-tos/getting-started)  
- [手动启用 API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)

## 凭据读取优先级

1. `GOOGLE_APPLICATION_CREDENTIALS`（Deploy 注入，通常为 ads_adc 共用路径）  
2. `CIZHENYU_AUTH_DIR` 下 `google/gsc_adc.json` / `gsc_adc.json`  
3. vault `google/gsc.json` 的 `credentialsPath`  
4. `%APPDATA%\gcloud\application_default_credentials.json`

## CLI

```powershell
python server.py gsc_sites
python server.py gsc_top_queries --json "{\"site_url\":\"sc-domain:example.com\",\"days\":28}"
```

`site_url` 与 GSC 属性一致：`sc-domain:example.com` 或 `https://example.com/`。
