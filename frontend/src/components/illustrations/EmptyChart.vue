<template>
  <svg
    viewBox="0 0 120 120"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- 图表背景 -->
    <rect
      x="20"
      y="30"
      width="80"
      height="60"
      rx="4"
      fill="#f0f9ff"
      stroke="#165dff"
      stroke-width="2"
    />
    
    <!-- 坐标轴 -->
    <line
      x1="30"
      y1="85"
      x2="90"
      y2="85"
      stroke="#165dff"
      stroke-width="2"
    />
    <line
      x1="30"
      y1="85"
      x2="30"
      y2="35"
      stroke="#165dff"
      stroke-width="2"
    />
    
    <!-- 空数据点（虚线） -->
    <line
      x1="40"
      y1="75"
      x2="40"
      y2="85"
      stroke="#d9d9d9"
      stroke-width="1.5"
      stroke-dasharray="4 2"
    />
    <line
      x1="55"
      y1="65"
      x2="55"
      y2="85"
      stroke="#d9d9d9"
      stroke-width="1.5"
      stroke-dasharray="4 2"
    />
    <line
      x1="70"
      y1="55"
      x2="70"
      y2="85"
      stroke="#d9d9d9"
      stroke-width="1.5"
      stroke-dasharray="4 2"
    />
    
    <!-- 虚线指示 -->
    <circle
      cx="40"
      cy="75"
      r="3"
      fill="none"
      stroke="#165dff"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      opacity="0.5"
    />
    <circle
      cx="55"
      cy="65"
      r="3"
      fill="none"
      stroke="#165dff"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      opacity="0.5"
    />
    <circle
      cx="70"
      cy="55"
      r="3"
      fill="none"
      stroke="#165dff"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      opacity="0.5"
    />
    
    <!-- 装饰元素 -->
    <circle
      cx="100"
      cy="25"
      r="4"
      fill="#00b42a"
      opacity="0.5"
    />
    <circle
      cx="10"
      cy="40"
      r="3"
      fill="#ff7d00"
      opacity="0.5"
    />
    <circle
      cx="15"
      cy="95"
      r="2"
      fill="#165dff"
      opacity="0.5"
    />
    
    <!-- 装饰线条 -->
    <line
      x1="95"
      y1="30"
      x2="100"
      y2="25"
      stroke="#00b42a"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      opacity="0.5"
    />
    <line
      x1="15"
      y1="45"
      x2="18"
      y2="40"
      stroke="#ff7d00"
      stroke-width="1.5"
      stroke-dasharray="3 2"
      opacity="0.5"
    />
    
    <!-- 向上箭头（表示上升趋势） -->
    <path
      d="M85 50 L95 40 L105 50"
      stroke="#00b42a"
      stroke-width="2"
      stroke-linecap="round"
      fill="none"
      opacity="0.6"
    />
  </svg>
</template>

<script setup>
</script>