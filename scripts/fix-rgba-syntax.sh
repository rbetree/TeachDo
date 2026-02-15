#!/bin/bash

# 修复SCSS rgba()语法为标准CSS语法
# 将 rgba($color: var(--editor-theme-color), $alpha: .05) 
# 转换为 rgba(209, 68, 36, 0.05) 或使用color-mix

EDITOR_DIR="frontend/src/views/Editor"

echo "开始修复rgba()语法..."

# 主题色 #d14424 = rgb(209, 68, 36)
find "$EDITOR_DIR" -name "*.vue" -not -path "*/EditorHeader/*" | while read -r file; do
  # 替换 rgba($color: var(--editor-theme-color), $alpha: .XX) 为标准语法
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.05)/rgba(209, 68, 36, 0.05)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha:\.05)/rgba(209, 68, 36, 0.05)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.1)/rgba(209, 68, 36, 0.1)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.15)/rgba(209, 68, 36, 0.15)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.2)/rgba(209, 68, 36, 0.2)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.25)/rgba(209, 68, 36, 0.25)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.75)/rgba(209, 68, 36, 0.75)/g' "$file"
  sed -i 's/rgba($color: var(--editor-theme-color), $alpha: \.08)/rgba(209, 68, 36, 0.08)/g' "$file"
done

echo "✅ rgba()语法修复完成！"