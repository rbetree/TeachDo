# 设计系统文档

本设计系统基于 `frontend-prototype` 原型实现,提供统一的视觉规范和可复用组件。

## 📁 文件结构

```
styles/
├── index.scss              # 主入口文件
├── design-tokens.scss      # 设计变量 (CSS Variables)
├── global-reset.scss       # 全局样式重置
├── typography.scss         # 排版系统
├── utilities.scss          # 工具类
├── components/
│   ├── button.scss        # 按钮样式
│   └── input.scss         # 输入框样式
├── font.scss              # 字体文件 (保留)
├── prosemirror.scss       # ProseMirror样式 (保留)
├── variable.scss          # 旧变量 (待迁移)
├── global.scss            # 旧全局样式 (待迁移)
└── mixin.scss             # SCSS混合 (保留)
```

## 🎨 设计变量 (Design Tokens)

### 颜色系统

#### 浅色主题
```scss
--bg-body: #F8FAFC
--bg-surface: #FFFFFF
--bg-surface-secondary: #F1F5F9
--text-primary: #0F172A
--text-secondary: #64748B
--primary-color: #6366F1
--primary-hover: #4F46E5
```

#### 深色主题
```scss
--bg-body: #0F172A
--bg-surface: #1E293B
--bg-surface-secondary: #334155
--text-primary: #F8FAFC
--text-secondary: #94A3B8
--primary-color: #818CF8
--primary-hover: #6366F1
```

### 间距系统
```scss
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 16px
--spacing-lg: 24px
--spacing-xl: 32px
--spacing-2xl: 48px
```

### 圆角
```scss
--radius-sm: 8px
--radius-md: 12px
--radius-lg: 16px
--radius-xl: 20px
--radius-full: 9999px
```

### 阴影
```scss
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05)
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1)
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1)
```

## 🔧 使用方法

### 在 Vue 组件中使用

```vue
<template>
  <div class="container">
    <h1 class="gradient-text">标题</h1>
    <p class="text-secondary">说明文字</p>
  </div>
</template>

<style scoped>
.custom-card {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-md);
}
</style>
```

### 使用工具类

```vue
<template>
  <div class="d-flex justify-between align-center gap-md p-lg">
    <span class="text-primary font-bold">标题</span>
    <span class="text-secondary text-sm">副标题</span>
  </div>
</template>
```

## 🧩 组件使用

### Button 组件

```vue
<script setup>
import { Button } from '@editor/components/common'
</script>

<template>
  <!-- Primary 按钮 -->
  <Button type="primary" @click="handleClick">
    点击我
  </Button>

  <!-- Secondary 按钮 -->
  <Button type="secondary" size="lg">
    大号按钮
  </Button>

  <!-- Ghost 按钮 -->
  <Button type="ghost" :loading="isLoading">
    加载中
  </Button>

  <!-- 带图标 -->
  <Button type="primary">
    <template #icon>
      <PlusIcon />
    </template>
    添加
  </Button>
</template>
```

### Input 组件

```vue
<script setup>
import { ref } from 'vue'
import { Input } from '@editor/components/common'

const username = ref('')
</script>

<template>
  <!-- 基础输入框 -->
  <Input
    v-model="username"
    label="用户名"
    placeholder="请输入用户名"
    required
  />

  <!-- 带验证状态 -->
  <Input
    v-model="email"
    type="email"
    label="邮箱"
    status="error"
    error-message="邮箱格式不正确"
  />

  <!-- 带前缀图标 -->
  <Input
    v-model="search"
    type="search"
    placeholder="搜索..."
  >
    <template #prefix>
      <SearchIcon />
    </template>
  </Input>

  <!-- 可清除 -->
  <Input
    v-model="text"
    clearable
    show-count
    :maxlength="100"
  />

  <!-- 文本域 -->
  <Input
    v-model="description"
    type="textarea"
    label="描述"
    placeholder="请输入描述"
  />
</template>
```

## 🌓 主题切换

### 使用 useTheme Hook

```vue
<script setup>
import { useTheme } from '@editor/hooks/useTheme'

const { currentTheme, toggleTheme, isDark } = useTheme()
</script>

<template>
  <button @click="toggleTheme">
    {{ isDark ? '☀️' : '🌙' }}
    切换主题
  </button>
</template>
```

### 手动设置主题

```typescript
import { useTheme } from '@editor/hooks/useTheme'

const { setTheme } = useTheme()

// 设置为深色主题
setTheme('dark')

// 设置为浅色主题
setTheme('light')
```

## 📝 工具类参考

### 布局
- `d-flex`, `d-block`, `d-none`, `d-grid`
- `flex-row`, `flex-column`, `flex-wrap`
- `justify-center`, `justify-between`, `align-center`
- `flex-1`, `flex-auto`, `flex-none`

### 间距
- `m-{size}`, `p-{size}` - 全方向
- `mt-{size}`, `pt-{size}` - 上
- `mr-{size}`, `pr-{size}` - 右
- `mb-{size}`, `pb-{size}` - 下
- `ml-{size}`, `pl-{size}` - 左
- `mx-{size}`, `px-{size}` - 水平
- `my-{size}`, `py-{size}` - 垂直
- 尺寸: `0`, `xs`, `sm`, `md`, `lg`, `xl`, `2xl`

### 文字
- `text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`
- `text-primary`, `text-secondary`, `text-theme`
- `text-left`, `text-center`, `text-right`
- `font-normal`, `font-medium`, `font-bold`
- `truncate`, `line-clamp-1`, `line-clamp-2`, `line-clamp-3`

### 圆角
- `rounded-none`, `rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-full`

### 阴影
- `shadow-none`, `shadow-sm`, `shadow-md`, `shadow-lg`

## 🎯 最佳实践

### 1. 优先使用设计变量
```scss
// ✅ 推荐
.my-component {
  color: var(--text-primary);
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
}

// ❌ 避免
.my-component {
  color: #0F172A;
  padding: 16px;
  border-radius: 16px;
}
```

### 2. 使用工具类减少自定义样式
```vue
<!-- ✅ 推荐 -->
<div class="d-flex justify-between align-center p-lg gap-md">
  <span class="text-primary font-bold">标题</span>
</div>

<!-- ❌ 避免 -->
<div class="custom-header">
  <span class="custom-title">标题</span>
</div>

<style>
.custom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  gap: 16px;
}
.custom-title {
  color: var(--text-primary);
  font-weight: bold;
}
</style>
```

### 3. 响应式设计
```vue
<template>
  <div class="container">
    <div class="hide-mobile">桌面端内容</div>
    <div class="hide-desktop">移动端内容</div>
  </div>
</template>
```

## 🔄 迁移指南

### 从旧样式系统迁移

1. **颜色迁移**
   ```scss
   // 旧代码
   color: $themeColor;
   
   // 新代码
   color: var(--primary-color);
   ```

2. **间距迁移**
   ```scss
   // 旧代码
   padding: 16px;
   
   // 新代码
   padding: var(--spacing-md);
   ```

3. **主题切换支持**
   - 确保使用 CSS Variables 而非固定颜色值
   - 测试浅色和深色主题下的显示效果

## 📚 参考资源

- 原型文件: `frontend-prototype/`
- 开发计划: `doc/dev/DEVELOPMENT_PLAN.md`
- 组件文档: `frontend/src/components/common/`
