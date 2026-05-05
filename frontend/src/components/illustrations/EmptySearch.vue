<template>
  <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- 搜索框 -->
    <rect x="25" y="50" width="60" height="35" rx="17.5" fill="#f0f9ff" stroke="#165dff" stroke-width="2"/>
    
    <!-- 搜索图标 -->
    <circle cx="48" cy="63" r="10" fill="none" stroke="#165dff" stroke-width="2.5"/>
    <line x1="55" y1="70" x2="63" y2="78" stroke="#165dff" stroke-width="2.5" stroke-linecap="round"/>
    
    <!-- 闪光效果 -->
    <circle cx="48" cy="63" r="14" fill="none" stroke="#165dff" stroke-width="1" opacity="0.3">
      <animate attributeName="r" values="14;18;14" dur="1.5s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.3;0;0.3" dur="1.5s" repeatCount="indefinite"/>
    </circle>
    
    <!-- 装饰：数据点 -->
    <circle cx="92" cy="42" r="5" fill="#00b42a" opacity="0.5"/>
    <circle cx="18" cy="75" r="3" fill="#ff7d00" opacity="0.5"/>
    <circle cx="95" cy="80" r="4" fill="#165dff" opacity="0.4"/>
    
    <!-- 装饰：虚线 -->
    <line x1="75" y1="35" x2="88" y2="42" stroke="#165dff" stroke-width="1.5" stroke-dasharray="3 2" opacity="0.5"/>
    <line x1="20" y1="68" x2="30" y2="72" stroke="#00b42a" stroke-width="1.5" stroke-dasharray="3 2" opacity="0.5"/>
    
    <!-- 问号装饰 -->
    <text x="95" y="55" font-family="Arial" font-size="14" font-weight="bold" fill="#165dff" opacity="0.6">?</text>
  </svg>
</template>

<script setup>
</script>