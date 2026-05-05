<template>
  <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- 警示框 -->
    <path d="M60 20 L100 90 L20 90 Z" fill="#fff8e6" stroke="#ff7d00" stroke-width="2.5" stroke-linejoin="round"/>
    
    <!-- 感叹号 -->
    <rect x="56" y="42" width="8" height="22" rx="2" fill="#ff7d00"/>
    <circle cx="60" cy="74" r="3" fill="#ff7d00"/>
    
    <!-- 装饰元素 -->
    <circle cx="15" cy="30" r="4" fill="#ff7d00" opacity="0.4"/>
    <circle cx="105" cy="25" r="3" fill="#00b42a" opacity="0.5"/>
    <circle cx="95" cy="95" r="3" fill="#165dff" opacity="0.4"/>
    
    <!-- 脉冲环 -->
    <circle cx="60" cy="55" r="35" fill="none" stroke="#ff7d00" stroke-width="1" opacity="0.2">
      <animate attributeName="r" values="35;45;35" dur="2s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.2;0;0.2" dur="2s" repeatCount="indefinite"/>
    </circle>
    
    <!-- 装饰线条 -->
    <line x1="8" y1="55" x2="15" y2="58" stroke="#ff7d00" stroke-width="1.5" stroke-dasharray="3 2" opacity="0.5"/>
    <line x1="100" y1="45" x2="92" y2="50" stroke="#165dff" stroke-width="1.5" stroke-dasharray="3 2" opacity="0.5"/>
  </svg>
</template>

<script setup>
</script>