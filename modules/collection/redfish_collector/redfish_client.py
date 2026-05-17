"""Redfish Client - Collect hardware metrics from Redfish API."""

import base64
import json
import ssl
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RedfishConfig:
    """Redfish API configuration."""

    host: str
    port: int = 443
    username: str = ""
    password: str = ""
    timeout: int = 30
    ssl_verify: bool = True


class RedfishCollector:
    """Collect hardware metrics via Redfish API using urllib.request."""

    def __init__(self, config: RedfishConfig):
        self.config = config
        self.base_url = f"https://{config.host}:{config.port}"
        self._session_id: Optional[str] = None
        self._headers: dict[str, str] = {}

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context based on ssl_verify setting."""
        ctx = ssl.create_default_context()
        if not self.config.ssl_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _create_request(self, url: str, method: str = "GET") -> urllib.request.Request:
        """Create urllib request with Basic Auth and headers."""
        req = urllib.request.Request(url, method=method)

        # Basic Auth header
        credentials = f"{self.config.username}:{self.config.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        req.add_header("Authorization", f"Basic {encoded}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        for key, value in self._headers.items():
            req.add_header(key, value)

        return req

    def _do_request(self, url: str, method: str = "GET") -> dict[str, Any]:
        """Execute HTTP request and return JSON response."""
        ctx = self._create_ssl_context()
        req = self._create_request(url, method)

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=ctx) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"HTTP {e.code}: {e.reason} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection failed: {e.reason}")

    def connect(self) -> bool:
        """Verify connection to /redfish/v1/."""
        try:
            data = self._do_request(f"{self.base_url}/redfish/v1/")
            # Store session info if provided
            if "Session" in data:
                self._session_id = data["Session"].get("@odata.id")
            return True
        except Exception as e:
            raise RuntimeError(f"Redfish connection failed: {e}")

    def _get_collection_members(self, url: str) -> list[dict[str, Any]]:
        """Get all members from a Redfish collection."""
        try:
            data = self._do_request(url)
            members = data.get("Members", [])
            return [m for m in members if "@odata.id" in m]
        except Exception:
            return []

    def collect_systems(self) -> dict[str, Any]:
        """Collect /redfish/v1/Systems/{id} data."""
        result = {}
        systems_url = f"{self.base_url}/redfish/v1/Systems"

        for member in self._get_collection_members(systems_url):
            member_url = member["@odata.id"]
            try:
                system = self._do_request(member_url)

                # CPU info
                cpus = []
                if "Processors" in system:
                    for proc in self._get_collection_members(system["Processors"]["@odata.id"]):
                        cpu_data = self._do_request(proc["@odata.id"])
                        cpus.append({
                            "id": cpu_data.get("Id", ""),
                            "model": cpu_data.get("Model", ""),
                            "manufacturer": cpu_data.get("Manufacturer", ""),
                            "max_speed_mhz": cpu_data.get("MaxSpeedMHz", 0),
                            "total_cores": cpu_data.get("TotalCores", 0),
                            "total_threads": cpu_data.get("TotalThreads", 0),
                            "status": cpu_data.get("Status", {}),
                        })

                # Memory info
                memory = []
                if "Memory" in system:
                    for mem in self._get_collection_members(system["Memory"]["@odata.id"]):
                        mem_data = self._do_request(mem["@odata.id"])
                        memory.append({
                            "id": mem_data.get("Id", ""),
                            "capacity_mb": mem_data.get("CapacityMiB", 0),
                            "type": mem_data.get("MemoryType", ""),
                            "speed_mhz": mem_data.get("OperatingSpeedMhz", 0),
                            "status": mem_data.get("Status", {}),
                        })

                # Storage info
                storage = []
                if "Storage" in system:
                    for stor in self._get_collection_members(system["Storage"]["@odata.id"]):
                        stor_data = self._do_request(stor["@odata.id"])
                        drives = []
                        if "Drives" in stor_data:
                            for drive_ref in stor_data["Drives"]:
                                drive = self._do_request(drive_ref["@odata.id"])
                                drives.append({
                                    "id": drive.get("Id", ""),
                                    "capacity_bytes": drive.get("CapacityBytes", 0),
                                    "media_type": drive.get("MediaType", ""),
                                    "status": drive.get("Status", {}),
                                })
                        storage.append({
                            "id": stor_data.get("Id", ""),
                            "drives": drives,
                        })

                # Network interfaces (MAC)
                network = []
                if "NetworkInterfaces" in system:
                    for ni_ref in self._get_collection_members(system["NetworkInterfaces"]["@odata.id"]):
                        ni = self._do_request(ni_ref["@odata.id"])
                        if "EthernetInterfaces" in ni:
                            for eth_ref in self._get_collection_members(ni["EthernetInterfaces"]["@odata.id"]):
                                eth = self._do_request(eth_ref["@odata.id"])
                                network.append({
                                    "id": eth.get("Id", ""),
                                    "mac_address": eth.get("MACAddress", ""),
                                    "speed_mbps": eth.get("SpeedMbps", 0),
                                    "status": eth.get("Status", {}),
                                })

                # Firmware info
                bios = system.get("BiosVersion", "")
                firmware = []
                if "Bios" in system:
                    bios_data = self._do_request(system["Bios"]["@odata.id"])
                    firmware.append({
                        "component": "BIOS",
                        "version": bios_data.get("Version", bios),
                    })

                result[system.get("Id", "")] = {
                    "id": system.get("Id", ""),
                    "model": system.get("Model", ""),
                    "manufacturer": system.get("Manufacturer", ""),
                    "serial": system.get("SerialNumber", ""),
                    "bios_version": bios,
                    "cpu": cpus,
                    "memory": memory,
                    "storage": storage,
                    "network": network,
                    "firmware": firmware,
                    "status": system.get("Status", {}),
                }
            except Exception as e:
                result[member_url] = {"error": str(e)}

        return result

    def collect_chassis(self) -> dict[str, Any]:
        """Collect /redfish/v1/Chassis/{id} data including power and thermal."""
        result = {}
        chassis_url = f"{self.base_url}/redfish/v1/Chassis"

        for member in self._get_collection_members(chassis_url):
            member_url = member["@odata.id"]
            try:
                chassis = self._do_request(member_url)

                # Power supplies
                power_supplies = []
                if "Power" in chassis:
                    power_data = self._do_request(chassis["Power"]["@odata.id"])
                    for ps in power_data.get("PowerSupplies", []):
                        power_supplies.append({
                            "id": ps.get("Id", ""),
                            "name": ps.get("Name", ""),
                            "power_output_watts": ps.get("PowerOutputWatts", 0),
                            "power_capacity_watts": ps.get("PowerCapacityWatts", 0),
                            "status": ps.get("Status", {}),
                        })

                # Thermal (fans and temperatures)
                fans = []
                temperatures = []
                if "Thermal" in chassis:
                    thermal_data = self._do_request(chassis["Thermal"]["@odata.id"])
                    for fan in thermal_data.get("Fans", []):
                        fans.append({
                            "id": fan.get("Id", ""),
                            "name": fan.get("Name", ""),
                            "speed_percent": fan.get("Reading", 0),
                            "status": fan.get("Status", {}),
                        })
                    for temp in thermal_data.get("Temperatures", []):
                        temperatures.append({
                            "id": temp.get("Id", ""),
                            "name": temp.get("Name", ""),
                            "temperature_celsius": temp.get("ReadingCelsius", 0),
                            "status": temp.get("Status", {}),
                        })

                result[chassis.get("Id", "")] = {
                    "id": chassis.get("Id", ""),
                    "type": chassis.get("ChassisType", ""),
                    "model": chassis.get("Model", ""),
                    "serial": chassis.get("SerialNumber", ""),
                    "power_supplies": power_supplies,
                    "fans": fans,
                    "temperatures": temperatures,
                    "status": chassis.get("Status", {}),
                }
            except Exception as e:
                result[member_url] = {"error": str(e)}

        return result

    def collect_managers(self) -> dict[str, Any]:
        """Collect /redfish/v1/Managers/{id} data."""
        result = {}
        managers_url = f"{self.base_url}/redfish/v1/Managers"

        for member in self._get_collection_members(managers_url):
            member_url = member["@odata.id"]
            try:
                manager = self._do_request(member_url)

                # Firmware versions
                firmware = []
                if "FirmwareVersion" in manager:
                    firmware.append({
                        "component": "BMC",
                        "version": manager.get("FirmwareVersion", ""),
                    })

                result[manager.get("Id", "")] = {
                    "id": manager.get("Id", ""),
                    "model": manager.get("Model", ""),
                    "type": manager.get("ManagerType", ""),
                    "firmware": firmware,
                    "status": manager.get("Status", {}),
                }
            except Exception as e:
                result[member_url] = {"error": str(e)}

        return result

    def collect_all_metrics(self) -> dict[str, Any]:
        """Collect all hardware metrics from Redfish API."""
        return {
            "systems": self.collect_systems(),
            "chassis": self.collect_chassis(),
            "managers": self.collect_managers(),
        }
