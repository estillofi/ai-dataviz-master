#!/usr/bin/env bash
# Публикация на GitHub. Нужны: git, gh (GitHub CLI), выполненный `gh auth login`.
# Запуск из корня репозитория:  bash scripts/publish.sh [имя-репозитория]
set -euo pipefail
NAME="${1:-ai-dataviz-master}"
command -v gh >/dev/null || { echo "Нет gh. Установи: https://cli.github.com/ и выполни gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Сначала: gh auth login"; exit 1; }
OWNER="$(gh api user --jq .login)"
VERSION="$(cat VERSION)"
echo "Владелец: $OWNER  Репозиторий: $NAME  Версия: $VERSION"

# проверки перед публикацией
python3 tests/preflight.py
python3 tests/lint_kit.py
python3 -m unittest discover -s tests -p "test_*.py"
if grep -rIl "Кори\|Корифей\|koriphey" --include=*.md --include=*.py --include=*.html . | grep -v "tests/lint_kit.py\|tests/test_tools.py\|tests/reports/" ; then
  echo "Найдена бренд-специфика (см. выше). Публикация остановлена."; exit 1
fi

# подставить владельца в ссылки и бейджи
grep -rIl "OWNER/ai-dataviz-master\|<ваш""-аккаунт>" --include=*.md . | while read -r f; do
  sed -i.bak -e "s#OWNER/ai-dataviz-master#$OWNER/$NAME#g" -e "s#<ваш""-аккаунт>/ai-dataviz-master#$OWNER/$NAME#g" "$f" && rm -f "$f.bak"
done
python3 tools/make_manifest.py >/dev/null

[ -d .git ] || git init -q -b main
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-$OWNER}" -c user.email="${GIT_AUTHOR_EMAIL:-$OWNER@users.noreply.github.com}" commit -q -m "AI-DataViz Master v$VERSION" || true
gh repo create "$NAME" --public --source . --push \
  --description "Open-source kit: an AI agent interviews you and builds your own honest, on-brand data-visualization skill (charts, dashboards, slides). RU docs."
gh repo edit "$OWNER/$NAME" --add-topic data-visualization --add-topic agent-skills --add-topic claude --add-topic codex --add-topic dataviz --add-topic ai-agents
git tag "v$VERSION" && git push -q origin "v$VERSION"
ZIP="/tmp/$NAME-$VERSION.zip"; git archive --format=zip --prefix="$NAME/" -o "$ZIP" HEAD
gh release create "v$VERSION" "$ZIP" --title "v$VERSION" --notes-file <(sed -n "/## \[$VERSION\]/,/## \[/p" CHANGELOG.md | sed '$d')
echo "Готово: https://github.com/$OWNER/$NAME"
