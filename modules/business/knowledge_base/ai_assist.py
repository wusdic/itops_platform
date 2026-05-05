"""
BM-03 AI辅助录入
提供AI生成SOP、AI生成故障分析、AI翻译、AI摘要功能
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


class AIAssist:
    """
    AI辅助录入类
    
    提供SOP生成、故障分析生成、翻译、摘要等AI辅助功能
    """
    
    def __init__(self, db: Session, llm_client=None):
        """
        初始化AI辅助
        
        Args:
            db: 数据库会话
            llm_client: LLM客户端(如OpenAI/Azure)
        """
        self.db = db
        self.llm_client = llm_client
    
    def generate_sop(
        self,
        title: str,
        process_description: str,
        category: Optional[str] = None,
        target_audience: Optional[str] = None,
        complexity: str = 'medium',
        include_steps: Optional[List[str]] = None,
        include_warnings: Optional[List[str]] = None,
        include_checkpoints: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        AI生成SOP文档
        
        Args:
            title: 标题
            process_description: 流程描述
            category: 分类
            target_audience: 目标受众
            complexity: 复杂度(low/medium/high)
            include_steps: 预设步骤
            include_warnings: 预设警告
            include_checkpoints: 预设检查点
            
        Returns:
            (是否成功, 生成的内容或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        # 构建提示
        prompt = self._build_sop_prompt(
            title, process_description, category, target_audience,
            complexity, include_steps, include_warnings, include_checkpoints
        )
        
        try:
            response = self.llm_client.chat(prompt)
            return True, response
        except Exception as e:
            return False, f'AI生成失败:{str(e)}'
    
    def _build_sop_prompt(
        self,
        title: str,
        process_description: str,
        category: Optional[str],
        target_audience: Optional[str],
        complexity: str,
        include_steps: Optional[List[str]],
        include_warnings: Optional[List[str]],
        include_checkpoints: Optional[List[str]]
    ) -> str:
        """构建SOP生成提示"""
        prompt = f"""请帮我生成一份标准的SOP(标准操作程序)文档。

# 文档基本信息
- 标题: {title}
- 流程描述: {process_description}
"""
        
        if category:
            prompt += f"- 分类: {category}\n"
        if target_audience:
            prompt += f"- 目标受众: {target_audience}\n"
        
        prompt += f"""
- 复杂度: {complexity}

"""
        
        if include_steps:
            prompt += f"""
# 预设步骤(供参考):
"""
            for i, step in enumerate(include_steps, 1):
                prompt += f"{i}. {step}\n"
        
        if include_warnings:
            prompt += f"""
# 需要注意的警告:
"""
            for w in include_warnings:
                prompt += f"- {w}\n"
        
        if include_checkpoints:
            prompt += f"""
# 检查点:
"""
            for cp in include_checkpoints:
                prompt += f"- {cp}\n"
        
        prompt += """
请按照以下Markdown格式生成完整的SOP文档:

```markdown
# {标题}

## 1. 目的
说明本SOP的目的和适用范围

## 2. 前提条件
执行前需要满足的条件

## 3. 所需工具/资源
需要的工具、软件、权限等

## 4. 操作步骤
详细列出每一步操作,使用有序列表

## 5. 注意事项
执行过程中需要注意的安全事项

## 6. 检查清单
执行完成后的检查项

## 7. 异常处理
常见异常及处理方法

## 8. 相关文档
相关的SOP或文档链接
```

请确保:
1. 内容专业、准确、可操作
2. 步骤清晰、易于理解
3. 包含必要的安全提示
4. 使用中文输出
"""
        
        return prompt
    
    def generate_fault_analysis(
        self,
        symptom: str,
        affected_systems: Optional[List[str]] = None,
        error_logs: Optional[str] = None,
        environment: Optional[str] = None,
        related_cases: Optional[List[str]] = None
    ) -> Tuple[bool, Dict]:
        """
        AI生成故障分析
        
        Args:
            symptom: 故障现象
            affected_systems: 受影响系统
            error_logs: 错误日志
            environment: 环境信息
            related_cases: 相关案例
            
        Returns:
            (是否成功, 分析结果字典或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        prompt = self._build_fault_analysis_prompt(
            symptom, affected_systems, error_logs, environment, related_cases
        )
        
        try:
            response = self.llm_client.chat(prompt)
            # 解析JSON响应
            analysis = self._parse_analysis_response(response)
            return True, analysis
        except Exception as e:
            return False, {'error': f'AI分析失败:{str(e)}'}
    
    def _build_fault_analysis_prompt(
        self,
        symptom: str,
        affected_systems: Optional[List[str]],
        error_logs: Optional[str],
        environment: Optional[str],
        related_cases: Optional[List[str]]
    ) -> str:
        """构建故障分析提示"""
        prompt = f"""请帮我分析以下故障案例,生成结构化的故障分析报告。

# 故障现象
{symptom}
"""
        
        if affected_systems:
            prompt += f"""
# 受影响系统
{', '.join(affected_systems)}
"""
        
        if error_logs:
            prompt += f"""
# 错误日志
```
{error_logs}
```
"""
        
        if environment:
            prompt += f"""
# 环境信息
{environment}
"""
        
        if related_cases:
            prompt += f"""
# 相关案例
{', '.join(related_cases)}
"""
        
        prompt += """
请以JSON格式返回分析结果:

```json
{
  "root_cause": "根本原因分析",
  "impact_analysis": {
    "user_impact": "用户影响等级(none/low/medium/high/critical)",
    "business_impact": "业务影响描述",
    "affected_services": ["受影响的服务列表"],
    "estimated_duration": "预计持续时间"
  },
  "solution": {
    "immediate_actions": [
      "立即采取的行动"
    ],
    "long_term_fix": "长期解决方案",
    "workaround": "临时解决方案(如适用)"
  },
  "prevention": {
    "monitoring_changes": "需要增加的监控项",
    "process_improvements": "流程改进建议",
    "documentation_updates": "需要更新的文档"
  },
  "lessons_learned": "经验教训总结",
  "similar_cases": ["可能的类似问题案例"]
}
```

请确保:
1. 原因分析逻辑清晰、有依据
2. 解决方案具体可操作
3. 预防措施切实可行
4. 使用中文输出
"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """解析分析响应"""
        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            import json
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析JSON,返回原始文本
        return {
            'root_cause': response[:500],
            'raw_response': response
        }
    
    def translate_content(
        self,
        content: str,
        source_lang: str = 'zh-CN',
        target_lang: str = 'en-US',
        preserve_format: bool = True
    ) -> Tuple[bool, str]:
        """
        AI翻译文档内容
        
        Args:
            content: 待翻译内容
            source_lang: 源语言
            target_lang: 目标语言
            preserve_format: 保持格式
            
        Returns:
            (是否成功, 翻译结果或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        lang_names = {
            'zh-CN': '简体中文',
            'en-US': '英文',
            'ja-JP': '日语',
            'ko-KR': '韩语'
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        prompt = f"""请将以下{source_name}内容翻译成{target_name}。

{'请保持Markdown格式不变。' if preserve_format else '请适当调整格式以适应目标语言。'}

# 待翻译内容:
{content}

翻译要求:
1. 保持专业术语的一致性
2. 意译为主,避免生硬翻译
3. 保持原文的语气和风格
4. 技术文档请确保术语准确
"""
        
        try:
            response = self.llm_client.chat(prompt)
            return True, response
        except Exception as e:
            return False, f'翻译失败:{str(e)}'
    
    def summarize_content(
        self,
        content: str,
        max_length: int = 500,
        summary_type: str = 'brief'
    ) -> Tuple[bool, str]:
        """
        AI生成内容摘要
        
        Args:
            content: 待摘要内容
            max_length: 最大长度
            summary_type: 摘要类型(brief/detailed/points)
            
        Returns:
            (是否成功, 摘要内容或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        type_mapping = {
            'brief': '简洁摘要(1-2段)',
            'detailed': '详细摘要(保留关键细节)',
            'points': '要点列表'
        }
        
        prompt = f"""请为以下内容生成{type_mapping.get(summary_type, '简洁摘要')}。

{'摘要长度限制在约{max_length}字以内。' if max_length else ''}

# 待摘要内容:
{content}

摘要要求:
1. 保留核心信息
2. 语言精炼
3. 结构清晰
4. 使用中文输出
"""
        
        try:
            response = self.llm_client.chat(prompt)
            return True, response
        except Exception as e:
            return False, f'摘要生成失败:{str(e)}'
    
    def improve_writing(
        self,
        content: str,
        style: str = 'professional'
    ) -> Tuple[bool, str]:
        """
        AI改进写作
        
        Args:
            content: 待改进内容
            style: 写作风格(professional/casual/technical)
            
        Returns:
            (是否成功, 改进后的内容或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        style_hints = {
            'professional': '专业、正式,适合商务和技术文档',
            'casual': '轻松、友好,适合内部沟通和培训材料',
            'technical': '技术性强,适合技术文档和API说明'
        }
        
        prompt = f"""请改进以下内容的写作质量。

目标风格: {style_hints.get(style, '专业')}

# 原文:
{content}

改进要求:
1. 改善表达清晰度
2. 优化句子结构
3. 修正可能的歧义
4. 保持Markdown格式
5. 使用中文输出
"""
        
        try:
            response = self.llm_client.chat(prompt)
            return True, response
        except Exception as e:
            return False, f'改进写作失败:{str(e)}'
    
    def expand_content(
        self,
        outline: str,
        target_length: int = 2000
    ) -> Tuple[bool, str]:
        """
        AI根据大纲扩展内容
        
        Args:
            outline: 内容大纲
            target_length: 目标长度
            
        Returns:
            (是否成功, 扩展后的内容或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        prompt = f"""请根据以下大纲扩展成一篇完整的文档。

目标长度: 约{target_length}字

# 大纲:
{outline}

扩展要求:
1. 保持大纲结构
2. 内容充实、论述完整
3. 使用适当的示例或说明
4. 保持Markdown格式
5. 使用中文输出
"""
        
        try:
            response = self.llm_client.chat(prompt)
            return True, response
        except Exception as e:
            return False, f'内容扩展失败:{str(e)}'
    
    def suggest_tags(
        self,
        content: str,
        max_tags: int = 5
    ) -> Tuple[bool, List[str]]:
        """
        AI建议标签
        
        Args:
            content: 文档内容
            max_tags: 最大标签数
            
        Returns:
            (是否成功, 标签列表或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        prompt = f"""请为以下文档推荐合适的标签。

要求: 最多{max_tags}个标签,使用中文,简洁明了

# 文档内容:
{content}

请以JSON数组格式返回标签列表:
```json
["标签1", "标签2", ...]
```
"""
        
        try:
            response = self.llm_client.chat(prompt)
            # 解析JSON标签
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                import json
                tags = json.loads(json_match.group())
                return True, tags[:max_tags]
            return True, []
        except Exception as e:
            return False, f'标签建议失败:{str(e)}'
    
    def check_consistency(
        self,
        content: str,
        reference_docs: Optional[List[Dict]] = None
    ) -> Tuple[bool, Dict]:
        """
        AI检查文档一致性
        
        Args:
            content: 待检查内容
            reference_docs: 参考文档列表
            
        Returns:
            (是否成功, 检查结果或错误消息)
        """
        if not self.llm_client:
            return False, '未配置AI客户端'
        
        prompt = f"""请检查以下文档的一致性问题。

# 待检查文档:
{content}
"""
        
        if reference_docs:
            prompt += """
# 参考文档:
"""
            for i, doc in enumerate(reference_docs, 1):
                prompt += f"""
{i}. {doc.get('title', '未命名文档')}
   {doc.get('content', '')[:500]}
"""

        prompt += """
一致性检查要点:
1. 术语使用是否一致
2. 步骤描述是否与其他文档冲突
3. 版本号、编号是否正确
4. 引用链接是否有效

请以JSON格式返回检查结果:
```json
{
  "issues": [
    {
      "type": "terminology/conflict/format/link",
      "location": "问题位置",
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "overall_status": "pass/warn/fail",
  "summary": "总体评价"
}
```
"""
        
        try:
            response = self.llm_client.chat(prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                return True, json.loads(json_match.group())
            return True, {'issues': [], 'summary': response}
        except Exception as e:
            return False, {'error': f'一致性检查失败:{str(e)}'}


class LLMClientBase:
    """LLM客户端基类"""
    
    def chat(self, prompt: str) -> str:
        """发送聊天请求"""
        raise NotImplementedError


class MockLLMClient(LLMClientBase):
    """模拟LLM客户端(用于测试)"""
    
    def chat(self, prompt: str) -> str:
        """返回模拟响应"""
        return "这是模拟AI响应\n\n基于提示: " + prompt[:100] + "..."
