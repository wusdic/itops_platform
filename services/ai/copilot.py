# -*- coding: utf-8 -*-
"""
ITOps Platform - AI Copilot
AI运维Copilot
"""
import httpx
from typing import Any, Dict, List, Optional


class AICopilot:
    """AI运维Copilot"""
    
    def __init__(
        self,
        llm_url: str = "http://localhost:11434/v1",
        api_key: str = "",
        model: str = "qwen2.5-7b-instruct",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        self.llm_url = llm_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._system_prompt = """你是一个专业的IT运维助手，帮助用户解决技术问题。
可以提供以下帮助：
1. 服务器运维问题诊断
2. 网络设备配置指导
3. 安全事件分析
4. 故障排除步骤
5. 运维最佳实践建议

请用简洁专业的语言回答问题。"""
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.llm_url,
                headers=headers,
                timeout=120
            )
        return self._client
    
    async def chat(self, message: str, context: List[Dict] = None) -> Dict[str, Any]:
        """对话"""
        client = await self.get_client()
        
        messages = [{"role": "system", "content": self._system_prompt}]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": message})
        
        try:
            response = await client.post("/chat/completions", json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            })
            response.raise_for_status()
            
            data = response.json()
            return {
                "status": "success",
                "response": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "usage": data.get("usage", {}),
            }
        except httpx.HTTPError as e:
            return {"status": "error", "error": str(e)}
    
    async def analyze_alert(self, alert: Dict) -> Dict[str, Any]:
        """分析告警"""
        prompt = f"""请分析以下告警信息，提供诊断建议：

告警级别：{alert.get('level', 'unknown')}
告警内容：{alert.get('message', '')}
主机：{alert.get('host', 'unknown')}
指标：{alert.get('metric', '')}
当前值：{alert.get('value', 0)}
阈值：{alert.get('threshold', 0)}

请提供：
1. 可能的原因分析
2. 建议的排查步骤
3. 建议的处理措施"""
        
        return await self.chat(prompt)
    
    async def diagnose_issue(self, symptoms: str, category: str = "general") -> Dict[str, Any]:
        """诊断问题"""
        category_prompts = {
            "server": "请专注于服务器相关问题，包括CPU、内存、磁盘、网络等。",
            "network": "请专注于网络相关问题，包括连通性、路由、DNS等。",
            "security": "请专注于安全相关问题，包括入侵检测、漏洞等。",
            "database": "请专注于数据库相关问题，包括连接、性能、备份等。",
        }
        
        prompt = f"""{category_prompts.get(category, '')}

请根据以下症状诊断问题：

症状描述：{symptoms}

请提供：
1. 可能的原因
2. 诊断步骤
3. 解决方案"""
        
        return await self.chat(prompt)
    
    async def generate_script(self, task: str, os_type: str = "linux") -> Dict[str, Any]:
        """生成运维脚本"""
        os_hints = {
            "linux": "请使用Linux Shell脚本语法。",
            "windows": "请使用PowerShell脚本语法。",
        }
        
        prompt = f"""{os_hints.get(os_type, '')}

请生成一个运维脚本：

任务：{task}

请提供完整的脚本代码和必要的说明。"""
        
        return await self.chat(prompt)
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
