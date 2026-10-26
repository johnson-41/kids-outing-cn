#!/bin/bash
# 用 v2 版本覆盖更新 GitHub 仓库
# 在终端执行：bash <本文件路径>

GH_USER="johnson-41"
REPO_NAME="kids-outing-cn"
SOURCE_DIR="/Users/johnson/WORK/claude/Workspace/Project/Project-003-亲子出行技能重构/repo-v2"
BRANCH="main"
GH="https://github.com/${GH_USER}/${REPO_NAME}.git"

say() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mxx %s\033[0m\n' "$1"; exit 1; }

say "1/5 检查"
[ -d "$SOURCE_DIR" ] || die "找不到目录：$SOURCE_DIR"
cd "$SOURCE_DIR" || die "进不去目录"
[ -z "$(git config --get user.name)" ] && die "先配 git 身份"
echo "  身份：$(git config --get user.name)"

say "2/5 备份远端现状"
git fetch "$GH" "$BRANCH" --depth=1 >/dev/null 2>&1 || echo "  读不到远端（首次可能正常）"
OLD=$(git rev-parse --short FETCH_HEAD 2>/dev/null || echo "无")
echo "  远端当前提交：$OLD"
echo "  若需回滚，事后执行："
echo "    git push --force $GH $OLD:refs/heads/$BRANCH"

say "3/5 提交新版"
[ -d .git ] || git init -q
git checkout -q -B "$BRANCH"
git add -A
git commit -q -m "docs: 重写 README，参照 SIWFA 版式

- 居中标题块、徽章、一句话主张
- 问题对照表、结构图、目录树
- 三套外观对照图与截图
- 三步接入、一次出行六步、特色机制、FAQ
- 清理废弃配置与缓存文件" 2>/dev/null || echo "  无改动"
git log --oneline -1

say "4/5 覆盖推送"
echo "  远端旧 README 会被替换。"
printf "  继续？(y/N) "
read -r ok
[ "$ok" = "y" ] || die "已取消"
git push --force "$GH" "$BRANCH" || die "推送失败，检查登录状态"

say "5/5 完成"
echo "  仓库：https://github.com/${GH_USER}/${REPO_NAME}"
echo "  下载：https://github.com/${GH_USER}/${REPO_NAME}/raw/${BRANCH}/dist/kids-outing-cn.zip"
