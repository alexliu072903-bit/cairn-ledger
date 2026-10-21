# Cairn Ledger

从本机 Claude Code 和 Codex transcript 中识别用户对 Agent 做法的纠正，生成可追溯、可计数的 `ledger.jsonl` 和 `regressions.md`。普通内容编辑、补充信息和不确定项不入账；同一原始消息重复扫描不重复计数。

当前版本面向 macOS，Python ≥ 3.9（仅标准库），以及已登录、支持代码中所用 `codex exec` 参数的 Codex CLI。当前只覆盖本机实际存在的 Claude Code / Codex transcript；不采集 claude.ai 云端会话。来源日志格式变化可能导致解析失败，失败会显示在本地视图中。会话深链兼容性尚未验证；保留文件和行号作为定位依据。

## 安装

仓库只保存代码与文档。运行目录必须在仓库外，安装不会加载服务，也不会启用分类。

```sh
python3 install.py
```

默认安装到 `~/.codex/ledger/`。可用 `--runtime /absolute/runtime/path` 自定义目录。已有配置和数据不会被覆盖，旧代码会复制到运行目录的 `backups/`。现有安装只更新代码可用 `python3 install.py --code-only`；已运行的 watcher 需重启才会加载 watcher 代码变化。

编辑运行目录的 `config.json`：

- `sources`：本机日志目录；不存在的来源应从配置移除（Codex archive 目录可缺省）。
- `vault`：输出目录，先创建；应位于此仓库外。
- `self_root`：规则目录，需有 `self.md`、`process.md`、`build.md`、`engineering.md`、`foundations.md` 五个文件；不使用的文件可留空。只读取以 `- ` 开头的规则。
- `codex`：本机 Codex CLI 路径；`model` 为空时使用 CLI 默认模型。
- `since`：带时区的 ISO 时间，决定首次回溯起点。视图时间当前以 Asia/Shanghai 显示。

路径支持 `~`。示例配置中的回溯起点只是占位，请自行设置。先检查来源（输出包含本机文件路径，不应公开）：

```sh
python3 ~/.codex/ledger/ledger.py scan
```

确认授权后将 `classification_enabled` 改为 `true`，再手动运行：

```sh
python3 ~/.codex/ledger/process-ledger
```

默认文件静默 10 分钟后才处理，轮询间隔 5 秒。仅已结束轮次参与分类；`--force` 可绕过静默窗口，但不会绕过轮次完成、授权或额度检查。默认每小时 ≤ 4 次、每天 ≤ 24 次分类，每批 ≤ 20 条。无新工作时 watcher 不启动处理器或模型调用。

## 数据与模型调用

会话原文、游标、分类日志、运行配置与输出仅保存在本机，**不应提交到 Git**。本仓库没有上传这些运行文件的机制；`.gitignore` 覆盖运行目录和 JSONL 文件，但仍需在每次提交前检查暂存内容。

启用分类后，候选短片段、必要的前文、规则文本及已有类别会通过当前登录的 Codex CLI 发送给模型服务。正则会脱敏常见密钥、邮箱和手机号，但不能保证识别所有个人信息；规则文本会原样发送。默认关闭分类，只有接受该数据流后才开启。分类调用使用独立 cwd、`--ephemeral`、只读 sandbox 和禁用工具配置；输出经本地校验后才写入账本。分类失败不推进对应处理游标，模型调用额度仍计入。

## 后台启动与停用

首次安装会在运行目录生成本机专用 plist。确认手动运行正常后：

```sh
mkdir -p ~/Library/LaunchAgents
cp ~/.codex/ledger/com.cairn.ledger.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cairn.ledger.plist
launchctl print gui/$(id -u)/com.cairn.ledger
```

已有其他 label 的 ledger 服务时，不应再启动第二个实例；沿用原有服务定义。自定义运行目录时，相应替换上面的 plist 来源路径。

停用：

```sh
launchctl bootout gui/$(id -u)/com.cairn.ledger
```

并将本地 `config.json` 的 `classification_enabled` 设为 `false`。停用不删除任何数据；已有其他 label 的安装应使用其实际 label。再次启动需显式 bootstrap，不会因安装脚本自动恢复。

## 验证

```sh
python3 -m unittest -v test_ledger.py test_install.py
```

测试使用虚构消息和临时目录，不读取真实会话、不调用模型。运行后保留的合成数据位于被 Git 忽略的 `test-runs/` 与系统临时目录。
