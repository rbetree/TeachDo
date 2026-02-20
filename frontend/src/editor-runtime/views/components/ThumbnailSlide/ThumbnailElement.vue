<template>
  <div 
    class="base-element"
    :class="`base-element-${elementInfo.id}`"
    :style="{
      zIndex: elementIndex,
    }"
  >
    <component
      :is="currentElementComponent"
      :elementInfo="elementInfo"
      target="thumbnail"
    ></component>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { ElementTypes, type PPTElement } from '@editor/types/slides'

import BaseImageElement from '@editor/views/components/element/ImageElement/BaseImageElement.vue'
import BaseTextElement from '@editor/views/components/element/TextElement/BaseTextElement.vue'
import BaseShapeElement from '@editor/views/components/element/ShapeElement/BaseShapeElement.vue'
import BaseLineElement from '@editor/views/components/element/LineElement/BaseLineElement.vue'
import BaseChartElement from '@editor/views/components/element/ChartElement/BaseChartElement.vue'
import BaseTableElement from '@editor/views/components/element/TableElement/BaseTableElement.vue'
import BaseLatexElement from '@editor/views/components/element/LatexElement/BaseLatexElement.vue'
import BaseVideoElement from '@editor/views/components/element/VideoElement/BaseVideoElement.vue'
import BaseAudioElement from '@editor/views/components/element/AudioElement/BaseAudioElement.vue'

const props = defineProps<{
  elementInfo: PPTElement
  elementIndex: number
}>()

const currentElementComponent = computed<unknown>(() => {
  const elementTypeMap = {
    [ElementTypes.IMAGE]: BaseImageElement,
    [ElementTypes.TEXT]: BaseTextElement,
    [ElementTypes.SHAPE]: BaseShapeElement,
    [ElementTypes.LINE]: BaseLineElement,
    [ElementTypes.CHART]: BaseChartElement,
    [ElementTypes.TABLE]: BaseTableElement,
    [ElementTypes.LATEX]: BaseLatexElement,
    [ElementTypes.VIDEO]: BaseVideoElement,
    [ElementTypes.AUDIO]: BaseAudioElement,
  }
  return elementTypeMap[props.elementInfo.type] || null
})
</script>