import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 外部库样式
import '@icon-park/vue-next/styles/index.css'
import 'prosemirror-view/style/prosemirror.css'
import 'animate.css'

// 新的设计系统样式 (优先级最高)
import '@/assets/styles/index.scss'

// 插件
import Icon from '@/plugins/icon'
import Directive from '@/plugins/directive'

const app = createApp(App)
app.use(Icon)
app.use(Directive)
app.use(createPinia())
app.use(router)
app.mount('#app')
