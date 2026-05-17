"""
VMware vSphere Collector
使用 pyvmomi 连接 vCenter/ESXi 采集虚拟化资源信息
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, TYPE_CHECKING

try:
    from pyVmomi import vim, vmodl
    from pyVim.connect import SmartConnect, Disconnect
    _pyvmomi_available = True
except ImportError:
    _pyvmomi_available = False
    vim = object
    vmodl = object

logger = logging.getLogger(__name__)


@dataclass
class VMwareConfig:
    """VMware 连接配置"""
    host: str                          # vCenter 或 ESXi 地址
    port: int = 443                   # 端口
    user: str = "administrator@vsphere.local"  # 用户名
    password: str = ""                # 密码
    ssl_context: Optional[Any] = None  # SSL 上下文
    datacenter: str = "Datacenter"    # 数据中心名称

    def __post_init__(self):
        if not self.host or not self.password:
            raise ValueError("host 和 password 是必填项")


class VMwareCollector:
    """VMware vSphere 资源采集器"""

    def __init__(self, config: VMwareConfig):
        if not _pyvmomi_available:
            raise ImportError(
                "pyvmomi not installed. Install with: pip install pyvmomi"
            )
        self.config = config
        self._si: Any = None
        self._content: Any = None

    def _connect(self) -> None:
        """建立 vCenter/ESXi 连接"""
        try:
            self._si = SmartConnect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                pwd=self.config.password,
                sslContext=self.config.ssl_context
            )
            self._content = self._si.RetrieveContent()
            logger.info(f"成功连接到 VMware: {self.config.host}")
        except Exception as e:
            logger.error(f"连接 VMware 失败: {e}")
            raise

    def _disconnect(self) -> None:
        """断开连接"""
        if self._si:
            Disconnect(self._si)
            self._si = None
            self._content = None
            logger.info("已断开 VMware 连接")

    def _get_obj(self, vim_type: type, name: str) -> Any:
        """根据类型和名称获取对象"""
        if not self._content:
            self._connect()
        container = self._content.viewManager.CreateContainerView(
            self._content.rootFolder, [vim_type], True
        )
        for item in container.view:
            if item.name == name:
                return item
        return None

    def _get_all_objs(self, vim_type: type) -> List[Any]:
        """获取所有指定类型的对象"""
        if not self._content:
            self._connect()
        container = self._content.viewManager.CreateContainerView(
            self._content.rootFolder, [vim_type], True
        )
        return list(container.view)

    # -------------------- 宿主机采集 --------------------

    def collect_hosts(self) -> List[Dict[str, Any]]:
        """
        采集宿主机信息
        包含: CPU/内存/网络/存储
        """
        if not self._content:
            self._connect()

        hosts = []
        for host in self._get_all_objs(vim.HostSystem):
            # CPU 信息
            cpu_info = {
                "model": host.hardware.cpuModel,
                "cores": host.hardware.cpuInfo.numCpuCores,
                "threads": host.hardware.cpuInfo.numCpuThreads,
                "hz": host.hardware.cpuInfo.hz,
                "cpu_usage_percent": host.summary.quickStats.overallCpuUsage,
            }

            # 内存信息
            mem_info = {
                "total_mb": host.hardware.memorySize / (1024 * 1024),
                "used_mb": host.summary.quickStats.overallMemoryUsage,
                "usage_percent": (
                    host.summary.quickStats.overallMemoryUsage
                    / (host.hardware.memorySize / (1024 * 1024)) * 100
                ),
            }

            # 网络信息
            networks = []
            for net in host.network:
                networks.append({
                    "name": net.name,
                    "type": type(net).__name__,
                })

            # 存储信息
            datastores = []
            for ds in host.datastore:
                datastores.append({
                    "name": ds.name,
                    "capacity_gb": ds.summary.capacity / (1024**3),
                    "free_gb": ds.summary.freeSpace / (1024**3),
                })

            # 主机状态
            hosts.append({
                "name": host.name,
                "status": str(host.overallStatus),
                "connection_state": str(host.runtime.connectionState),
                "power_state": str(host.runtime.powerState),
                "cpu": cpu_info,
                "memory": mem_info,
                "networks": networks,
                "datastores": datastores,
            })

        logger.info(f"采集到 {len(hosts)} 台宿主机")
        return hosts

    # -------------------- 虚拟机采集 --------------------

    def collect_vms(self) -> List[Dict[str, Any]]:
        """
        采集虚拟机信息
        包含: CPU/内存/磁盘/网络
        """
        if not self._content:
            self._connect()

        vms = []
        for vm in self._get_all_objs(vim.VirtualMachine):
            # CPU 信息
            cpu_info = {
                "num_cpus": vm.config.hardware.numCPU,
                "num_cores_per_socket": vm.config.hardware.numCoresPerSocket,
                "cpu_usage_percent": (
                    vm.summary.quickStats.overallCpuUsage
                    if vm.summary.quickStats else 0
                ),
            }

            # 内存信息
            mem_info = {
                "memory_mb": vm.config.hardware.memoryMB,
                "memory_usage_percent": (
                    vm.summary.quickStats.overallCpuDemand
                    if vm.summary.quickStats else 0
                ),
            }

            # 磁盘信息
            disks = []
            for disk in vm.config.hardware.device:
                if isinstance(disk, vim.vm.device.VirtualDisk):
                    disks.append({
                        "label": disk.deviceInfo.label,
                        "capacity_gb": disk.capacityInKB / (1024 * 1024),
                        "thin_provisioned": disk.diskMode == "persistent",
                    })

            # 网络信息
            networks = []
            for nic in vm.config.hardware.device:
                if isinstance(nic, vim.vm.device.VirtualEthernetCard):
                    networks.append({
                        "label": nic.deviceInfo.label,
                        "mac_address": nic.macAddress,
                        "connected": nic.connectable.connected,
                    })

            # 虚拟机状态
            vms.append({
                "name": vm.name,
                "status": str(vm.overallStatus),
                "power_state": str(vm.runtime.powerState),
                "cpu": cpu_info,
                "memory": mem_info,
                "disks": disks,
                "networks": networks,
                "host": vm.runtime.host.name if vm.runtime.host else None,
                "guest": vm.guest.guestFullName if vm.guest else None,
            })

        logger.info(f"采集到 {len(vms)} 台虚拟机")
        return vms

    # -------------------- 数据存储采集 --------------------

    def collect_datastores(self) -> List[Dict[str, Any]]:
        """采集数据存储信息"""
        if not self._content:
            self._connect()

        datastores = []
        for ds in self._get_all_objs(vim.Datastore):
            # 获取关联的宿主机
            hosts = [h.name for h in ds.host] if hasattr(ds, 'host') else []

            datastores.append({
                "name": ds.name,
                "type": ds.summary.type,
                "capacity_gb": ds.summary.capacity / (1024**3),
                "free_gb": ds.summary.freeSpace / (1024**3),
                "usage_percent": (
                    (ds.summary.capacity - ds.summary.freeSpace)
                    / ds.summary.capacity * 100
                ),
                "hosts": hosts,
            })

        logger.info(f"采集到 {len(datastores)} 个数据存储")
        return datastores

    # -------------------- 集群采集 --------------------

    def collect_clusters(self) -> List[Dict[str, Any]]:
        """采集集群信息"""
        if not self._content:
            self._connect()

        clusters = []
        for cluster in self._get_all_objs(vim.ClusterComputeResource):
            # 集群资源使用情况
            resource_info = {
                "cpu_used_mhz": cluster.summary.usageSummary.cpuUsedMHz,
                "cpu_total_mhz": cluster.summary.usageSummary.cpuTotalMHz,
                "cpu_usage_percent": cluster.summary.usageSummary.cpuUsagePercent,
                "mem_used_mb": cluster.summary.usageSummary.memUsedMB,
                "mem_total_mb": cluster.summary.usageSummary.memTotalMB,
                "mem_usage_percent": cluster.summary.usageSummary.memUsagePercent,
            }

            # 主机列表
            hosts = [h.name for h in cluster.host]

            clusters.append({
                "name": cluster.name,
                "status": str(cluster.overallStatus),
                "num_hosts": len(hosts),
                "num_vms": cluster.summary.usageSummary.numVms,
                "resource": resource_info,
                "hosts": hosts,
            })

        logger.info(f"采集到 {len(clusters)} 个集群")
        return clusters

    # -------------------- 综合采集 --------------------

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        综合采集所有指标
        包含: 宿主机状态/虚拟机列表/数据存储/集群资源
        """
        if not self._content:
            self._connect()

        try:
            return {
                "success": True,
                "hosts": self.collect_hosts(),
                "vms": self.collect_vms(),
                "datastores": self.collect_datastores(),
                "clusters": self.collect_clusters(),
            }
        except Exception as e:
            logger.error(f"采集失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            self._disconnect()

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()
        return False
