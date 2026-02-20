# 通用组件库文档

## 📦 组件列表

### 基础组件（集合 1.1）
- [Button](#button-按钮) - 按钮组件
- [Input](#input-输入框) - 输入框组件

### 布局组件（集合 1.2）
- [Navbar](#navbar-导航栏) - 顶部导航栏
- [StepProgress](#stepprogress-步骤进度条) - 步骤进度条
- [PageLayout](#pagelayout-页面布局) - 页面布局容器
- [Container](#container-内容容器) - 内容容器

### 高级交互组件（集合 1.3）
- [Modal](#modal-模态框) - 模态框/对话框
- [Spinner](#spinner-加载动画) - 旋转加载动画
- [Loading](#loading-加载提示) - 加载提示组件（带进度）
- [Card](#card-卡片) - 卡片组件
- [Tag](#tag-标签) - 标签/徽章组件

---

## Modal 模态框

模态框组件，用于显示对话框、确认框等场景。

### 基础用法

```vue
<template>
  <Button @click="visible = true">打开模态框</Button>
  
  <Modal v-model="visible" title="提示" @confirm="handleConfirm">
    <p>这是模态框的内容</p>
  </Modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Modal, Button } from '@editor/components/common'

const visible = ref(false)
const handleConfirm = () => {
  console.log('确认')
  visible.value = false
}
</script>
```

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| modelValue | 是否显示 | `boolean` | `false` |
| title | 标题 | `string` | - |
| size | 尺寸 | `'sm' \| 'md' \| 'lg' \| 'xl' \| 'full'` | `'md'` |
| showClose | 显示关闭按钮 | `boolean` | `true` |
| closeOnClickOverlay | 点击遮罩关闭 | `boolean` | `true` |

---

## Spinner 加载动画

旋转加载动画组件。

### 基础用法

```vue
<Spinner />
<Spinner text="加载中..." />
<Spinner variant="primary" size="lg" text="请稍候..." />
```

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| variant | 变体 | `'primary' \| 'secondary' \| 'white'` | `'primary'` |
| size | 尺寸 | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` |
| text | 提示文本 | `string` | - |
| color | 自定义颜色 | `string` | - |

---

## Loading 加载提示

带进度提示的加载组件。

### 基础用法

```vue
<Loading 
  text="正在生成演示文稿..." 
  description="AI 正在撰写内容并应用设计，请稍候"
/>
```

### 带进度条

```vue
<Loading 
  text="上传中..." 
  :progress="uploadProgress"
  show-progress
/>
```

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| text | 主要提示文本 | `string` | - |
| description | 描述文本 | `string` | - |
| showProgress | 显示进度条 | `boolean` | `false` |
| progress | 进度值 (0-100) | `number` | `0` |

---

## Card 卡片

卡片组件，支持选中状态和悬停效果。

### 基础用法

```vue
<Card>
  <h3>卡片标题</h3>
  <p>卡片内容</p>
</Card>
```

### 可选择卡片（模板选择场景）

```vue
<Card
  hoverable
  clickable
  selectable
  :selected="selectedId === 1"
  @click="selectedId = 1"
>
  <template #header>
    <img src="/template.jpg" alt="模板" />
  </template>
  <h3>极简科技</h3>
  <Tag>商务</Tag>
  <Tag>科技</Tag>
</Card>
```

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| variant | 变体 | `'default' \| 'bordered' \| 'shadow'` | `'default'` |
| hoverable | 可悬停 | `boolean` | `false` |
| clickable | 可点击 | `boolean` | `false` |
| selectable | 可选择 | `boolean` | `false` |
| selected | 是否选中 | `boolean` | `false` |
| cover | 封面图片 | `string` | - |

---

## Tag 标签

标签/徽章组件。

### 基础用法

```vue
<Tag>默认标签</Tag>
<Tag variant="primary">主要标签</Tag>
<Tag variant="success">成功</Tag>
<Tag variant="warning">警告</Tag>
<Tag variant="error">错误</Tag>
```

### 可关闭

```vue
<Tag closable @close="handleClose">可关闭标签</Tag>
```

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| variant | 变体 | `'default' \| 'primary' \| 'success' \| 'warning' \| 'error' \| 'info'` | `'default'` |
| size | 尺寸 | `'sm' \| 'md' \| 'lg'` | `'md'` |
| closable | 可关闭 | `boolean` | `false` |
| rounded | 圆角 | `boolean` | `false` |

---

## 完整示例

### 模板选择页面

```vue
<template>
  <PageLayout>
    <Container size="lg">
      <h2>选择设计风格</h2>
      
      <div class="template-grid">
        <Card
          v-for="template in templates"
          :key="template.id"
          variant="shadow"
          hoverable
          clickable
          selectable
          :selected="selectedTemplate === template.id"
          @click="selectTemplate(template.id)"
        >
          <template #header>
            <img :src="template.image" :alt="template.name" />
          </template>
          
          <h3>{{ template.name }}</h3>
          
          <div class="tags">
            <Tag v-for="tag in template.tags" :key="tag" size="sm">
              {{ tag }}
            </Tag>
          </div>
        </Card>
      </div>
      
      <div class="action-bar">
        <Button variant="secondary" @click="goBack">返回修改大纲</Button>
        <Button variant="primary" @click="generate">生成演示文稿</Button>
      </div>
    </Container>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { PageLayout, Container, Card, Tag, Button } from '@editor/components/common'

const selectedTemplate = ref(1)
const templates = ref([
  { id: 1, name: '极简科技', image: '/t1.jpg', tags: ['商务', '科技'] },
  { id: 2, name: '暖色活力', image: '/t2.jpg', tags: ['教育', '创意'] },
])

const selectTemplate = (id: number) => {
  selectedTemplate.value = id
}
</script>

<style scoped>
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
  margin: 24px 0;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 32px;
}
</style>
```

### 加载页面

```vue
<template>
  <PageLayout>
    <Loading
      text="正在生成演示文稿..."
      description="AI 正在撰写内容并应用设计，请稍候"
      :progress="progress"
      show-progress
    />
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PageLayout, Loading } from '@editor/components/common'

const progress = ref(0)

onMounted(() => {
  const timer = setInterval(() => {
    progress.value += 10
    if (progress.value >= 100) {
      clearInterval(timer)
    }
  }, 500)
})
</script>
```

### 确认对话框

```vue
<template>
  <div>
    <Button @click="showDeleteConfirm = true">删除</Button>
    
    <Modal
      v-model="showDeleteConfirm"
      title="确认删除"
      size="sm"
      @confirm="handleDelete"
    >
      <p>确定要删除这个项目吗？此操作无法撤销。</p>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Modal, Button } from '@editor/components/common'

const showDeleteConfirm = ref(false)

const handleDelete = () => {
  console.log('已删除')
  showDeleteConfirm.value = false
}
</script>
```

---

## 设计规范

### 颜色系统

所有组件使用统一的 CSS Variables，支持浅色/深色主题。

### 响应式

- 移动端：<= 768px
- 桌面端：> 768px

### 可访问性

所有组件都遵循 WCAG 2.1 AA 标准：

- ✅ 支持键盘导航
- ✅ 提供 ARIA 属性
- ✅ 合适的焦点样式
- ✅ 语义化 HTML

---

**更新日期**: 2025-11-29  
**版本**: 1.0.0