# GitHub 上传与小组协作

## 1. 本项目如何放入 Git

主项目记录源码、文档、配置、测试、依赖清单及已有的 `results/demo`、`results/migration_check` 两份运行产物。两份结果是同配置的重复验证，不能当作不同研究设计。

`.venv`、IDE 配置、Python 缓存、macOS 元数据和后续新结果目录默认忽略。新增正式实验结果时，先核对体积和内容，再修改 `.gitignore` 中的结果目录白名单。

`vendor/predictive-lsm-trees` 是一个 Git 子模块：主项目记录它的地址和确切提交，而不是将第三方仓库的内部 Git 文件重复上传。本项目使用提交 `495e71a94559a845c76019740341745900a87666`。复用归属见 [THIRD_PARTY.md](../THIRD_PARTY.md)。

## 2. 首次创建 GitHub 仓库

在 [GitHub 新建仓库页面](https://github.com/new) 选择自己的账户并填写名称。建议名为 `monkey-bloom-filter-replication`；公开或私有由小组决定。课程小组起步可先用私有仓库。

建议描述：`DSC5003 Track 2: Python replication of Monkey Bloom-filter memory allocation, with static LSM experiments and analytical cost models.`

将 Add README、Add .gitignore、Choose a license 都保持未初始化状态，因为本地项目已有文件和提交。创建后复制 HTTPS 或 SSH 仓库地址。[GitHub 官方建库说明](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)

如果仓库已经有文件或提交，先查看远端内容再合并；不要直接强制推送覆盖它。

## 3. 连接并上传已有本地提交

在项目根目录执行。`YOUR_REPOSITORY_URL` 是占位符，须替换为实际仓库地址：

```bash
git status
git remote -v
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

如果 `origin` 已存在，先检查是否正确，不要重复添加。首次推送成功后，刷新仓库页面，应能看到 README、代码、文档及 `vendor` 下固定版本的子模块入口。

本机已有 Git；准备阶段未发现 GitHub CLI（`gh`）。上传可以使用终端、PyCharm 或 GitHub Desktop，不必额外安装 CLI。遇到认证要求时，在本机工具中登录。HTTPS Git 操作使用令牌或凭据管理器，SSH 使用密钥；不要将 GitHub 网站登录密码当作 Git 密码，也不要把令牌发到聊天或提交进文件。[GitHub 官方认证说明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)

## 4. 组员获取项目

```bash
git clone --recurse-submodules YOUR_REPOSITORY_URL
```

进入克隆生成的目录。若先前普通克隆导致 vendor 为空，执行：

```bash
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

不要复制别人的 `.venv`。下载 ZIP 不能替代带子模块的克隆；主 README 也提供 vendor 缺失时的手动恢复方法。

私有仓库的组员需要先由仓库所有者添加为协作者，才能克隆和推送。添加协作者由所有者在 GitHub 仓库设置中完成。

## 5. 日常协作示例

开始工作前，确保工作区干净，再更新主分支并创建自己的任务分支：

```bash
git switch main
git pull --ff-only
git submodule update --init --recursive
git switch -c experiment/level-count-plot
```

完成修改后，检查差异、运行与改动相关的验证，只添加实际改动的文件：

```bash
git diff
git add monkey_lab/plotting.py
git diff --cached
git commit -m "Add plot for level-count experiments"
git push -u origin experiment/level-count-plot
```

上面的文件和分支名仅为示例。推送后在 GitHub 创建 Pull Request，由另一位组员查看算法、数据口径和验证结果，再合并。

## 6. 常见情况

| 情况 | 处理 |
|---|---|
| `not a git repository` | 确认终端处于项目根目录 |
| `remote origin already exists` | 用 `git remote -v` 检查已有地址 |
| `Permission denied` / `Authentication failed` | 检查本机登录、密钥以及仓库访问权限 |
| `non-fast-forward` | 远端已有新提交，先查看差异和整合；不要默认强推 |
| 导入时报 vendor 文件缺失 | 执行 `git submodule update --init --recursive` |
| 新实验目录未出现在 `git status` | 它被结果目录规则忽略；正式保留时更新白名单 |

[返回 README](../README.md)
