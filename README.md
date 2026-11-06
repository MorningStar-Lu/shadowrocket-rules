# Shadowrocket：Apple 智能与日常分流

适用于 Mac、iPhone 和 iPad 的规则配置。更新于 2026-11-07。

[下载配置](https://raw.githubusercontent.com/MorningStar-Lu/shadowrocket-rules/main/personal-apple-ai.conf)

这是规则文件，不提供节点或订阅。导入后继续使用你自己的节点；不要把节点 URI、订阅密钥、二维码、密码或解密证书上传到此仓库。

## 导入与选择

1. Shadowrocket → 配置 → 添加配置链接，粘贴上面的下载地址；也可下载 `.conf` 后从“导入”选择本地文件。
2. 选中 `personal-apple-ai.conf`，选择“使用配置”；首页“全局路由”设为“配置”。
3. 在代理分组中检查 `SiriAI`、`AI` 和 `DNSProxy`。默认选择“新加坡节点”，其成员根据已有节点名称筛选。若该分组为空或连接失败，请手动选择可用的新加坡、美国或日本节点，或切换到 `PROXY` 并在首页选择合适节点。
4. 保持代理连接。Mac 的系统服务也需要经过 Shadowrocket 的 VPN 隧道，仅设置浏览器代理不能保证 Siri 的流量被接管。
5. 第一次导入需要下载 36 个远程规则文件，等待完成后再测试；下载失败时先恢复旧配置排查联网。

## 分流行为

| 服务 | 策略 |
| --- | --- |
| Siri、搜索、Private Cloud Compute、Apple 智能扩展 | `SiriAI`，默认新加坡 |
| ChatGPT、Claude、Gemini、Copilot | `AI`，默认新加坡 |
| GitHub、GitHub 静态资源、linux.do | 代理 |
| Gitee、npm 国内镜像、国内开发镜像 | 直连 |
| 普通 Apple 服务、iCloud、App Store | `苹果服务`，默认直连 |
| 普通 Microsoft 服务 | `微软服务`，默认直连；Copilot 优先进入 AI 分组 |
| 国内影音、Steam 中国 CDN、局域网 | 直连 |
| YouTube、Netflix 等 | 各自独立分组 |
| 未匹配流量 | 代理；中国 IP 兜底直连 |

代理目标使用经 `DNSProxy` 的 Cloudflare HTTPS DNS；直连目标使用系统 DNS；节点地址使用独立的国内 HTTPS DNS 引导解析。代理 DNS 不回退到系统明文 DNS，故该分组必须有可用节点。

兼容仅提供 TCP 转发、IPv4 出口的节点：代理 QUIC 被阻止以便应用回退 TCP，IPv6 解析关闭；不支持的 UDP 被拒绝，不偷偷回退直连。依赖 UDP 的游戏、通话等不保证可用，可单独调整对应服务策略。不同服务是否支持 TCP 回退，需要以实际客户端结果为准。

## Siri / Apple 智能的适用范围

规则只调整联网路径，不能更改设备销售地区、Apple 账户地区、语言、年龄要求、模型下载状态或服务资格，也不承诺解锁功能。

普通 Siri、Siri 接入 ChatGPT、Siri AI Beta 是不同功能。请以“系统设置 → Siri”显示的可用功能和 Apple 当前要求为准；不要为了套用规则直接修改账户地区。

Apple 官方资料：

- [Apple 企业网络主机要求：Siri 与 Private Cloud Compute](https://support.apple.com/en-us/101555)
- [Apple 智能要求及地区限制](https://support.apple.com/en-us/121115)
- [Siri AI 要求](https://support.apple.com/en-us/127893)

## 与旧配置合并时的修正

- 统一流媒体规则引用与实际分组名称，避免 `YOUTUBE` / `YouTube` 等不一致。
- 把 AI 和 Siri 专项规则放在普通 Apple、Microsoft、中国直连规则之前。
- 对 Apple、Global 和 China 同时引用上游配套的 `.list` 与 `_Domain.list`，分别使用 `RULE-SET` 和 `DOMAIN-SET`。
- 合并此前的开发分流与有效静态规则，去重；移除过宽的 `aka` 关键词、旧的单 IP `/32` 代理例外和依赖解密的旧 User-Agent 规则。
- 删除上游整份配置的自动替换地址，避免个人修改被覆盖；远程规则集仍可独立更新。
- 删除 Apple 域名强制使用系统 DNS 的 Hosts 覆盖。
- 不包含 HTTPS 解密、CA、脚本、重写或第三方模块。导入规则无需安装根证书。
- 公开版移除了四条个人站点例外。本地完整版本额外保留这四条规则，两者不含节点凭据。

## Mac 客户端版本

本次 Mac 实测：Shadowrocket 2.2.90 使用同一订阅出现 CONNECT 超时，而 iPhone 可以使用；更新官方客户端至 2.2.93 后恢复，实际出口校验及 HTTP/HTTPS 请求均通过。建议先更新客户端，再排查规则和节点。这个结果不代表所有旧版本都必然故障。

[App Store 官方更新记录](https://apps.apple.com/us/app/shadowrocket/id932747118)包含隧道、测速状态及 iCloud 同步相关修复。本配置无需为兼容旧客户端而关闭证书校验或降级服务器。

## 验证与回退

```sh
python3 validate.py
```

验证器下载所有远程规则文件、检查策略组引用及远程文件格式，并重放 29 个关键域名的首条匹配结果。它不读取节点凭据、不进行解密，也不代表 Siri 已经完成实际请求。

本次静态检查：670 条主配置规则、25 个策略组、36 个远程文件、29 个域名检查通过。远程列表会更新，未来运行结果可能变化。

在 Shadowrocket“配置 → 测试规则”检查 `guzzoni.apple.com`、`apple-relay.apple.com` 和 `cp4.cloudflare.com` 应进入 `SiriAI`，`chatgpt.com` 应进入 `AI`，`www.apple.com` 应进入 `苹果服务`。

连接异常可重新选择原来的配置恢复；新导入文件不需要删除旧配置。若分流正确而 Siri 提示地区、语言或资格不可用，需要继续核实 Apple 的服务条件。

## 来源

基于用户提供的 `lazy_group.conf` 及此前的静态分流配置整理。规则来源和作者见 [NOTICE.md](NOTICE.md)。本仓库只维护配置编排，不镜像上游规则库。
