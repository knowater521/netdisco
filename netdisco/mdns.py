"""Add support for discovering mDNS services."""
from typing import List  # noqa: F401

from zeroconf import (
    Zeroconf,
    ServiceBrowser,
    ServiceInfo,
    DNSRecord,
    DNSPointer,
    ServiceStateChange,
)


class FastServiceBrowser(ServiceBrowser):
    """ServiceBrowser that does not process record updates."""

    def update_record(self, zc: Zeroconf, now: float, record: DNSRecord) -> None:
        """Ignore record updates for non-ptrs."""
        if record.name not in self.types or not isinstance(record, DNSPointer):
            return
        super().update_record(zc, now, record)


class MDNS:
    """Base class to discover mDNS services."""

    def __init__(self, zeroconf_instance=None):
        """Initialize the discovery."""
        self.zeroconf = zeroconf_instance
        self._created_zeroconf = False
        self.services = []  # type: List[ServiceInfo]
        self._browser = None  # type: ServiceBrowser

    def register_service(self, service):
        """Register a mDNS service."""
        self.services.append(service)

    def start(self):
        """Start discovery."""
        try:
            if not self.zeroconf:
                self.zeroconf = Zeroconf()
                self._created_zeroconf = True

            services_by_type = {}

            for service in self.services:
                services_by_type.setdefault(service.typ, [])
                services_by_type[service.typ].append(service)

            def _service_update(zeroconf, service_type, name, state_change):
                if state_change == ServiceStateChange.Added:
                    for service in services_by_type[service_type]:
                        service.add_service(zeroconf, service_type, name)
                elif state_change == ServiceStateChange.Removed:
                    for service in services_by_type[service_type]:
                        service.remove_service(zeroconf, service_type, name)

            types = [service.typ for service in self.services]
            self._browser = FastServiceBrowser(
                self.zeroconf, types, handlers=[_service_update]
            )
        except Exception:  # pylint: disable=broad-except
            self.stop()
            raise

    def stop(self):
        """Stop discovering."""
        if self._browser:
            self._browser.cancel()
            self._browser = None

        for service in self.services:
            service.reset()

        if self._created_zeroconf:
            self.zeroconf.close()
            self.zeroconf = None

    @property
    def entries(self):
        """Return all entries in the cache."""
        return self.zeroconf.cache.entries()
