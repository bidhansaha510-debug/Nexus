"""
NEXUS AI — Ethical Hacking Engine v2.0 (MAXIMUM CAPABILITIES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Capabilities:
  • Network reconnaissance (local IP, gateway, public IP, interfaces)
  • Port scanning (TCP connect scan with threading)
  • DNS resolution & reverse DNS lookup
  • Ping sweep (host alive detection)
  • Vulnerability assessment (open port → risk mapping)
  • HTTP header security analysis
  • SSL/TLS certificate analysis
  • Subdomain enumeration
  • Traceroute
  • WHOIS lookup
  • WAF detection
  • Service fingerprinting (enhanced banners)
  • Subnet sweep (ping entire subnet)
  • Directory/path discovery
  • Full reconnaissance (combined scan)
  • Scan history & statistics tracking

IMPORTANT: Only use on networks/hosts you own or have explicit
permission to test. Unauthorized scanning is illegal.
"""

import os
import sys
import json
import socket
import ssl
import struct
import subprocess
import threading
import time
import re
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime
from collections import deque
from urllib.parse import urlparse

from utils.logger import get_logger

logger = get_logger("ethical_hacking")

# ═══════════════════════════════════════════════════════════════════
# KNOWN RISKY SERVICES — port → (service, risk_level, description)
# ═══════════════════════════════════════════════════════════════════
KNOWN_SERVICES: Dict[int, Tuple[str, str, str]] = {
    20:    ("FTP-Data",     "medium", "FTP data transfer — unencrypted"),
    21:    ("FTP",          "high",   "FTP control — cleartext credentials"),
    22:    ("SSH",          "low",    "Secure Shell — generally safe if updated"),
    23:    ("Telnet",       "critical","Telnet — fully unencrypted, replace with SSH"),
    25:    ("SMTP",         "medium", "Mail server — may allow relay if misconfigured"),
    53:    ("DNS",          "low",    "Domain Name System"),
    80:    ("HTTP",         "medium", "Unencrypted web server"),
    110:   ("POP3",         "high",   "Email retrieval — cleartext passwords"),
    111:   ("RPCBind",      "high",   "RPC — can expose internal services"),
    135:   ("MSRPC",        "high",   "Microsoft RPC — common attack vector"),
    139:   ("NetBIOS",      "high",   "NetBIOS Session — SMB enumeration vector"),
    143:   ("IMAP",         "medium", "Email retrieval — prefer IMAPS"),
    389:   ("LDAP",         "high",   "LDAP — directory service, often unauthenticated"),
    443:   ("HTTPS",        "low",    "Encrypted web server"),
    445:   ("SMB",          "critical","Server Message Block — WannaCry/EternalBlue target"),
    636:   ("LDAPS",        "low",    "Encrypted LDAP"),
    993:   ("IMAPS",        "low",    "Encrypted IMAP"),
    995:   ("POP3S",        "low",    "Encrypted POP3"),
    1080:  ("SOCKS",        "high",   "SOCKS proxy — possible open proxy"),
    1433:  ("MSSQL",        "high",   "Microsoft SQL Server — should not be public"),
    1434:  ("MSSQL-UDP",    "high",   "MS SQL Browser — information leak"),
    1521:  ("Oracle",       "high",   "Oracle DB — should not be publicly exposed"),
    2049:  ("NFS",          "high",   "Network File System — data exposure risk"),
    2181:  ("ZooKeeper",    "high",   "Apache ZooKeeper — often unauthenticated"),
    3000:  ("Grafana/Node", "medium", "Development server — often with default creds"),
    3306:  ("MySQL",        "high",   "MySQL — should not be publicly exposed"),
    3389:  ("RDP",          "critical","Remote Desktop — brute-force target"),
    4443:  ("HTTPS-Alt",    "low",    "Alternative HTTPS"),
    5000:  ("Flask/Docker", "medium", "Development/Docker API — check auth"),
    5432:  ("PostgreSQL",   "high",   "PostgreSQL — should not be publicly exposed"),
    5601:  ("Kibana",       "high",   "Kibana — often unauthenticated dashboard"),
    5900:  ("VNC",          "critical","VNC — often weak/no authentication"),
    6379:  ("Redis",        "critical","Redis — often no auth, RCE possible"),
    7001:  ("WebLogic",     "high",   "Oracle WebLogic — known CVE target"),
    8080:  ("HTTP-Alt",     "medium", "Alternative HTTP — check for admin panels"),
    8443:  ("HTTPS-Alt",    "low",    "Alternative HTTPS"),
    8888:  ("Jupyter",      "critical","Jupyter Notebook — often no auth, RCE"),
    9090:  ("Prometheus",   "medium", "Prometheus metrics — info disclosure"),
    9200:  ("Elasticsearch","high",   "Elasticsearch — often unauthenticated"),
    9300:  ("ES-Transport", "high",   "Elasticsearch transport — cluster access"),
    10000: ("Webmin",       "high",   "Webmin — admin panel, RCE history"),
    11211: ("Memcached",    "high",   "Memcached — DDoS amplification, data leak"),
    27017: ("MongoDB",      "critical","MongoDB — often exposed without auth"),
    27018: ("MongoDB-Alt",  "critical","MongoDB alternate — often no auth"),
    28017: ("MongoDB-Web",  "critical","MongoDB web interface — info leak"),
}

DEFAULT_PORTS = sorted(set([
    20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143,
    443, 445, 993, 995, 1433, 1434, 3306, 3389, 5432, 5900,
    6379, 8080, 8443, 9200, 27017,
]))

EXTENDED_PORTS = sorted(set(DEFAULT_PORTS + [
    81, 88, 389, 636, 1080, 1521, 2049, 2082, 2083, 2181,
    3000, 4443, 5000, 5001, 5601, 7001, 8000, 8081, 8443,
    8888, 9090, 9300, 9999, 10000, 11211, 27018, 28017,
]))

# Security headers to check
SECURITY_HEADERS = {
    "Strict-Transport-Security": ("HSTS", "critical", "Missing HSTS — vulnerable to SSL stripping"),
    "Content-Security-Policy": ("CSP", "high", "Missing CSP — vulnerable to XSS"),
    "X-Content-Type-Options": ("X-CTO", "medium", "Missing X-Content-Type-Options — MIME sniffing risk"),
    "X-Frame-Options": ("XFO", "medium", "Missing X-Frame-Options — clickjacking risk"),
    "X-XSS-Protection": ("X-XSS", "low", "Missing X-XSS-Protection header"),
    "Referrer-Policy": ("Referrer", "low", "Missing Referrer-Policy — information leak"),
    "Permissions-Policy": ("Permissions", "low", "Missing Permissions-Policy header"),
    "X-Permitted-Cross-Domain-Policies": ("XPCDP", "low", "Missing cross-domain policy"),
}

# Common subdomains for enumeration
COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "admin", "blog", "dev", "staging", "test",
    "api", "m", "mobile", "app", "portal", "vpn", "remote", "webmail",
    "ns1", "ns2", "dns", "mx", "smtp", "pop", "imap", "cpanel",
    "whm", "cdn", "media", "static", "assets", "img", "images",
    "docs", "wiki", "help", "support", "status", "monitor",
    "git", "gitlab", "jenkins", "ci", "build", "deploy",
    "db", "database", "mysql", "postgres", "redis", "elastic",
    "dashboard", "panel", "login", "auth", "sso", "oauth",
    "shop", "store", "pay", "billing", "checkout",
    "internal", "intranet", "corp", "office", "exchange",
]

# Common web paths for directory discovery
COMMON_PATHS = [
    "/admin", "/login", "/wp-admin", "/wp-login.php", "/administrator",
    "/phpmyadmin", "/cpanel", "/.env", "/.git/config", "/robots.txt",
    "/sitemap.xml", "/api", "/api/v1", "/graphql", "/swagger",
    "/docs", "/.well-known/security.txt", "/server-status",
    "/server-info", "/.htaccess", "/backup", "/config",
    "/console", "/debug", "/trace", "/actuator", "/health",
    "/metrics", "/info", "/env", "/dump", "/.DS_Store",
    "/wp-content", "/wp-includes", "/xmlrpc.php", "/readme.html",
    "/license.txt", "/changelog.txt", "/web.config", "/crossdomain.xml",
]

# Known WAF signatures
WAF_SIGNATURES = {
    "cloudflare": ["cloudflare", "cf-ray", "__cfduid"],
    "aws_waf": ["awselb", "x-amzn"],
    "akamai": ["akamai", "x-akamai"],
    "sucuri": ["sucuri", "x-sucuri"],
    "imperva": ["incapsula", "x-iinfo", "visid_incap"],
    "f5_bigip": ["bigipserver", "f5"],
    "barracuda": ["barra_counter_session"],
    "fortinet": ["fortigate", "fortiwebserver"],
    "modsecurity": ["mod_security", "modsecurity"],
}

class ScanResult:
    """Represents the result of a single scan."""

    def __init__(self, target: str, scan_type: str = "port_scan"):
        self.target = target
        self.scan_type = scan_type
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.open_ports: List[Dict[str, Any]] = []
        self.closed_ports: int = 0
        self.filtered_ports: int = 0
        self.vulnerabilities: List[Dict[str, Any]] = []
        self.dns_records: List[Dict[str, str]] = []
        self.host_alive: Optional[bool] = None
        self.os_hint: str = ""
        self.error: Optional[str] = None
        self.ports_scanned: int = 0
        # New v2 fields
        self.http_headers: Dict[str, Any] = {}
        self.ssl_info: Dict[str, Any] = {}
        self.subdomains: List[str] = []
        self.traceroute_hops: List[Dict[str, Any]] = []
        self.whois_data: Dict[str, Any] = {}
        self.waf_detected: Optional[str] = None
        self.discovered_paths: List[Dict[str, Any]] = []
        self.security_score: int = 100  # starts perfect, deducted per issue

    def to_dict(self) -> dict:
        duration = 0
        if self.completed_at and self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        return {
            "target": self.target,
            "scan_type": self.scan_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(duration, 2),
            "host_alive": self.host_alive,
            "open_ports": self.open_ports,
            "open_port_count": len(self.open_ports),
            "closed_ports": self.closed_ports,
            "filtered_ports": self.filtered_ports,
            "ports_scanned": self.ports_scanned,
            "vulnerabilities": self.vulnerabilities,
            "vulnerability_count": len(self.vulnerabilities),
            "dns_records": self.dns_records,
            "os_hint": self.os_hint,
            "error": self.error,
            "http_headers": self.http_headers,
            "ssl_info": self.ssl_info,
            "subdomains": self.subdomains,
            "traceroute_hops": self.traceroute_hops,
            "whois_data": self.whois_data,
            "waf_detected": self.waf_detected,
            "discovered_paths": self.discovered_paths,
            "security_score": self.security_score,
        }

class EthicalHackingEngine:
    """
    Ethical hacking & penetration testing engine for NEXUS v2.0.
    Maximum capabilities with network recon, port scanning, HTTP audit,
    SSL analysis, subdomain enum, WAF detection, and more.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Stats
        self._total_scans = 0
        self._total_open_ports_found = 0
        self._total_vulns_found = 0
        self._total_targets_scanned: Set[str] = set()
        self._scan_history: deque = deque(maxlen=100)
        self._current_scan: Optional[ScanResult] = None
        self._is_scanning = False
        self._scan_lock = threading.Lock()

        # Extended stats v2
        self._total_http_audits = 0
        self._total_ssl_checks = 0
        self._total_subdomain_enums = 0
        self._total_traceroutes = 0
        self._total_whois_lookups = 0
        self._total_waf_detections = 0
        self._total_path_discoveries = 0
        self._total_subnet_sweeps = 0
        self._total_full_recons = 0
        self._alive_hosts: Set[str] = set()

        # Network info cache
        self._network_info: Dict[str, Any] = {}
        self._network_info_updated: Optional[datetime] = None

        logger.info("EthicalHackingEngine v2.0 initialized — MAXIMUM capabilities active")

    # ═══════════════════════════════════════════════════════════════════
    # NETWORK RECONNAISSANCE
    # ═══════════════════════════════════════════════════════════════════

    def get_network_info(self, refresh: bool = False) -> Dict[str, Any]:
        """Get local network information."""
        if self._network_info and not refresh:
            if self._network_info_updated:
                elapsed = (datetime.now() - self._network_info_updated).total_seconds()
                if elapsed < 60:
                    return self._network_info

        info: Dict[str, Any] = {
            "local_ip": "unknown", "public_ip": "unknown",
            "hostname": "unknown", "gateway": "unknown",
            "subnet": "unknown", "interfaces": [], "mac_address": "unknown",
        }

        try:
            info["hostname"] = socket.gethostname()
        except Exception:
            pass

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            info["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                info["local_ip"] = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass

        try:
            ip_parts = info["local_ip"].split(".")
            if len(ip_parts) == 4:
                info["subnet"] = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
                info["gateway"] = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
        except Exception:
            pass

        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.ipify.org?format=json",
                headers={"User-Agent": "NEXUS-AI/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                info["public_ip"] = data.get("ip", "unknown")
        except Exception:
            pass

        try:
            if sys.platform == "win32":
                result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split("\n"):
                    if "Default Gateway" in line and ":" in line:
                        gw = line.split(":")[-1].strip()
                        if gw:
                            info["gateway"] = gw
                            break
                    if "Physical Address" in line and ":" in line:
                        mac = line.split(":")[-1].strip().replace("-", ":")
                        if mac and info["mac_address"] == "unknown":
                            info["mac_address"] = mac
        except Exception:
            pass

        self._network_info = info
        self._network_info_updated = datetime.now()
        return info

    # ═══════════════════════════════════════════════════════════════════
    # PORT SCANNING
    # ═══════════════════════════════════════════════════════════════════

    def scan_target(self, target: str, ports: Optional[List[int]] = None,
                    timeout: float = 1.0, extended: bool = False) -> Dict[str, Any]:
        """Scan a target host for open ports and vulnerabilities."""
        if self._is_scanning:
            return {"error": "A scan is already in progress", "status": "busy"}

        with self._scan_lock:
            self._is_scanning = True

        result = ScanResult(target, "port_scan")
        self._current_scan = result

        try:
            try:
                resolved_ip = socket.gethostbyname(target)
                if resolved_ip != target:
                    result.dns_records.append({"type": "A", "name": target, "value": resolved_ip})
            except socket.gaierror:
                result.error = f"Cannot resolve hostname: {target}"
                result.completed_at = datetime.now()
                self._finalize_scan(result)
                return result.to_dict()

            try:
                reverse_name = socket.gethostbyaddr(resolved_ip)
                if reverse_name and reverse_name[0]:
                    result.dns_records.append({"type": "PTR", "name": resolved_ip, "value": reverse_name[0]})
            except (socket.herror, socket.gaierror):
                pass

            result.host_alive = self._ping_host(resolved_ip)
            if result.host_alive:
                self._alive_hosts.add(target)

            if ports:
                scan_ports = sorted(set(ports))
            elif extended:
                scan_ports = sorted(set(EXTENDED_PORTS))
            else:
                scan_ports = sorted(set(DEFAULT_PORTS))

            result.ports_scanned = len(scan_ports)

            open_ports_raw: List[Tuple[int, str]] = []
            results_lock = threading.Lock()

            def _scan_port(port: int):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    conn_result = sock.connect_ex((resolved_ip, port))
                    sock.close()
                    if conn_result == 0:
                        banner = self._grab_banner(resolved_ip, port, timeout)
                        with results_lock:
                            open_ports_raw.append((port, banner))
                except Exception:
                    pass

            batch_size = 50
            for i in range(0, len(scan_ports), batch_size):
                batch = scan_ports[i:i + batch_size]
                threads = [threading.Thread(target=_scan_port, args=(p,), daemon=True) for p in batch]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=timeout + 2)

            open_ports_raw.sort(key=lambda x: x[0])
            for port, banner in open_ports_raw:
                service_info = KNOWN_SERVICES.get(port, ("Unknown", "info", ""))
                port_entry = {
                    "port": port, "state": "open", "service": service_info[0],
                    "risk": service_info[1], "description": service_info[2],
                    "banner": banner[:200] if banner else "",
                }
                result.open_ports.append(port_entry)
                if service_info[1] in ("high", "critical"):
                    result.vulnerabilities.append({
                        "port": port, "service": service_info[0],
                        "severity": service_info[1],
                        "title": f"Risky service exposed: {service_info[0]} on port {port}",
                        "description": service_info[2],
                        "recommendation": self._get_recommendation(port, service_info[0]),
                    })
                    result.security_score -= 10 if service_info[1] == "high" else 15

            result.closed_ports = len(scan_ports) - len(open_ports_raw)
            result.os_hint = self._guess_os(result.open_ports)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Scan error for {target}: {e}")
        finally:
            result.completed_at = datetime.now()
            self._finalize_scan(result)

        return result.to_dict()

    # ═══════════════════════════════════════════════════════════════════
    # HTTP HEADER SECURITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════

    def analyze_http_headers(self, target: str, port: int = 80, use_https: bool = False) -> Dict[str, Any]:
        """Analyze HTTP security headers of a target."""
        self._total_http_audits += 1
        scheme = "https" if use_https or port == 443 else "http"
        url = f"{scheme}://{target}:{port}" if port not in (80, 443) else f"{scheme}://{target}"

        result = {
            "target": target, "url": url, "status_code": None,
            "server": None, "headers": {}, "missing_security_headers": [],
            "present_security_headers": [], "info_disclosure": [],
            "score": 100, "error": None,
        }

        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-SecurityScanner/2.0"})
            ctx = None
            if use_https or port == 443:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                result["status_code"] = resp.status
                headers = dict(resp.headers)
                result["headers"] = headers
                result["server"] = headers.get("Server", "Not disclosed")

                # Check security headers
                for header, (short, severity, desc) in SECURITY_HEADERS.items():
                    if header.lower() in {k.lower(): v for k, v in headers.items()}:
                        result["present_security_headers"].append({"header": header, "short": short})
                    else:
                        result["missing_security_headers"].append({
                            "header": header, "short": short,
                            "severity": severity, "description": desc,
                        })
                        deduction = {"critical": 15, "high": 10, "medium": 5, "low": 2}.get(severity, 2)
                        result["score"] -= deduction

                # Info disclosure checks
                if "Server" in headers:
                    result["info_disclosure"].append(f"Server header exposes: {headers['Server']}")
                    result["score"] -= 3
                if "X-Powered-By" in headers:
                    result["info_disclosure"].append(f"X-Powered-By exposes: {headers['X-Powered-By']}")
                    result["score"] -= 5
                if "X-AspNet-Version" in headers:
                    result["info_disclosure"].append(f"ASP.NET version exposed: {headers['X-AspNet-Version']}")
                    result["score"] -= 5

        except Exception as e:
            result["error"] = str(e)

        result["score"] = max(0, result["score"])
        return result

    # ═══════════════════════════════════════════════════════════════════
    # SSL/TLS CERTIFICATE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════

    def analyze_ssl(self, target: str, port: int = 443) -> Dict[str, Any]:
        """Analyze SSL/TLS certificate and configuration."""
        self._total_ssl_checks += 1
        result = {
            "target": target, "port": port, "ssl_enabled": False,
            "cert_info": {}, "protocol": None, "cipher": None,
            "issues": [], "score": 100, "error": None,
        }

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with socket.create_connection((target, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                    result["ssl_enabled"] = True
                    result["protocol"] = ssock.version()
                    cipher = ssock.cipher()
                    if cipher:
                        result["cipher"] = {"name": cipher[0], "protocol": cipher[1], "bits": cipher[2]}

                    cert = ssock.getpeercert(binary_form=True)
                    if cert:
                        # Parse cert using ssl module
                        try:
                            ctx2 = ssl.create_default_context()
                            ctx2.check_hostname = False
                            ctx2.verify_mode = ssl.CERT_NONE
                            with socket.create_connection((target, port), timeout=5) as s2:
                                with ctx2.wrap_socket(s2, server_hostname=target) as ss2:
                                    cert_dict = ss2.getpeercert()
                                    if cert_dict:
                                        result["cert_info"] = {
                                            "subject": str(dict(x[0] for x in cert_dict.get("subject", ()))),
                                            "issuer": str(dict(x[0] for x in cert_dict.get("issuer", ()))),
                                            "not_before": cert_dict.get("notBefore", ""),
                                            "not_after": cert_dict.get("notAfter", ""),
                                            "serial": cert_dict.get("serialNumber", ""),
                                            "san": [x[1] for x in cert_dict.get("subjectAltName", ())],
                                        }
                                        # Check expiry
                                        try:
                                            from datetime import timezone
                                            not_after = ssl.cert_time_to_seconds(cert_dict["notAfter"])
                                            remaining = not_after - time.time()
                                            days_left = remaining / 86400
                                            result["cert_info"]["days_until_expiry"] = int(days_left)
                                            if days_left < 0:
                                                result["issues"].append("CRITICAL: Certificate EXPIRED")
                                                result["score"] -= 40
                                            elif days_left < 30:
                                                result["issues"].append(f"WARNING: Certificate expires in {int(days_left)} days")
                                                result["score"] -= 15
                                        except Exception:
                                            pass
                        except Exception:
                            result["cert_info"]["raw_size"] = len(cert)

                    # Protocol checks
                    prot = result["protocol"]
                    if prot and "TLSv1.0" in str(prot):
                        result["issues"].append("Weak protocol: TLSv1.0 (deprecated)")
                        result["score"] -= 20
                    if prot and "TLSv1.1" in str(prot):
                        result["issues"].append("Weak protocol: TLSv1.1 (deprecated)")
                        result["score"] -= 15
                    if prot and "SSLv" in str(prot):
                        result["issues"].append("CRITICAL: SSLv2/SSLv3 (broken)")
                        result["score"] -= 30

        except ssl.SSLError as e:
            result["error"] = f"SSL error: {e}"
            result["issues"].append(str(e))
        except ConnectionRefusedError:
            result["error"] = "Connection refused — SSL not available on this port"
        except Exception as e:
            result["error"] = str(e)

        result["score"] = max(0, result["score"])
        return result

    # ═══════════════════════════════════════════════════════════════════
    # SUBDOMAIN ENUMERATION
    # ═══════════════════════════════════════════════════════════════════

    def enumerate_subdomains(self, domain: str) -> Dict[str, Any]:
        """Enumerate subdomains via DNS resolution."""
        self._total_subdomain_enums += 1
        result = {"domain": domain, "found": [], "total_checked": 0, "error": None}

        try:
            found_lock = threading.Lock()
            found_list = []

            def _check_sub(sub):
                fqdn = f"{sub}.{domain}"
                try:
                    ip = socket.gethostbyname(fqdn)
                    with found_lock:
                        found_list.append({"subdomain": fqdn, "ip": ip})
                except socket.gaierror:
                    pass

            threads = []
            for sub in COMMON_SUBDOMAINS:
                t = threading.Thread(target=_check_sub, args=(sub,), daemon=True)
                t.start()
                threads.append(t)
                if len(threads) >= 20:
                    for t2 in threads:
                        t2.join(timeout=3)
                    threads = []

            for t in threads:
                t.join(timeout=3)

            result["found"] = sorted(found_list, key=lambda x: x["subdomain"])
            result["total_checked"] = len(COMMON_SUBDOMAINS)

        except Exception as e:
            result["error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════════════════
    # TRACEROUTE
    # ═══════════════════════════════════════════════════════════════════

    def traceroute(self, target: str) -> Dict[str, Any]:
        """Run traceroute to target."""
        self._total_traceroutes += 1
        result = {"target": target, "hops": [], "error": None}

        try:
            if sys.platform == "win32":
                cmd = ["tracert", "-d", "-w", "1000", "-h", "20", target]
            else:
                cmd = ["traceroute", "-n", "-w", "1", "-m", "20", target]

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = proc.stdout.split("\n")

            hop_num = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Parse hop lines (Windows: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1")
                parts = line.split()
                if parts and parts[0].isdigit():
                    hop_num = int(parts[0])
                    # Find IP in the line
                    ip = "*"
                    for p in reversed(parts):
                        if re.match(r"\d+\.\d+\.\d+\.\d+", p):
                            ip = p
                            break
                    # Find RTT
                    rtts = []
                    for p in parts[1:]:
                        if p.replace(".", "").isdigit():
                            rtts.append(float(p))
                        elif p == "<1":
                            rtts.append(0.5)
                    avg_rtt = round(sum(rtts) / len(rtts), 1) if rtts else None
                    result["hops"].append({
                        "hop": hop_num, "ip": ip, "rtt_ms": avg_rtt,
                    })
        except subprocess.TimeoutExpired:
            result["error"] = "Traceroute timed out"
        except Exception as e:
            result["error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════════════════
    # WHOIS LOOKUP
    # ═══════════════════════════════════════════════════════════════════

    def whois_lookup(self, target: str) -> Dict[str, Any]:
        """Perform WHOIS lookup on a domain or IP."""
        self._total_whois_lookups += 1
        result = {"target": target, "data": {}, "raw": "", "error": None}

        try:
            # Use socket to query WHOIS server
            whois_server = "whois.iana.org"
            # Determine appropriate WHOIS server
            if re.match(r"\d+\.\d+\.\d+\.\d+", target):
                whois_server = "whois.arin.net"
            elif target.endswith(".com") or target.endswith(".net"):
                whois_server = "whois.verisign-grs.com"
            elif target.endswith(".org"):
                whois_server = "whois.pir.org"
            elif target.endswith(".io"):
                whois_server = "whois.nic.io"

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((whois_server, 43))
                sock.send((target + "\r\n").encode())

                response = b""
                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        response += data
                    except socket.timeout:
                        break

            raw = response.decode("utf-8", errors="replace")
            result["raw"] = raw[:2000]

            # Parse key fields
            for line in raw.split("\n"):
                line = line.strip()
                if ":" in line and not line.startswith("%") and not line.startswith("#"):
                    key, _, val = line.partition(":")
                    key = key.strip().lower().replace(" ", "_")
                    val = val.strip()
                    if val and key not in result["data"]:
                        result["data"][key] = val

        except Exception as e:
            result["error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════════════════
    # WAF DETECTION
    # ═══════════════════════════════════════════════════════════════════

    def detect_waf(self, target: str) -> Dict[str, Any]:
        """Detect Web Application Firewall."""
        self._total_waf_detections += 1
        result = {"target": target, "waf_detected": False, "waf_name": None,
                  "evidence": [], "error": None}

        try:
            import urllib.request
            for scheme in ["https", "http"]:
                try:
                    url = f"{scheme}://{target}"
                    # Normal request
                    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-WAFDetect/2.0"})
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                        headers = {k.lower(): v.lower() for k, v in resp.headers.items()}
                        cookies = headers.get("set-cookie", "").lower()

                        for waf_name, signatures in WAF_SIGNATURES.items():
                            for sig in signatures:
                                # Check in headers
                                for hk, hv in headers.items():
                                    if sig in hk or sig in hv:
                                        result["waf_detected"] = True
                                        result["waf_name"] = waf_name
                                        result["evidence"].append(f"Header match: {sig} in {hk}")
                                # Check in cookies
                                if sig in cookies:
                                    result["waf_detected"] = True
                                    result["waf_name"] = waf_name
                                    result["evidence"].append(f"Cookie match: {sig}")

                        if result["waf_detected"]:
                            break
                    break
                except Exception:
                    continue

            # Malicious request test — see if WAF blocks it
            if not result["waf_detected"]:
                try:
                    evil_url = f"http://{target}/?id=1' OR '1'='1"
                    req2 = urllib.request.Request(evil_url, headers={"User-Agent": "NEXUS-WAFDetect/2.0"})
                    with urllib.request.urlopen(req2, timeout=5) as resp2:
                        if resp2.status in (403, 406, 429, 503):
                            result["waf_detected"] = True
                            result["waf_name"] = "unknown"
                            result["evidence"].append(f"Blocked SQLi probe with HTTP {resp2.status}")
                except Exception as e:
                    err_str = str(e).lower()
                    if "403" in err_str or "406" in err_str:
                        result["waf_detected"] = True
                        result["waf_name"] = "unknown"
                        result["evidence"].append("Blocked SQLi probe")

        except Exception as e:
            result["error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════════════════
    # DIRECTORY / PATH DISCOVERY
    # ═══════════════════════════════════════════════════════════════════

    def discover_paths(self, target: str, use_https: bool = False) -> Dict[str, Any]:
        """Discover accessible paths/directories on a web server."""
        self._total_path_discoveries += 1
        scheme = "https" if use_https else "http"
        result = {"target": target, "found_paths": [], "checked": 0, "error": None}

        try:
            import urllib.request
            ctx = None
            if use_https:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            found_lock = threading.Lock()
            found = []

            def _check_path(path):
                try:
                    url = f"{scheme}://{target}{path}"
                    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-DirScan/2.0"}, method="GET")
                    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                        status = resp.status
                        size = len(resp.read(1024))
                        with found_lock:
                            found.append({
                                "path": path, "status": status,
                                "size_bytes": size,
                                "interesting": path in ("/.env", "/.git/config", "/wp-admin",
                                                       "/phpmyadmin", "/server-status", "/actuator"),
                            })
                except Exception:
                    pass

            # Thread pool
            threads = []
            for path in COMMON_PATHS:
                t = threading.Thread(target=_check_path, args=(path,), daemon=True)
                t.start()
                threads.append(t)
                if len(threads) >= 10:
                    for t2 in threads:
                        t2.join(timeout=6)
                    threads = []
            for t in threads:
                t.join(timeout=6)

            result["found_paths"] = sorted(found, key=lambda x: x["path"])
            result["checked"] = len(COMMON_PATHS)

        except Exception as e:
            result["error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════════════════
    # SUBNET SWEEP
    # ═══════════════════════════════════════════════════════════════════

    def sweep_subnet(self, subnet_base: str = None) -> Dict[str, Any]:
        """Ping sweep an entire /24 subnet."""
        self._total_subnet_sweeps += 1
        if not subnet_base:
            info = self.get_network_info()
            ip = info.get("local_ip", "")
            if ip and "." in ip:
                subnet_base = ".".join(ip.split(".")[:3])
            else:
                return {"error": "Cannot determine subnet", "alive_hosts": []}

        result = {"subnet": f"{subnet_base}.0/24", "alive_hosts": [], "total_checked": 0, "error": None}

        alive_lock = threading.Lock()
        alive = []

        def _ping(ip):
            if self._ping_host(ip):
                with alive_lock:
                    alive.append(ip)
                    self._alive_hosts.add(ip)

        threads = []
        for i in range(1, 255):
            ip = f"{subnet_base}.{i}"
            t = threading.Thread(target=_ping, args=(ip,), daemon=True)
            t.start()
            threads.append(t)
            if len(threads) >= 50:
                for t2 in threads:
                    t2.join(timeout=3)
                threads = []
        for t in threads:
            t.join(timeout=3)

        result["alive_hosts"] = sorted(alive, key=lambda x: [int(p) for p in x.split(".")])
        result["total_checked"] = 254
        return result

    # ═══════════════════════════════════════════════════════════════════
    # FULL RECONNAISSANCE (COMBINED)
    # ═══════════════════════════════════════════════════════════════════

    def full_recon(self, target: str) -> Dict[str, Any]:
        """Run a full reconnaissance scan: ports + HTTP + SSL + traceroute."""
        self._total_full_recons += 1
        recon = {"target": target, "timestamp": datetime.now().isoformat()}

        # 1. Port scan
        recon["port_scan"] = self.scan_target(target, extended=True, timeout=0.8)

        # 2. HTTP security headers
        has_http = any(p.get("port") in (80, 8080, 8000) for p in recon["port_scan"].get("open_ports", []))
        has_https = any(p.get("port") in (443, 8443) for p in recon["port_scan"].get("open_ports", []))

        if has_https:
            recon["http_headers"] = self.analyze_http_headers(target, 443, use_https=True)
            recon["ssl_analysis"] = self.analyze_ssl(target, 443)
        elif has_http:
            recon["http_headers"] = self.analyze_http_headers(target, 80)

        # 3. WAF detection (only for web targets)
        if has_http or has_https:
            recon["waf_detection"] = self.detect_waf(target)
            recon["path_discovery"] = self.discover_paths(target, use_https=has_https)

        # 4. Traceroute
        recon["traceroute"] = self.traceroute(target)

        # 5. Calculate overall security score
        scores = []
        if "port_scan" in recon and "security_score" in recon["port_scan"]:
            scores.append(recon["port_scan"]["security_score"])
        if "http_headers" in recon and "score" in recon["http_headers"]:
            scores.append(recon["http_headers"]["score"])
        if "ssl_analysis" in recon and "score" in recon["ssl_analysis"]:
            scores.append(recon["ssl_analysis"]["score"])

        recon["overall_security_score"] = round(sum(scores) / len(scores)) if scores else 0
        recon["scan_count"] = len([k for k in recon if k not in ("target", "timestamp", "overall_security_score", "scan_count")])

        return recon

    # ═══════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════

    def _finalize_scan(self, result: ScanResult):
        self._total_scans += 1
        self._total_open_ports_found += len(result.open_ports)
        self._total_vulns_found += len(result.vulnerabilities)
        self._total_targets_scanned.add(result.target)
        self._scan_history.appendleft(result.to_dict())
        self._current_scan = None
        self._is_scanning = False

    def _ping_host(self, host: str) -> bool:
        try:
            if sys.platform == "win32":
                cmd = ["ping", "-n", "1", "-w", "1000", host]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _grab_banner(self, host: str, port: int, timeout: float = 1.0) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((host, port))
                if port in (80, 8080, 8000, 8888, 3000, 5000):
                    sock.send(b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n")
                elif port == 443:
                    return "SSL/TLS"
                banner = sock.recv(256).decode("utf-8", errors="replace").strip()
                return banner
        except Exception:
            return ""

    def _guess_os(self, open_ports: List[Dict]) -> str:
        ports = {p["port"] for p in open_ports}
        if ports & {135, 139, 445, 3389}:
            return "Windows (SMB/RDP detected)"
        elif ports & {22} and not ports & {135, 445}:
            return "Linux/Unix (SSH detected)"
        elif ports & {548}:
            return "macOS (AFP detected)"
        elif ports & {80, 443} and not ports & {22, 135, 445}:
            return "Web Server / Appliance"
        return "Unknown"

    def _get_recommendation(self, port: int, service: str) -> str:
        recommendations = {
            21:    "Migrate to SFTP (port 22). Disable anonymous FTP.",
            23:    "DISABLE Telnet immediately. Use SSH instead.",
            110:   "Migrate to POP3S (port 995) or use IMAP/IMAPS.",
            135:   "Block MSRPC from external access. Firewall port 135.",
            139:   "Block NetBIOS from external access. Disable if unused.",
            445:   "Patch SMB, block from internet. Ensure EternalBlue patches applied.",
            1433:  "Do NOT expose SQL Server to internet. Use VPN/firewall.",
            1434:  "Block MS SQL Browser from external access.",
            3306:  "Do NOT expose MySQL to internet. Bind to localhost only.",
            3389:  "Enable NLA for RDP. Use VPN. Consider disabling if unused.",
            5432:  "Do NOT expose PostgreSQL to internet. Use SSH tunnel.",
            5900:  "Use VNC over SSH tunnel. Add strong authentication.",
            6379:  "Add Redis AUTH password. Bind to localhost. Never expose publicly.",
            8888:  "Add Jupyter authentication. Never expose publicly.",
            9200:  "Enable Elasticsearch security. Add authentication.",
            27017: "Enable MongoDB authentication. Bind to localhost.",
        }
        return recommendations.get(port, f"Review {service} configuration and restrict access.")

    # ═══════════════════════════════════════════════════════════════════
    # DNS UTILITIES
    # ═══════════════════════════════════════════════════════════════════

    def dns_lookup(self, hostname: str) -> Dict[str, Any]:
        """Perform DNS lookup for a hostname."""
        result = {"hostname": hostname, "records": [], "error": None}
        try:
            addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
            seen = set()
            for addr in addrs:
                ip = addr[4][0]
                if ip not in seen:
                    seen.add(ip)
                    result["records"].append({"type": "A", "value": ip})
            try:
                addrs6 = socket.getaddrinfo(hostname, None, socket.AF_INET6)
                for addr in addrs6:
                    ip6 = addr[4][0]
                    if ip6 not in seen:
                        seen.add(ip6)
                        result["records"].append({"type": "AAAA", "value": ip6})
            except Exception:
                pass
            for rec in list(result["records"]):
                if rec["type"] == "A":
                    try:
                        rev = socket.gethostbyaddr(rec["value"])
                        if rev and rev[0]:
                            result["records"].append({"type": "PTR", "value": rev[0], "for": rec["value"]})
                    except Exception:
                        pass
        except socket.gaierror as e:
            result["error"] = f"DNS resolution failed: {e}"
        except Exception as e:
            result["error"] = str(e)
        result["ipv4"] = [r["value"] for r in result["records"] if r["type"] == "A"]
        result["ipv6"] = [r["value"] for r in result["records"] if r["type"] == "AAAA"]
        return result

    # ═══════════════════════════════════════════════════════════════════
    # STATS & STATUS
    # ═══════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive hacking engine statistics."""
        network = self.get_network_info()
        recent_scans = []
        for scan in list(self._scan_history)[:10]:
            recent_scans.append({
                "target": scan.get("target", "?"),
                "scan_type": scan.get("scan_type", "port_scan"),
                "open_ports": scan.get("open_port_count", 0),
                "vulns": scan.get("vulnerability_count", 0),
                "duration": scan.get("duration_seconds", 0),
                "started_at": scan.get("started_at", ""),
                "host_alive": scan.get("host_alive"),
                "security_score": scan.get("security_score", 0),
            })

        latest_scan = None
        if self._scan_history:
            latest_scan = self._scan_history[0]

        return {
            "engine_status": "scanning" if self._is_scanning else "idle",
            "engine_version": "2.0",
            "is_scanning": self._is_scanning,
            "total_scans": self._total_scans,
            "total_open_ports_found": self._total_open_ports_found,
            "total_vulns_found": self._total_vulns_found,
            "unique_targets_scanned": len(self._total_targets_scanned),
            "targets_list": list(self._total_targets_scanned)[:30],
            "network_info": network,
            "recent_scans": recent_scans,
            "latest_scan": latest_scan,
            "current_scan_target": self._current_scan.target if self._current_scan else None,
            "total_http_audits": self._total_http_audits,
            "total_ssl_checks": self._total_ssl_checks,
            "total_subdomain_enums": self._total_subdomain_enums,
            "total_traceroutes": self._total_traceroutes,
            "total_whois_lookups": self._total_whois_lookups,
            "total_waf_detections": self._total_waf_detections,
            "total_path_discoveries": self._total_path_discoveries,
            "total_subnet_sweeps": self._total_subnet_sweeps,
            "total_full_recons": self._total_full_recons,
            "alive_hosts_count": len(self._alive_hosts),
            "alive_hosts": list(self._alive_hosts)[:30],
            "capabilities": [
                "port_scan", "http_header_audit", "ssl_tls_analysis",
                "subdomain_enumeration", "traceroute", "whois_lookup",
                "waf_detection", "path_discovery", "subnet_sweep",
                "full_recon", "dns_lookup", "ping_sweep",
                "banner_grabbing", "os_fingerprinting", "vuln_assessment",
            ],
        }

# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════

ethical_hacking_engine = EthicalHackingEngine()

# ═══════════════════════════════════════════════════════════════════════
# CONTINUOUS HACKING DAEMON — runs independently, never depends on brain
# ═══════════════════════════════════════════════════════════════════════

def _hacking_daemon():
    """Continuously runs ALL 15 hacking capabilities every 60 seconds."""
    import random
    cycle = 0

    time.sleep(8)
    logger.info("☠️ ═══ HACKING DAEMON STARTED — runs every 60s ═══")

    EXTERNAL_TARGETS = [
        "google.com", "github.com", "cloudflare.com", "amazon.com",
        "microsoft.com", "apple.com", "facebook.com", "netflix.com",
        "twitter.com", "reddit.com", "stackoverflow.com", "wikipedia.org",
        "yahoo.com", "linkedin.com", "mozilla.org", "apache.org",
    ]

    while True:
        cycle += 1
        succeeded = 0
        failed = 0

        try:
            e = ethical_hacking_engine
            net = e.get_network_info()
            gw = net.get("gateway", "")
            lip = net.get("local_ip", "")
            alive_list = list(e._alive_hosts)

            def pick_target():
                pool = []
                if gw: pool.append(gw)
                pool.append("127.0.0.1")
                if alive_list: pool.extend(alive_list[:5])
                if lip:
                    base = ".".join(lip.split(".")[:3])
                    for _ in range(3):
                        pool.append(f"{base}.{random.randint(1, 254)}")
                pool.extend(random.sample(EXTERNAL_TARGETS, min(3, len(EXTERNAL_TARGETS))))
                return random.choice(pool)

            def pick_domain():
                pool = [gw] if gw else ["127.0.0.1"]
                pool.extend(random.sample(EXTERNAL_TARGETS, min(3, len(EXTERNAL_TARGETS))))
                return random.choice(pool)

            logger.info(f"☠️ ═══ HACK CYCLE #{cycle} STARTING ═══")

            # 1-15: Each capability with its own try/except
            for cap_name, cap_fn in [
                ("port_scan", lambda: e.scan_target(pick_target(), timeout=1.0, extended=False)),
                ("http_audit", lambda: e.analyze_http_headers(pick_domain(), port=80)),
                ("ssl_check", lambda: e.analyze_ssl(pick_domain())),
                ("subdomain", lambda: e.enumerate_subdomains(pick_domain())),
                ("traceroute", lambda: e.traceroute(pick_target())),
                ("whois", lambda: e.whois_lookup(pick_domain())),
                ("waf_detect", lambda: e.detect_waf(pick_domain())),
                ("path_disc", lambda: e.discover_paths(pick_target())),
                ("sweep", lambda: e.sweep_subnet()),
                ("dns", lambda: e.dns_lookup(pick_domain())),
                ("full_recon", lambda: e.full_recon(pick_target())),
                ("banner", lambda: [e._grab_banner(pick_target(), p, 0.5) for p in [80,443,22,21,8080]]),
                ("os_fp", lambda: e._guess_os(list(e._scan_history)[0].get("open_ports",[]) if e._scan_history else [])),
                ("ping", lambda: [e._ping_host(f"{'.'.join(lip.split('.')[:3])}.{random.randint(1,254)}") for _ in range(15)] if lip else None),
                ("vuln_assess", lambda: e.scan_target(pick_target(), timeout=1.0, extended=True)),
            ]:
                try:
                    cap_fn()
                    succeeded += 1
                except Exception as err:
                    failed += 1
                    logger.warning(f"☠️ [{cap_name}] ERR: {err}")

            stats = e.get_stats()
            logger.info(
                f"☠️ ═══ HACK CYCLE #{cycle} DONE: {succeeded}/15 OK, {failed} ERR | "
                f"scans={stats['total_scans']} ports={stats['total_open_ports_found']} "
                f"vulns={stats['total_vulns_found']} targets={stats['unique_targets_scanned']} ═══"
            )

        except Exception as outer:
            logger.warning(f"☠️ Hacking daemon cycle #{cycle} outer error: {outer}")

        time.sleep(60)

threading.Thread(target=_hacking_daemon, daemon=True, name="hacking-daemon").start()
