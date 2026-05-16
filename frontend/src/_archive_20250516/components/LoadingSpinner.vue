<template>
  <el-button
    v-bind="$attrs"
    :loading="loading"
    :disabled="loading"
  >
    <el-icon v-if="loading">
      <Loading />
    </el-icon>
    <slot v-else />
  </el-button>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'

defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.el-button {
  position: relative;
}

.el-button :deep(.el-icon) {
  vertical-align: middle;
}
</style>
