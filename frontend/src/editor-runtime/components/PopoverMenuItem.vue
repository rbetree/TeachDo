<template>
  <div class="popover-menu-item" :class="{ 'center': center }" @click="emit('click')">
    <slot></slot>
  </div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  center?: boolean
}>(), {
  center: false,
})

const emit = defineEmits<{
  (event: 'click'): void
}>()
</script>

<style lang="scss" scoped>
.popover-menu-item {
  min-width: 80px;
  padding: 6px 10px;
  border-radius: 2px;
  font-size: 13px;
  cursor: pointer;
  color: #333333;

  &.center {
    text-align: center;
  }

  &:hover {
    background-color: #f1f1f1;
    color: #333333;
  }
  & + .popover-menu-item {
    margin-top: 2px;
  }
}
</style>