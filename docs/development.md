# 开发与更新

[← 返回首页](../README.md)

## 目录

```text
cairn-ledger/
├── ledger.py              # 解析、分类校验、写入、视图与 watcher
├── install.py             # 部署代码，保留本机配置与数据
├── config.example.json    # 默认关闭分类
├── bin/                   # 安装到运行目录的命令入口
├── schemas/               # 分类结果 schema
├── launchd/               # 不含个人路径的服务模板
├── tests/                 # 虚构数据与离线测试
└── docs/                  # 使用说明、演示与预览
```

代码仓库是源码来源；运行目录是安装产物与本机状态。安装时，schema 和命令入口会被复制到运行目录根部，保留现有调用路径。

## 验证

在仓库根目录执行：

```sh
python3 -m unittest discover -s tests -v
python3 docs/demo.py
```

测试不读取真实会话、不调用模型。合成测试数据保留在被忽略的 `test-runs/` 与系统临时目录中。

## 更新现有安装

```sh
git pull --ff-only
python3 install.py --code-only
```

`--code-only` 要求已有 `config.json`，只更新运行代码，不改配置、数据和服务定义。旧代码保存在运行目录的 `backups/` 中；安装本身不重启服务。

处理器每次启动会读取新代码；常驻 watcher 的代码更新需显式重启原有服务。重启前确认当前处理已结束，再使用实际 label 停用和重新 bootstrap。不要为了更新而启动第二个 label。

## 发布前检查

检查暂存文件：只保留通用源码、文档和虚构测试。不要上传 JSONL、游标、运行日志、本机配置、真实摘录、定位或个人路径。提交身份使用你希望公开的邮箱。
