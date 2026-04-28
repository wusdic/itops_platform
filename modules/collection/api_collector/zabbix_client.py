"""
Zabbix API客户端

Zabbix是一个企业级监控解决方案，本模块提供：
- 认证管理（login/logout）
- 主机管理
- 监控项（Item）操作
- 历史数据查询
- 触发器管理
- 告警管理

配置参数：
    url: Zabbix API地址
    user: 用户名
    password: 密码
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class ZabbixClient:
    """
    Zabbix API客户端
    
    提供与Zabbix服务器的完整API交互能力。
    
    Attributes:
        url: Zabbix API URL
        user: 用户名
        password: 密码
        auth_token: 认证令牌
        timeout: 请求超时
    """
    
    def __init__(
        self,
        url: str = 'http://localhost/zabbix/api_jsonrpc.php',
        user: str = 'Admin',
        password: str = 'zabbix',
        timeout: int = 30
    ):
        """
        初始化Zabbix客户端
        
        Args:
            url: Zabbix API地址
            user: 用户名
            password: 密码
            timeout: 超时时间
        """
        self.url = url
        self.user = user
        self.password = password
        self.timeout = timeout
        self.auth_token: Optional[str] = None
        self._id = 0
    
    def _get_next_id(self) -> int:
        """获取下一个请求ID"""
        self._id += 1
        return self._id
    
    def _make_request(
        self,
        method: str,
        params: Optional[Dict] = None,
        auth_required: bool = True
    ) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            method: API方法
            params: 方法参数
            auth_required: 是否需要认证
            
        Returns:
            API响应
        """
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'id': self._get_next_id()
        }
        
        if params:
            payload['params'] = params
        
        if auth_required:
            payload['auth'] = self.auth_token
        
        request = Request(
            self.url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'error' in result:
                    error = result['error']
                    raise ZabbixAPIError(
                        code=error.get('code', -1),
                        message=error.get('message', ''),
                        data=error.get('data', '')
                    )
                
                return result.get('result', {})
                
        except HTTPError as e:
            raise ConnectionError(f"HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            raise ConnectionError(f"Connection Error: {e.reason}")
    
    def login(self) -> bool:
        """
        登录Zabbix
        
        Returns:
            登录是否成功
        """
        result = self._make_request(
            'user.login',
            params={
                'user': self.user,
                'password': self.password
            },
            auth_required=False
        )
        
        self.auth_token = result
        return bool(result)
    
    def logout(self) -> bool:
        """
        登出Zabbix
        
        Returns:
            登出是否成功
        """
        if not self.auth_token:
            return True
        
        try:
            self._make_request('user.logout', auth_required=True)
            self.auth_token = None
            return True
        except Exception:
            self.auth_token = None
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.login()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.logout()
    
    # ========== Host Operations ==========
    
    def host_get(
        self,
        hostids: Optional[List[str]] = None,
        groupids: Optional[List[str]] = None,
        filter_: Optional[Dict] = None,
        selectInterfaces: Optional[List[str]] = None,
        selectGroups: Optional[List[str]] = None,
        output: str = 'extend'
    ) -> List[Dict[str, Any]]:
        """
        获取主机列表
        
        Args:
            hostids: 主机ID列表
            groupids: 主机组ID列表
            filter_: 过滤器
            selectInterfaces: 返回接口信息
            selectGroups: 返回组信息
            output: 输出字段
            
        Returns:
            主机列表
        """
        params = {'output': output}
        
        if hostids:
            params['hostids'] = hostids
        if groupids:
            params['groupids'] = groupids
        if filter_:
            params['filter'] = filter_
        if selectInterfaces:
            params['selectInterfaces'] = selectInterfaces
        if selectGroups:
            params['selectGroups'] = selectGroups
        
        return self._make_request('host.get', params)
    
    def host_create(
        self,
        host: str,
        groups: List[Dict],
        interfaces: Optional[List[Dict]] = None,
        templates: Optional[List[Dict]] = None,
        macros: Optional[List[Dict]] = None,
        inventory: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建主机
        
        Args:
            host: 主机名
            groups: 主机组列表 [{'groupid': '1'}, ...]
            interfaces: 接口配置
            templates: 模板列表
            macros: 宏定义
            inventory: 资产清单
            
        Returns:
            创建结果
        """
        data = {
            'host': host,
            'groups': groups
        }
        
        if interfaces:
            data['interfaces'] = interfaces
        if templates:
            data['templates'] = templates
        if macros:
            data['macros'] = macros
        if inventory:
            data['inventory'] = inventory
        
        return self._make_request('host.create', data)
    
    def host_update(
        self,
        hostid: str,
        **kwargs
    ) -> Dict[str, Any]:
        """更新主机"""
        kwargs['hostid'] = hostid
        return self._make_request('host.update', kwargs)
    
    def host_delete(self, hostids: List[str]) -> Dict[str, Any]:
        """删除主机"""
        return self._make_request('host.delete', hostids)
    
    # ========== Host Group Operations ==========
    
    def hostgroup_get(
        self,
        groupids: Optional[List[str]] = None,
        output: str = 'extend'
    ) -> List[Dict[str, Any]]:
        """获取主机组"""
        params = {'output': output}
        if groupids:
            params['groupids'] = groupids
        return self._make_request('hostgroup.get', params)
    
    def hostgroup_create(
        self,
        name: str
    ) -> Dict[str, Any]:
        """创建主机组"""
        return self._make_request('hostgroup.create', {'name': name})
    
    # ========== Item Operations ==========
    
    def item_get(
        self,
        itemids: Optional[List[str]] = None,
        hostids: Optional[List[str]] = None,
        groupids: Optional[List[str]] = None,
        filter_: Optional[Dict] = None,
        output: str = 'extend',
        selectHosts: Optional[List[str]] = None,
        selectApplications: Optional[List[str]] = None,
        search: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        获取监控项
        
        Args:
            itemids: 监控项ID列表
            hostids: 主机ID列表
            groupids: 主机组ID列表
            filter_: 过滤器
            output: 输出字段
            selectHosts: 返回主机信息
            selectApplications: 返回应用集信息
            search: 搜索条件
            
        Returns:
            监控项列表
        """
        params = {'output': output}
        
        if itemids:
            params['itemids'] = itemids
        if hostids:
            params['hostids'] = hostids
        if groupids:
            params['groupids'] = groupids
        if filter_:
            params['filter'] = filter_
        if selectHosts:
            params['selectHosts'] = selectHosts
        if selectApplications:
            params['selectApplications'] = selectApplications
        if search:
            params['search'] = search
        
        return self._make_request('item.get', params)
    
    def item_create(
        self,
        name: str,
        key_: str,
        hostid: str,
        type_: int = 0,
        value_type: int = 0,
        interfaceid: Optional[str] = None,
        delay: str = '60s',
        history: str = '7d',
        trends: str = '365d',
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建监控项
        
        Args:
            name: 监控项名称
            key_: 监控项键值
            hostid: 主机ID
            type_: 类型（0=Zabbix Agent, 2=SNMPv1, 3=Simple check, ...）
            value_type: 值类型（0=float, 1=character, 2=log, 3=numeric unsigned, 4=text）
            interfaceid: 接口ID
            delay: 采集间隔
            history: 历史数据保留期
            trends: 趋势数据保留期
            
        Returns:
            创建结果
        """
        data = {
            'name': name,
            'key_': key_,
            'hostid': hostid,
            'type': type_,
            'value_type': value_type,
            'delay': delay,
            'history': history,
            'trends': trends
        }
        
        if interfaceid:
            data['interfaceid'] = interfaceid
        
        data.update(kwargs)
        
        return self._make_request('item.create', data)
    
    def item_update(
        self,
        itemid: str,
        **kwargs
    ) -> Dict[str, Any]:
        """更新监控项"""
        kwargs['itemid'] = itemid
        return self._make_request('item.update', kwargs)
    
    def item_delete(self, itemids: List[str]) -> Dict[str, Any]:
        """删除监控项"""
        return self._make_request('item.delete', itemids)
    
    # ========== History Operations ==========
    
    def history_get(
        self,
        itemids: List[str],
        history: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        sortfield: Optional[str] = None,
        sortorder: str = 'DESC'
    ) -> List[Dict[str, Any]]:
        """
        获取历史数据
        
        Args:
            itemids: 监控项ID列表
            history: 历史类型（0=numeric float, 1=character, 2=log, 3=numeric unsigned, 4=text）
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回条数
            sortfield: 排序字段
            sortorder: 排序方向
            
        Returns:
            历史数据列表
        """
        params = {
            'itemids': itemids,
            'history': history,
            'limit': limit,
            'sortorder': sortorder
        }
        
        if start_time:
            params['time_from'] = int(start_time.timestamp())
        if end_time:
            params['time_till'] = int(end_time.timestamp())
        if sortfield:
            params['sortfield'] = sortfield
        
        return self._make_request('history.get', params)
    
    def history_push(
        self,
        itemid: str,
        value: Union[int, float, str],
        clock: Optional[int] = None,
        ns: Optional[int] = None
    ) -> bool:
        """
        推送历史数据（通过Zabbix Sender）
        
        注意：此方法需要Zabbix Trapper类型的监控项
        
        Args:
            itemid: 监控项ID
            value: 值
            clock: 时间戳（默认当前时间）
            ns: 纳秒
            
        Returns:
            是否成功
        """
        # 构建Zabbix Sender格式的数据
        data = [{
            'host': '',  # 需要在调用时指定
            'key': '',
            'value': str(value)
        }]
        
        if clock:
            data[0]['clock'] = clock
        if ns:
            data[0]['ns'] = ns
        
        result = self._make_request('history.push', data)
        return bool(result)
    
    # ========== Trend Operations ==========
    
    def trend_get(
        self,
        itemids: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        获取趋势数据
        
        趋势数据是Zabbix聚合的小时级别统计数据（avg, min, max, count）
        
        Args:
            itemids: 监控项ID列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            趋势数据列表
        """
        params = {'itemids': itemids}
        
        if start_time:
            params['time_from'] = int(start_time.timestamp())
        if end_time:
            params['time_till'] = int(end_time.timestamp())
        
        return self._make_request('trend.get', params)
    
    # ========== Trigger Operations ==========
    
    def trigger_get(
        self,
        triggerids: Optional[List[str]] = None,
        hostids: Optional[List[str]] = None,
        groupids: Optional[List[str]] = None,
        filter_: Optional[Dict] = None,
        output: str = 'extend',
        selectFunctions: Optional[List[str]] = None,
        expandDescription: bool = True,
        expandExpression: bool = True,
        only_true: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取触发器
        
        Args:
            triggerids: 触发器ID列表
            hostids: 主机ID列表
            groupids: 主机组ID列表
            filter_: 过滤器
            output: 输出字段
            selectFunctions: 返回关联的函数
            expandDescription: 展开描述
            expandExpression: 展开表达式
            only_true: 仅返回处于PROBLEM状态的触发器
            
        Returns:
            触发器列表
        """
        params = {
            'output': output,
            'expandDescription': expandDescription,
            'expandExpression': expandExpression
        }
        
        if triggerids:
            params['triggerids'] = triggerids
        if hostids:
            params['hostids'] = hostids
        if groupids:
            params['groupids'] = groupids
        if filter_:
            params['filter'] = filter_
        if selectFunctions:
            params['selectFunctions'] = selectFunctions
        if only_true:
            params['only_true'] = True
        
        return self._make_request('trigger.get', params)
    
    def trigger_create(
        self,
        description: str,
        expression: str,
        priority: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建触发器
        
        Args:
            description: 触发器名称
            expression: 触发表达式
            priority: 优先级（0=未分类, 1=信息, 2=警告, 3=一般严重, 4=严重, 5=灾难）
            
        Returns:
            创建结果
        """
        data = {
            'description': description,
            'expression': expression,
            'priority': priority
        }
        data.update(kwargs)
        
        return self._make_request('trigger.create', data)
    
    # ========== Alert Operations ==========
    
    def alert_get(
        self,
        alertids: Optional[List[str]] = None,
        userids: Optional[List[str]] = None,
        output: str = 'extend'
    ) -> List[Dict[str, Any]]:
        """获取告警"""
        params = {'output': output}
        
        if alertids:
            params['alertids'] = alertids
        if userids:
            params['userids'] = userids
        
        return self._make_request('alert.get', params)
    
    # ========== Event Operations ==========
    
    def event_get(
        self,
        eventids: Optional[List[str]] = None,
        objectids: Optional[List[str]] = None,
        source: int = 0,
        object_: int = 0,
        acknowledged: Optional[bool] = None,
        output: str = 'extend',
        selectHosts: Optional[List[str]] = None,
        time_from: Optional[datetime] = None,
        time_till: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        获取事件
        
        Args:
            eventids: 事件ID列表
            objectids: 对象ID列表
            source: 来源（0=事件来源触发器）
            object_: 对象类型（0=触发器）
            acknowledged: 是否已确认
            output: 输出字段
            selectHosts: 返回主机信息
            time_from: 开始时间
            time_till: 结束时间
            limit: 限制条数
            
        Returns:
            事件列表
        """
        params = {
            'source': source,
            'object': object_,
            'output': output,
            'limit': limit
        }
        
        if eventids:
            params['eventids'] = eventids
        if objectids:
            params['objectids'] = objectids
        if acknowledged is not None:
            params['acknowledged'] = acknowledged
        if selectHosts:
            params['selectHosts'] = selectHosts
        if time_from:
            params['time_from'] = int(time_from.timestamp())
        if time_till:
            params['time_till'] = int(time_till.timestamp())
        
        return self._make_request('event.get', params)
    
    # ========== Template Operations ==========
    
    def template_get(
        self,
        templateids: Optional[List[str]] = None,
        output: str = 'extend'
    ) -> List[Dict[str, Any]]:
        """获取模板"""
        params = {'output': output}
        if templateids:
            params['templateids'] = templateids
        return self._make_request('template.get', params)
    
    def template_create(
        self,
        host: str,
        groups: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """创建模板"""
        data = {
            'host': host,
            'groups': groups
        }
        data.update(kwargs)
        return self._make_request('template.create', data)
    
    def template_link(
        self,
        hostid: str,
        templateids: List[str]
    ) -> Dict[str, Any]:
        """链接模板到主机"""
        return self._make_request('host.massadd', {
            'hosts': [{'hostid': hostid}],
            'templates': [{'templateid': tid} for tid in templateids]
        })
    
    # ========== Maintenance Operations ==========
    
    def maintenance_get(
        self,
        maintenanceids: Optional[List[str]] = None,
        groupids: Optional[List[str]] = None,
        hostids: Optional[List[str]] = None,
        output: str = 'extend'
    ) -> List[Dict[str, Any]]:
        """获取维护期"""
        params = {'output': output}
        if maintenanceids:
            params['maintenanceids'] = maintenanceids
        if groupids:
            params['groupids'] = groupids
        if hostids:
            params['hostids'] = hostids
        return self._make_request('maintenance.get', params)
    
    def maintenance_create(
        self,
        name: str,
        active_since: int,
        active_till: int,
        hostids: Optional[List[str]] = None,
        groupids: Optional[List[str]] = None,
        time_periods: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """创建维护期"""
        data = {
            'name': name,
            'active_since': active_since,
            'active_till': active_till
        }
        if hostids:
            data['hostids'] = hostids
        if groupids:
            data['groupids'] = groupids
        if time_periods:
            data['timeperiods'] = time_periods
        return self._make_request('maintenance.create', data)
    
    # ========== Utility ==========
    
    def version(self) -> str:
        """获取API版本"""
        return self._make_request('api.info', auth_required=False)
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.login()
            self.logout()
            return True
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        self.logout()


class ZabbixAPIError(Exception):
    """Zabbix API错误"""
    
    def __init__(self, code: int, message: str, data: str):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"Zabbix API Error {code}: {message} - {data}")


# 使用示例
if __name__ == '__main__':
    # 配置连接参数
    config = {
        'url': 'http://localhost/zabbix/api_jsonrpc.php',
        'user': 'Admin',
        'password': 'zabbix'
    }
    
    # 创建客户端
    client = ZabbixClient(**config)
    
    # 登录
    if client.login():
        print("Login successful")
    else:
        print("Login failed")
    
    # 获取主机列表
    hosts = client.host_get(
        output=['hostid', 'host', 'name', 'status'],
        selectInterfaces=['interfaceid', 'ip']
    )
    print(f"Found {len(hosts)} hosts")
    for host in hosts[:5]:
        print(f"  - {host['host']} ({host['name']})")
    
    # 获取主机组
    groups = client.hostgroup_get()
    print(f"Found {len(groups)} host groups")
    
    # 获取监控项（CPU使用率示例）
    items = client.item_get(
        search={'key_': 'system.cpu.util'},
        output=['itemid', 'name', 'key_', 'lastvalue'],
        limit=10
    )
    print(f"Found {len(items)} CPU items")
    
    # 获取历史数据（最近24小时）
    from datetime import datetime, timedelta
    
    for item in items[:1]:
        history = client.history_get(
            itemids=[item['itemid']],
            history=0,  # float类型
            start_time=datetime.now() - timedelta(hours=24),
            limit=100
        )
        print(f"History for {item['name']}: {len(history)} records")
    
    # 获取当前告警的触发器
    triggers = client.trigger_get(
        only_true=True,
        output=['triggerid', 'description', 'priority', 'status', 'value'],
        expandDescription=True
    )
    print(f"Found {len(triggers)} active triggers")
    for t in triggers[:3]:
        print(f"  - {t['description']} (Priority: {t['priority']})")
    
    # 获取事件
    events = client.event_get(
        source=0,  # 触发器
        object_=0,  # 触发器
        time_from=datetime.now() - timedelta(hours=24),
        limit=50
    )
    print(f"Found {len(events)} events in last 24h")
    
    # 获取模板
    templates = client.template_get(output=['templateid', 'host', 'name'])
    print(f"Found {len(templates)} templates")
    
    # 获取维护期
    maintenance = client.maintenance_get()
    print(f"Found {len(maintenance)} maintenance periods")
    
    # 登出
    client.logout()
    print("Logged out")
    
    client.close()
    
    # 使用上下文管理器
    with ZabbixClient(**config) as client:
        hosts = client.host_get(output=['hostid', 'host'])
        print(f"Context manager: Found {len(hosts)} hosts")
