# -*- coding: utf-8 -*-
"""
ITOps Platform - Script Executor
脚本执行器
"""
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import tempfile
import os


@dataclass
class ScriptResult:
    """脚本执行结果"""
    script_id: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0
    executed_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


class ScriptExecutor:
    """脚本执行器"""
    
    def __init__(self):
        self._scripts: Dict[str, str] = {}
    
    def register_script(self, script_id: str, content: str):
        """注册脚本"""
        self._scripts[script_id] = content
    
    def get_script(self, script_id: str) -> Optional[str]:
        """获取脚本"""
        return self._scripts.get(script_id)
    
    async def execute(
        self,
        script_id: str,
        language: str = "bash",
        args: List[str] = None,
        env: Dict[str, str] = None,
        timeout: int = 300
    ) -> ScriptResult:
        """执行脚本"""
        script_content = self.get_script(script_id)
        if not script_content:
            return ScriptResult(
                script_id=script_id,
                exit_code=1,
                error=f"Script {script_id} not found"
            )
        
        return await self.execute_code(
            script_content,
            language=language,
            args=args,
            env=env,
            timeout=timeout
        )
    
    async def execute_code(
        self,
        code: str,
        language: str = "bash",
        args: List[str] = None,
        env: Dict[str, str] = None,
        timeout: int = 300
    ) -> ScriptResult:
        """执行代码"""
        start_time = datetime.now()
        args = args or []
        env = env or {}
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=self._get_suffix(language),
                delete=False
            ) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # 构建命令
                cmd = self._build_command(language, temp_file, args)
                
                # 设置环境变量
                exec_env = os.environ.copy()
                exec_env.update(env)
                
                # 执行
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=exec_env
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                return ScriptResult(
                    script_id="temp",
                    exit_code=process.returncode,
                    stdout=stdout.decode('utf-8', errors='ignore'),
                    stderr=stderr.decode('utf-8', errors='ignore'),
                    duration=duration
                )
            
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            return ScriptResult(
                script_id="temp",
                exit_code=124,
                stdout="",
                stderr=f"Script execution timed out after {timeout} seconds",
                duration=duration,
                error="Timeout"
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return ScriptResult(
                script_id="temp",
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration=duration,
                error=str(e)
            )
    
    def _get_suffix(self, language: str) -> str:
        """获取文件后缀"""
        suffixes = {
            "bash": ".sh",
            "python": ".py",
            "powershell": ".ps1",
        }
        return suffixes.get(language, ".sh")
    
    def _build_command(self, language: str, script_file: str, args: List[str]) -> List[str]:
        """构建执行命令"""
        if language == "bash":
            return ["bash", script_file] + args
        elif language == "python":
            return ["python3", script_file] + args
        elif language == "powershell":
            return ["pwsh", "-File", script_file] + args
        else:
            return ["bash", script_file] + args
