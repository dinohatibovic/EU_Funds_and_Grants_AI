#!/usr/bin/env python3
import os
import sys
import re
import json
import hashlib
import logging
import urllib.request
import urllib.error
from typing import Set, Dict, Any, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnterpriseAuditor")

RENDER_URL = "https://eu-funds-and-grants-ai.onrender.com"
LOCAL_DATA_PATH = "data/grants.json"

class SystemAuditor:
    def __init__(self, base_url: str, local_data: str):
        self.base_url = base_url.rstrip('/')
        self.local_data = local_data
        self.has_failures = False

    def flag_failure(self, message: str):
        logger.error(message)
        self.has_failures = True

    def fetch_json(self, url: str) -> Tuple[Any, Dict[str, str]]:
        try:
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "DevOps-Audit-Engine/3.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                headers = {k.lower(): v for k, v in response.getheaders()}
                return json.loads(response.read().decode("utf-8")), headers
        except Exception as e:
            self.flag_failure(f"Network error on {url}: {str(e)}")
            return None, {}

    def audit_runtime_health(self) -> str:
        logger.info("Starting Phase 1: Production Infrastructure Metrics Audit...")
        data, _ = self.fetch_json(f"{self.base_url}/health")
        if not data:
            self.flag_failure("Critical infrastructure component missing: Health endpoint unreachable.")
            return "unknown"

        version = data.get("version", "N/A")
        db_status = data.get("database", "N/A")
        ai_engine = data.get("ai_engine", "N/A")
        total_grants = data.get("grants_total", 0)

        logger.info(f"   [METRIC] Production Engine Version: {version}")
        logger.info(f"   [METRIC] Vector/Relational Persistence Status: {db_status}")
        logger.info(f"   [METRIC] AI Core Engine Readiness: {ai_engine}")
        logger.info(f"   [METRIC] Isolated Production Document Pool: {total_grants}")

        if db_status != "connected":
            self.flag_failure("Persistence Layer Malfunction: Database unstable.")
        if ai_engine != "ready":
            self.flag_failure("AI Inference Engine Failure: Subsystem down.")
        if total_grants != 22:
            self.flag_failure(f"Payload Cardinality Drift: Found {total_grants} documents, expected 22.")
        return version

    def extract_remote_routes(self) -> Set[str]:
        logger.info("Starting Phase 2: Production Routing Topology Extraction...")
        data, _ = self.fetch_json(f"{self.base_url}/openapi.json")
        if not data or "paths" not in data:
            self.flag_failure("Routing Schema Extraction Failure.")
            return set()
        return set(data["paths"].keys())

    def extract_local_routes(self) -> Set[str]:
        logger.info("Starting Phase 3: Local Codebase Abstract Routing Synthesis...")
        local_routes = set()
        route_pattern = re.compile(r'@(?:app|router)\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']')

        for root, _, files in os.walk("."):
            if any(exclude in root for exclude in ["venv", ".git", "__pycache__"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    if file == "verify_sync.py":
                        continue
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as stream:
                            for line in stream:
                                match = route_pattern.search(line)
                                if match:
                                    local_routes.add(match.group(1))
                    except Exception:
                        pass
        return local_routes

    def verify_data_drift(self):
        logger.info("Starting Phase 4: Cryptographic Payload Drift Audit...")
        if not os.path.exists(self.local_data):
            self.flag_failure(f"Source Missing: Local file '{self.local_data}' not found.")
            return

        remote_payload, _ = self.fetch_json(f"{self.base_url}/grants")
        if not remote_payload:
            return

        try:
            with open(self.local_data, "r", encoding="utf-8") as stream:
                local_payload = json.load(stream)

            local_list = local_payload.get("grants", local_payload) if isinstance(local_payload, dict) else local_payload
            remote_list = remote_payload.get("grants", remote_payload) if isinstance(remote_payload, dict) else remote_payload

            local_serialized = json.dumps(local_list, sort_keys=True, ensure_ascii=False)
            remote_serialized = json.dumps(remote_list, sort_keys=True, ensure_ascii=False)

            local_hash = hashlib.sha256(local_serialized.encode("utf-8")).hexdigest()
            remote_hash = hashlib.sha256(remote_serialized.encode("utf-8")).hexdigest()

            if local_hash == remote_hash:
                logger.info("   [INTEGRITY] Cryptographic Match: Remote state matches local definition.")
            else:
                self.flag_failure("   [CRITICAL DRIFT] Content mismatch between Local and Production!")
                logger.error(f"      Local SHA-256:  {local_hash}")
                logger.error(f"      Remote SHA-256: {remote_hash}")
        except Exception as e:
            self.flag_failure(f"Data Drift Pipeline Aborted: {str(e)}")

    def audit_security_posture(self):
        logger.info("Starting Phase 5: Production Edge Security Configuration Audit...")
        _, headers = self.fetch_json(f"{self.base_url}/health")
        
        security_headers = {
            "strict-transport-security": "HSTS Missing: Transport layering vulnerable to MiTM.",
            "x-content-type-options": "X-Content-Type-Options Missing: Mime-sniffing hazard.",
            "x-frame-options": "X-Frame-Options Missing: Clickjacking surface exposed."
        }
        for header, failure_msg in security_headers.items():
            if header not in headers:
                logger.warning(f"   [SECURITY WARNING] {failure_msg}")

        try:
            req = urllib.request.Request(f"{self.base_url}/health") # Health endpoint is public, safe fallback test
            with urllib.request.urlopen(req, timeout=5):
                logger.info("   [SECURITY] Public availability validation successful.")
        except Exception:
            pass

    def run_all(self):
        print("=" * 80)
        logger.info("INITIATING SYSTEM ARCHITECTURE SYNCHRONIZATION RUN")
        print("=" * 80)

        self.audit_runtime_health()
        print("-" * 80)

        remote_r = self.extract_remote_routes()
        local_r = self.extract_local_routes()
        
        unreleased_routes = local_r - remote_r
        orphaned_routes = remote_r - local_r

        if not unreleased_routes and not orphaned_routes:
            logger.info("   🟢 Route Parity Check: Local structural matrix matches Production perfectly.")
        else:
            if unreleased_routes:
                self.flag_failure(f"   ⚠️  Unreleased Changes (Local only): {sorted(unreleased_routes)}")
            if orphaned_routes:
                self.flag_failure(f"   ⚠️  Divergent Drift (Production only): {sorted(orphaned_routes)}")

        print("-" * 80)
        self.verify_data_drift()
        print("-" * 80)
        self.audit_security_posture()
        print("=" * 80)

        if self.has_failures:
            logger.error("❌ CI/CD STATUS: BUILD FAILED. Deployment state out of sync.")
            sys.exit(1)
        else:
            logger.info("✅ CI/CD STATUS: SUCCESS. Environments synchronized.")
            sys.exit(0)

if __name__ == "__main__":
    auditor = SystemAuditor(base_url=RENDER_URL, local_data=LOCAL_DATA_PATH)
    auditor.run_all()
