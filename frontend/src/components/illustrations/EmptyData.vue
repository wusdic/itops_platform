<template>
  <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- 主数据库图标 -->
    <ellipse cx="60" cy="95" rx="25" ry="6" fill="#e6f7ff" stroke="#165dff" stroke-width="1.5"/>
    <path d="M35 40 L35 90 Q35 95 60 95 Q85 95 85 90 L85 40 Q85 35 60 35 Q35 35 35 40 Z" fill="#e8f4ff" stroke="#165dff" stroke-width="2"/>
    <ellipse cx="60" cy="40" rx="25" ry="6" fill="#f0f9ff" stroke="#165dff" stroke-width="2"/>
    
    <!-- 数据层 -->
    <ellipse cx="60" cy="52" rx="25" ry="6" fill="none" stroke="#165dff" stroke-width="1" opacity="0.5"/>
    <ellipse cx="60" cy="64" rx="25" ry="6" fill="none" stroke="#165dff" stroke-width="1" opacity="0.5"/>
    
    <!-- 数据线条 -->
    <line x1="40" y1="52" x2="80" y2="52" stroke="#165dff" stroke-width="1.5" opacity="0.6"/>
    <line x1="42" y1="64" x2="78" y2="64" stroke="#165dff" stroke-width="1.5" opacity="0.6"/>
    
    <!-- 顶部光芒 -->
    <path d="M50 25 L60 15 L70 25" stroke="#165dff" stroke-width="2" stroke-linecap="round"/>
    
    <!-- 装饰元素 -->
    <circle cx="20" cy="50" r="4" fill="#00b42a" opacity="0.4"/>
    <circle cx="100" cy="70" r="3" fill="#ff7d00" opacity="0.4"/>
    <circle cx="95" cy="30" r="2" fill="#165dff" opacity="0.5"/>
    <circle cx="25" cy="85" r="2" fill="#00b42a" opacity="0.5"/>
    
    <!-- 动画效果：脉冲 -->
    <circle cx="60" cy="40" r="25" fill="none" stroke="#165dff" stroke-width="1" opacity="0.3">
      <animate attributeName="r" values="25;30;25" dur="2s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.3;0;0.3" dur="2s" repeatCount="indefinite"/>
    </circle>
  </svg>
</template>

<script setup>
</script>