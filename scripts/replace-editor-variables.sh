#!/bin/bash

# 编辑器SCSS变量批量替换脚本
# 用途: 将编辑器中的SCSS变量替换为CSS变量
# 排除: EditorHeader目录（已迁移到全局CSS变量）

EDITOR_DIR="frontend/src/views/Editor"

echo "开始替换编辑器SCSS变量..."

# 排除EditorHeader目录
find "$EDITOR_DIR" -name "*.vue" -not -path "*/EditorHeader/*" | while read -r file; do
  echo "处理: $file"
  
  # 替换主题变量
  sed -i 's/\$themeColor/var(--editor-theme-color)/g' "$file"
  sed -i 's/\$themeHoverColor/var(--editor-theme-hover)/g' "$file"
  
  # 替换文字和边框变量
  sed -i 's/\$textColor/var(--editor-text-color)/g' "$file"
  sed -i 's/\$borderColor/var(--editor-border-color)/g' "$file"
  sed -i 's/\$lightGray/var(--editor-bg-light)/g' "$file"
  
  # 替换效果变量
  sed -i 's/\$boxShadow/var(--editor-box-shadow)/g' "$file"
  sed -i 's/\$borderRadius/var(--editor-border-radius)/g' "$file"
  
  # 替换过渡变量
  sed -i 's/\$transitionDelaySlow/var(--editor-transition-slow)/g' "$file"
  sed -i 's/\$transitionDelayFast/var(--editor-transition-fast)/g' "$file"
  sed -i 's/\$transitionDelay/var(--editor-transition)/g' "$file"
done

echo "✅ 替换完成！"
echo ""
echo "请验证以下内容:"
echo "1. 检查是否有遗漏的SCSS变量"
echo "2. 处理特殊的rgba()函数调用"
echo "3. 验证动画面板的特殊颜色"