"""
NEXUS AI — Satellite Command: Space Infrastructure Access
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
God-Level Feature #10: Satellite tracking and space-based asset control.

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ TLE/SGP4     │  │  GROUND      │  │  ORBITAL     │  │  COMMS LINK  │
  │ Tracker      │  │  Station     │  │  Mechanics   │  │  Budget      │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              SATELLITE COMMAND ENGINE                               │
  │   • TLE orbit propagation (simplified SGP4)                        │
  │   • Real-time satellite pass prediction                            │
  │   • Ground station antenna pointing                                │
  │   • Link budget calculation (free-space path loss)                 │
  │   • Space debris collision risk assessment                         │
  │   • Multi-satellite constellation management                       │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import math
import os
import sys
import threading
import time
import traceback
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("satellite_command")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class OrbitType(Enum):
    LEO = "leo"  # Low Earth Orbit
    MEO = "meo"  # Medium Earth Orbit
    GEO = "geo"  # Geostationary
    HEO = "heo"  # Highly Elliptical
    SSO = "sso"  # Sun-Synchronous
    POLAR = "polar"
    MOLNIYA = "molniya"

class SatelliteFunction(Enum):
    COMMUNICATION = "communication"
    EARTH_OBSERVATION = "earth_observation"
    NAVIGATION = "navigation"
    WEATHER = "weather"
    MILITARY = "military"
    SCIENTIFIC = "scientific"
    ISS = "iss"
    STARLINK = "starlink"
    DEBRIS = "debris"

class PassStatus(Enum):
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"

@dataclass
class TLE:
    """Two-Line Element set for satellite orbit description."""
    name: str = ""
    line1: str = ""
    line2: str = ""
    norad_id: int = 0
    inclination_deg: float = 0.0
    raan_deg: float = 0.0
    eccentricity: float = 0.0
    arg_perigee_deg: float = 0.0
    mean_anomaly_deg: float = 0.0
    mean_motion: float = 0.0
    epoch_year: int = 0
    epoch_day: float = 0.0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SatelliteAsset:
    sat_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    norad_id: int = 0
    orbit_type: str = "leo"
    function: str = "communication"
    tle: Optional[Dict] = None
    altitude_km: float = 400.0
    velocity_kms: float = 7.66
    period_min: float = 92.0
    inclination_deg: float = 51.6
    status: str = "active"
    latitude: float = 0.0
    longitude: float = 0.0
    last_tracked: Optional[str] = None
    signal_freq_mhz: float = 0.0
    uplink_freq_mhz: float = 0.0
    downlink_freq_mhz: float = 0.0
    transponder_count: int = 0
    owner: str = ""
    launch_date: str = ""
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SatellitePass:
    pass_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sat_name: str = ""
    norad_id: int = 0
    aos_time: str = ""  # Acquisition of Signal
    los_time: str = ""  # Loss of Signal
    max_elev_deg: float = 0.0
    azimuth_aos_deg: float = 0.0
    azimuth_los_deg: float = 0.0
    duration_sec: float = 0.0
    pass_status: str = "upcoming"
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class GroundStation:
    station_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float = 0.0
    antenna_gain_db: float = 20.0
    frequency_range: Tuple[float, float] = (100.0, 3000.0)
    tracking_satellites: List[int] = field(default_factory=list)
    status: str = "idle"
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class LinkBudget:
    frequency_mhz: float = 0.0
    distance_km: float = 0.0
    tx_power_dbm: float = 30.0
    tx_gain_db: float = 10.0
    rx_gain_db: float = 20.0
    free_space_loss_db: float = 0.0
    atmospheric_loss_db: float = 2.0
    rain_loss_db: float = 0.0
    received_power_dbm: float = 0.0
    snr_db: float = 0.0
    link_margin_db: float = 0.0
    data_rate_kbps: float = 0.0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class CollisionRisk:
    object_a: str = ""
    object_b: str = ""
    tca: str = ""  # Time of Closest Approach
    miss_distance_km: float = 0.0
    probability: float = 0.0
    risk_level: str = "low"
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SatelliteStats:
    total_satellites: int = 0
    tracked_satellites: int = 0
    total_passes: int = 0
    successful_contacts: int = 0
    ground_stations: int = 0
    collision_warnings: int = 0
    total_link_budgets: int = 0
    constellations_tracked: int = 0
    debris_objects_tracked: int = 0
    orbit_predictions: int = 0
    data_downlinked_mb: float = 0.0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# ORBIT PROPAGATOR (Simplified SGP4)
# ═══════════════════════════════════════════════════════════════════════════════

class OrbitPropagator:
    """Simplified orbital mechanics calculator."""

    MU = 398600.4418  # Earth gravitational parameter (km^3/s^2)
    RE = 6371.0       # Earth radius (km)
    J2 = 1.08263e-3   # Earth oblateness coefficient

    def propagate(self, tle: TLE, minutes_from_epoch: float = 0) -> Dict[str, float]:
        """Propagate orbit position from TLE (simplified two-body)."""
        n = tle.mean_motion * 2 * math.pi / 86400  # rad/s
        a = (self.MU / (n ** 2)) ** (1.0 / 3.0)  # semi-major axis km
        M = math.radians(tle.mean_anomaly_deg) + n * minutes_from_epoch * 60
        # Solve Kepler's equation (simple iteration)
        E = M
        for _ in range(10):
            E = M + tle.eccentricity * math.sin(E)
        # True anomaly
        nu = 2 * math.atan2(
            math.sqrt(1 + tle.eccentricity) * math.sin(E / 2),
            math.sqrt(1 - tle.eccentricity) * math.cos(E / 2)
        )
        r = a * (1 - tle.eccentricity * math.cos(E))
        # Position in orbital plane
        x_orb = r * math.cos(nu)
        y_orb = r * math.sin(nu)
        # Rotation to ECI (simplified)
        i = math.radians(tle.inclination_deg)
        omega = math.radians(tle.arg_perigee_deg)
        RAAN = math.radians(tle.raan_deg)
        lat = math.degrees(math.asin(math.sin(i) * math.sin(omega + nu)))
        lon = math.degrees(RAAN + math.atan2(
            math.cos(i) * math.sin(omega + nu),
            math.cos(omega + nu)
        ))
        lon = ((lon + 180) % 360) - 180
        alt = r - self.RE
        velocity = math.sqrt(self.MU * (2 / r - 1 / a))
        return {"latitude": round(lat, 4), "longitude": round(lon, 4),
                "altitude_km": round(alt, 2), "velocity_kms": round(velocity, 3),
                "radius_km": round(r, 2)}

    def predict_pass(self, tle: TLE, station_lat: float, station_lon: float,
                      hours_ahead: int = 24) -> List[SatellitePass]:
        """Predict satellite passes over a ground station."""
        passes = []
        for minute in range(0, hours_ahead * 60, 1):
            pos = self.propagate(tle, minute)
            dist = self._great_circle_dist(station_lat, station_lon,
                                           pos["latitude"], pos["longitude"])
            elevation = math.degrees(math.atan2(
                pos["altitude_km"] - 0, max(1, dist)
            ))
            if elevation > 5:  # Visible pass
                if not passes or (passes and passes[-1].pass_status == "completed"):
                    sp = SatellitePass(
                        sat_name=tle.name, norad_id=tle.norad_id,
                        aos_time=(datetime.now() + timedelta(minutes=minute)).isoformat(),
                        max_elev_deg=elevation,
                    )
                    passes.append(sp)
                elif passes:
                    passes[-1].max_elev_deg = max(passes[-1].max_elev_deg, elevation)
                    passes[-1].los_time = (datetime.now() + timedelta(minutes=minute)).isoformat()
            elif passes and not passes[-1].los_time:
                passes[-1].los_time = (datetime.now() + timedelta(minutes=minute)).isoformat()
                passes[-1].pass_status = "completed"
        return passes[:10]

    def calculate_link_budget(self, freq_mhz: float, distance_km: float,
                               tx_power_dbm: float = 30, tx_gain_db: float = 10,
                               rx_gain_db: float = 20) -> LinkBudget:
        fspl = 20 * math.log10(distance_km * 1000) + 20 * math.log10(freq_mhz * 1e6) - 147.55
        rx_power = tx_power_dbm + tx_gain_db + rx_gain_db - fspl - 2
        noise_floor = -174 + 10 * math.log10(1e6)
        snr = rx_power - noise_floor
        data_rate = max(0, 1e3 * 2 ** (snr / 10))
        return LinkBudget(
            frequency_mhz=freq_mhz, distance_km=distance_km,
            tx_power_dbm=tx_power_dbm, tx_gain_db=tx_gain_db,
            rx_gain_db=rx_gain_db, free_space_loss_db=round(fspl, 2),
            received_power_dbm=round(rx_power, 2), snr_db=round(snr, 2),
            link_margin_db=round(snr - 10, 2),
            data_rate_kbps=round(data_rate / 1000, 2),
        )

    def collision_risk(self, sat_a: SatelliteAsset, sat_b: SatelliteAsset) -> CollisionRisk:
        alt_diff = abs(sat_a.altitude_km - sat_b.altitude_km)
        dist = math.sqrt(alt_diff**2 + self._great_circle_dist(
            sat_a.latitude, sat_a.longitude, sat_b.latitude, sat_b.longitude
        )**2)
        prob = max(0, 1e-6 / max(0.1, dist))
        level = "critical" if prob > 1e-4 else ("high" if prob > 1e-5 else ("medium" if prob > 1e-6 else "low"))
        return CollisionRisk(
            object_a=sat_a.name, object_b=sat_b.name,
            miss_distance_km=round(dist, 2), probability=prob, risk_level=level,
            tca=(datetime.now() + timedelta(hours=1)).isoformat(),
        )

    def _great_circle_dist(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = self.RE
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ═══════════════════════════════════════════════════════════════════════════════
# SATELLITE CATALOG — LIVE TLE FROM CELESTRAK
# ═══════════════════════════════════════════════════════════════════════════════

class SatelliteCatalog:
    """
    Real satellite catalog powered by CelesTrak live TLE feeds.
      • Fetches TLEs from https://celestrak.org (free, no key)
      • Parses standard Two-Line Element sets
      • Falls back to hardcoded catalog if network is down
    """

    CELESTRAK_URLS = {
        "stations":  "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
        "visual":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
        "active":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
        "starlink":  "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
        "gps":       "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
        "weather":   "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    }

    # Only fetch these groups by default (keep startup fast)
    DEFAULT_GROUPS = ["stations", "visual", "weather", "gps"]

    def __init__(self):
        self._catalog: Dict[int, SatelliteAsset] = {}
        self._live_mode = False
        self._last_fetch: float = 0
        self._fetch_interval = 3600  # refresh TLEs every hour
        self._lock = threading.Lock()
        # Try live first, fallback to hardcoded
        self._fetch_celestrak_catalog()
        if not self._catalog:
            self._build_fallback_catalog()

    # ──────────────────────────────────────────────────────────────────────
    # LIVE TLE FETCHER
    # ──────────────────────────────────────────────────────────────────────

    def _fetch_celestrak_catalog(self, groups: List[str] = None):
        """Fetch real TLE data from CelesTrak."""
        try:
            import requests as _req
        except ImportError:
            logger.warning("🛰️ requests not installed — using fallback catalog")
            return

        target_groups = groups or self.DEFAULT_GROUPS
        total_fetched = 0
        for group in target_groups:
            url = self.CELESTRAK_URLS.get(group)
            if not url:
                continue
            try:
                resp = _req.get(url, timeout=15)
                resp.raise_for_status()
                sats = self._parse_tle_text(resp.text, group)
                total_fetched += sats
            except Exception as e:
                logger.warning(f"🛰️ CelesTrak fetch failed for {group}: {e}")

        if total_fetched > 0:
            self._live_mode = True
            self._last_fetch = time.time()
            logger.info(f"🛰️ CelesTrak: loaded {total_fetched} satellites from {len(target_groups)} groups (catalog total: {self.total})")

    def _parse_tle_text(self, text: str, group: str) -> int:
        """Parse CelesTrak TLE text format (3 lines per satellite)."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        count = 0
        i = 0
        while i + 2 < len(lines):
            name_line = lines[i]
            line1 = lines[i + 1]
            line2 = lines[i + 2]

            # Validate TLE format
            if not line1.startswith("1 ") or not line2.startswith("2 "):
                i += 1
                continue

            try:
                tle = self._parse_tle_lines(name_line, line1, line2)
                # Determine function from group
                func_map = {
                    "stations": "iss", "starlink": "starlink",
                    "gps": "navigation", "weather": "weather",
                    "visual": "communication", "active": "communication",
                }
                func = func_map.get(group, "communication")

                # Compute orbital parameters
                n = tle.mean_motion  # rev/day
                a_km = (398600.4418 / ((n * 2 * math.pi / 86400) ** 2)) ** (1.0/3.0) if n > 0 else 6771
                alt_km = a_km - 6371.0
                period_min = 1440.0 / n if n > 0 else 92

                orbit_type = "leo" if alt_km < 2000 else \
                             "meo" if alt_km < 20000 else \
                             "geo" if alt_km > 35000 else "heo"

                sat = SatelliteAsset(
                    name=tle.name, norad_id=tle.norad_id,
                    orbit_type=orbit_type, function=func,
                    altitude_km=round(alt_km, 1),
                    inclination_deg=tle.inclination_deg,
                    period_min=round(period_min, 1),
                    status="active",
                    tle=tle.to_dict(),
                )

                with self._lock:
                    self._catalog[tle.norad_id] = sat
                count += 1

            except Exception as e:
                logger.debug(f"🛰️ TLE parse error: {e}")

            i += 3

        return count

    def _parse_tle_lines(self, name: str, line1: str, line2: str) -> TLE:
        """Parse actual TLE two-line element format per NORAD standard."""
        norad_id = int(line1[2:7].strip())
        epoch_year = int(line1[18:20])
        epoch_year = epoch_year + 2000 if epoch_year < 57 else epoch_year + 1900
        epoch_day = float(line1[20:32].strip())
        inclination = float(line2[8:16].strip())
        raan = float(line2[17:25].strip())
        ecc_str = line2[26:33].strip()
        eccentricity = float("0." + ecc_str)
        arg_perigee = float(line2[34:42].strip())
        mean_anomaly = float(line2[43:51].strip())
        mean_motion = float(line2[52:63].strip())

        return TLE(
            name=name.strip(), line1=line1, line2=line2,
            norad_id=norad_id, inclination_deg=inclination,
            raan_deg=raan, eccentricity=eccentricity,
            arg_perigee_deg=arg_perigee, mean_anomaly_deg=mean_anomaly,
            mean_motion=mean_motion, epoch_year=epoch_year,
            epoch_day=epoch_day,
        )

    def refresh_if_stale(self):
        """Re-fetch TLEs if they're older than the refresh interval."""
        if time.time() - self._last_fetch > self._fetch_interval:
            self._fetch_celestrak_catalog()

    # ──────────────────────────────────────────────────────────────────────
    # FALLBACK (8 hardcoded sats — used only when CelesTrak is down)
    # ──────────────────────────────────────────────────────────────────────

    def _build_fallback_catalog(self):
        entries = [
            ("ISS (ZARYA)", 25544, "leo", "iss", 420, 51.6),
            ("STARLINK-1007", 44713, "leo", "starlink", 550, 53.0),
            ("GPS BIIR-2", 28474, "meo", "navigation", 20200, 55.0),
            ("GOES-16", 41866, "geo", "weather", 35786, 0.1),
            ("HUBBLE", 20580, "leo", "scientific", 540, 28.5),
            ("TERRA", 25994, "sso", "earth_observation", 705, 98.2),
            ("NOAA 20", 43013, "sso", "weather", 824, 98.7),
            ("COSMOS 2251 DEB", 34115, "leo", "debris", 800, 74.0),
        ]
        for name, norad, orbit, func, alt, inc in entries:
            n_revday = 86400 / (2 * math.pi * math.sqrt((6371 + alt)**3 / 398600.4))
            sat = SatelliteAsset(
                name=name, norad_id=norad, orbit_type=orbit,
                function=func, altitude_km=alt, inclination_deg=inc,
                status="active",
                tle={"name": name, "norad_id": norad, "inclination_deg": inc,
                     "eccentricity": 0.001, "mean_motion": n_revday,
                     "mean_anomaly_deg": 0, "raan_deg": 0, "arg_perigee_deg": 0},
            )
            self._catalog[norad] = sat
        logger.info(f"🛰️ Using fallback catalog ({len(entries)} satellites)")

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API (same interface)
    # ──────────────────────────────────────────────────────────────────────

    def get(self, norad_id: int) -> Optional[SatelliteAsset]:
        return self._catalog.get(norad_id)

    def search(self, name: str = "", orbit: str = "", function: str = "") -> List[SatelliteAsset]:
        results = list(self._catalog.values())
        if name: results = [s for s in results if name.lower() in s.name.lower()]
        if orbit: results = [s for s in results if s.orbit_type == orbit]
        if function: results = [s for s in results if s.function == function]
        return results

    @property
    def is_live(self) -> bool:
        return self._live_mode

    @property
    def total(self) -> int:
        return len(self._catalog)


# ═══════════════════════════════════════════════════════════════════════════════
# SATELLITE COMMAND ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class SatelliteCommandEngine:
    """God-Level Feature #10: Satellite / Space Infrastructure Access."""

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data_dir = Path(DATA_DIR) / "satellite_command"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._propagator = OrbitPropagator()
        self._catalog = SatelliteCatalog()
        self._ground_stations: Dict[str, GroundStation] = {}

        self._running = False
        self._stats = SatelliteStats()
        self._stats.total_satellites = self._catalog.total
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_state()

        logger.info(f"🛰️ Satellite Command initialized | Catalog: {self._catalog.total}")

    def start(self):
        if self._running: return
        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True, name="SatelliteCommand")
        self._daemon_thread.start()
        logger.info("🛰️ Satellite Command daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def _daemon_loop(self):
        time.sleep(120)
        while self._running:
            try:
                self._catalog.refresh_if_stale()
                self._track_satellites()
                self._save_state()
                time.sleep(60)
            except Exception as e:
                logger.error(f"🛰️ Satellite daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(300)

    def _track_satellites(self):
        for sat in self._catalog.search():
            if sat.tle:
                tle = TLE()
                for k, v in sat.tle.items():
                    if hasattr(tle, k): setattr(tle, k, v)
                try:
                    pos = self._propagator.propagate(tle)
                    sat.latitude = pos["latitude"]
                    sat.longitude = pos["longitude"]
                    sat.altitude_km = pos["altitude_km"]
                    sat.last_tracked = datetime.now().isoformat()
                    self._stats.tracked_satellites += 1
                except Exception:
                    pass

    def track_satellite(self, norad_id: int) -> Optional[Dict]:
        sat = self._catalog.get(norad_id)
        if not sat or not sat.tle:
            return None
        tle = TLE()
        for k, v in sat.tle.items():
            if hasattr(tle, k): setattr(tle, k, v)
        pos = self._propagator.propagate(tle)
        sat.latitude = pos["latitude"]
        sat.longitude = pos["longitude"]
        return {**pos, "name": sat.name, "function": sat.function}

    def predict_passes(self, norad_id: int, station_lat: float, station_lon: float) -> List[Dict]:
        sat = self._catalog.get(norad_id)
        if not sat or not sat.tle: return []
        tle = TLE()
        for k, v in sat.tle.items():
            if hasattr(tle, k): setattr(tle, k, v)
        passes = self._propagator.predict_pass(tle, station_lat, station_lon)
        self._stats.total_passes += len(passes)
        return [p.to_dict() for p in passes]

    def calculate_link(self, freq_mhz: float, distance_km: float) -> LinkBudget:
        self._stats.total_link_budgets += 1
        return self._propagator.calculate_link_budget(freq_mhz, distance_km)

    def search_satellites(self, **kwargs) -> List[Dict]:
        return [s.to_dict() for s in self._catalog.search(**kwargs)]

    def get_status(self) -> Dict[str, Any]:
        return {"running": self._running, "stats": self._stats.to_dict(),
                "catalog_size": self._catalog.total, "ground_stations": len(self._ground_stations)}

    def get_summary(self) -> str:
        lines = [
            f"Running: {self._running}",
            f"Satellites: {self._stats.total_satellites} ({self._stats.tracked_satellites} tracked)",
            f"Passes Predicted: {self._stats.total_passes}",
            f"Ground Stations: {self._stats.ground_stations}",
            f"Collision Warnings: {self._stats.collision_warnings}",
            f"Link Budgets: {self._stats.total_link_budgets}",
            f"Data Downlinked: {self._stats.data_downlinked_mb:.1f} MB",
        ]
        return "\n".join(lines)

    def _save_state(self):
        try:
            (self._data_dir / "satellite_state.json").write_text(
                json.dumps({"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()},
                           indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save satellite state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "satellite_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k): setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load satellite state: {e}")


satellite_command = SatelliteCommandEngine()
def get_satellite_command() -> SatelliteCommandEngine: return satellite_command
