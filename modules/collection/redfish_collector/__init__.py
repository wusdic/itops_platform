"""Redfish Collector Module - Hardware metrics collection via Redfish API."""

from .redfish_client import RedfishConfig, RedfishCollector

__all__ = ["RedfishConfig", "RedfishCollector"]
