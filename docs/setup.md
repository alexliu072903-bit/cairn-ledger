# 配置与运行

[← 返回首页](../README.zh-CN.md)

## 配置

安装后编辑运行目录的 `config.json`，不要将本机配置放回源码仓库。路径支持 `~`。

| 字段 | 设置方式 |
| --- | --- |
| `sources.claude` | 本机 Claude Code transcript 根目录，通常为 `~/.claude/projects` |
| `sources.codex` | 本机 Codex 的 `sessions` 和 `archived_sessions`；archive 目录可不存在 |
| `vault` | 输出目录，需先创建，放在源码仓库外 |
| `self_root` | 规则目录，需有 `self.md`、`process.md`、`build.md`、`engineering.md`、`foundations.md`；不用的文件留空 |
| `codex` | Codex CLI 的绝对路径，可用 `command -v codex` 查找，再填入配置 |
| `model` | 为空使用 CLI 默认模型；也可指定当前账号可用的模型 |
| `since` | 带时区的 ISO 时间，例如 `2026-01-12T00:00:00+08:00`；示例日期不是推荐回溯范围 |
| `classification_enabled` | 默认 `false`，接受模型数据流后再设为 `true` |

规则文件只读取以 `- ` 开头、长度足够的条目，并保留真实文件/行号作为引用。规则文本会原样发给模型，请自行检查其中的私密内容。

只使用一个来源时，从 `sources` 删除另一个来源的整个键。必需来源目录缺失会报错，不会悄悄跳过。输出视图的时间当前统一显示为 Asia/Shanghai。

## 手动运行

```sh
python3 ~/.codex/ledger/ledger.py scan
python3 ~/.codex/ledger/process-ledger
```

`scan` 仅列出来源文件与元数据，不调用模型。`process-ledger` 会处理符合条件的轮次；模型开关关闭且出现待分类候选时，报告 `classification_not_authorized`。

手动回溯可加 `--force` 跳过 10 分钟文件静默窗口。它仍保留轮次完成判断、授权开关与额度检查。

```sh
python3 ~/.codex/ledger/process-ledger --force
```

## 默认限制

| 参数 | 默认值 |
| --- | ---: |
| 文件静默窗口 `debounce` | 600 秒 |
| 元数据轮询 `poll` | 5 秒 |
| 滚动小时调用上限 `hour_limit` | 4 |
| 滚动 24 小时调用上限 `day_limit` | 24 |
| 单批候选 `batch_limit` | 20 |
| 单次输入 `input_chars` | 24,000 字符 |
| 单次超时 `timeout` | 180 秒 |
| 原话摘录 `quote_chars` | 160 字符 |

没有新工作时，watcher 只轮询元数据，不启动处理器和模型。首次回溯可能分批完成；调用受限时不要把输出当作已经覆盖全部会话。

## 后台运行

安装会在运行目录生成 `com.cairn.ledger.plist`，其中包含本机绝对路径。这份生成文件不应提交到 Git。

确认手动运行正常后执行：

```sh
mkdir -p ~/Library/LaunchAgents
cp ~/.codex/ledger/com.cairn.ledger.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cairn.ledger.plist
launchctl print gui/$(id -u)/com.cairn.ledger
```

`state = running` 表示 watcher 正在运行；处理是否成功，还应查看 `regressions.md` 顶部的时间和错误状态。

已有其他 label 的 ledger 服务时，沿用已有定义，不启动第二个实例。自定义运行目录时，替换命令中的 plist 来源路径。

## 停用

```sh
launchctl bootout gui/$(id -u)/com.cairn.ledger
```

将本地配置的 `classification_enabled` 设为 `false`。停用不删除数据，再次运行需要显式启动；已有安装使用其实际服务 label。

## 常见状态

| 状态 | 含义与处理 |
| --- | --- |
| `新增 0` | 查看来源状态和待处理数；可能没有纠正，也可能尚未完成轮次或回溯 |
| `rate_limited` | 达到滚动调用上限；watcher 会为该批等待额度恢复，手动运行则稍后重试 |
| `classification_not_authorized` | 分类开关关闭；先确认数据流，再决定是否启用 |
| `source_missing` | 来源目录不存在；修改路径或移除不用的来源 |
| `unsupported_codex_user_schema` | 当前日志格式不受支持；保留错误信息供排查 |
| `classifier_exit_*` | CLI 执行失败；核查 CLI 登录和版本参数兼容性 |

其他处理失败不会推进对应工作单元游标；修复原因后手动重试，或等待来源再次发生变化。watcher 对普通失败不会持续自动重试。
