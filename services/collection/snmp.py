# -*- coding: utf-8 -*-
"""
ITOps Platform - SNMP Collector
SNMP协议数据采集
"""
import asyncio
from typing import Any, Dict, List, Optional
from pysnmp.hlapi import *
from core.log import get_logger

logger = get_logger(__name__)


class SNMPCollector:
    """SNMP采集器"""
    
    def __init__(
        self,
        host: str,
        community: str = "public",
        version: str = "v2c",
        port: int = 161,
        timeout: int = 5,
        retries: int = 3
    ):
        self.host = host
        self.community = community
        self.version = version
        self.port = port
        self.timeout = timeout
        self.retries = retries
    
    async def collect(self, oids: List[str]) -> Dict[str, Any]:
        """采集指定OID的数据"""
        results = {}
        
        for oid in oids:
            try:
                value = await self._get_snmp(oid)
                results[oid] = value
            except Exception as e:
                logger.error(f"SNMP采集失败 {self.host}/{oid}: {e}")
                results[oid] = None
        
        return results
    
    async def _get_snmp(self, oid: str) -> Any:
        """获取单个OID值"""
        loop = asyncio.get_event_loop()
        
        def sync_get():
            error_indication, error_status, error_index, var_bind_table = next(
                getCmd(
                    SnmpEngine(),
                    CommunityData(self.community, mpModel=1 if self.version == "v2c" else 0),
                    UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
            )
            
            if error_indication:
                raise Exception(error_indication)
            
            if error_status:
                raise Exception(f"{error_status.prettyPrint()} at {error_index and var_bind_table[int(error_index) - 1][0]}")
            
            return var_bind_table[0][1]
        
        return await loop.run_in_executor(None, sync_get)
    
    async def walk(self, base_oid: str) -> Dict[str, Any]:
        """SNMP Walk"""
        loop = asyncio.get_event_loop()
        results = {}
        
        def sync_walk():
            for error_indication, error_status, error_index, var_bind_table in nextCmd(
                SnmpEngine(),
                CommunityData(self.community, mpModel=1),
                UdpTransportTarget((self.host, self.port)),
                ContextData(),
                ObjectType(ObjectIdentity(base_oid)),
                lexicographicMode=False
            ):
                if error_indication:
                    raise Exception(error_indication)
                
                for var_bind in var_bind_table:
                    results[str(var_bind[0])] = var_bind[1]
        
        await loop.run_in_executor(None, sync_walk)
        return results
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = await self._get_snmp("1.3.6.1.2.1.1.1.0")  # sysDescr
            return result is not None
        except Exception:
            return False
    
    @staticmethod
    def get_system_oids() -> List[str]:
        """系统常用OID"""
        return [
            "1.3.6.1.2.1.1.1.0",  # sysDescr
            "1.3.6.1.2.1.1.3.0",  # sysUpTime
            "1.3.6.1.2.1.1.5.0",  # sysName
            "1.3.6.1.2.1.2.1.0",  # ifNumber
        ]
    
    @staticmethod
    def get_interface_oids() -> List[str]:
        """接口常用OID"""
        return [
            "1.3.6.1.2.1.2.2.1.1",  # ifIndex
            "1.3.6.1.2.1.2.2.1.2",  # ifDescr
            "1.3.6.1.2.1.2.2.1.5",  # ifSpeed
            "1.3.6.1.2.1.2.2.1.7",  # ifAdminStatus
            "1.3.6.1.2.1.2.2.1.8",  # ifOperStatus
            "1.3.6.1.2.1.2.2.1.10", # ifInOctets
            "1.3.6.1.2.1.2.2.1.16", # ifOutOctets
        ]
