"""Stage 3: RawResultParser (<= 70 LOC)"""
import re
from typing import List, Dict, Any

class RawResultParser:
    def parse(self, raw_output: str, tool_name: str) -> List[Dict[str, Any]]:
        results = []
        if "nmap" in tool_name.lower() or "PORT" in raw_output:
            for line in raw_output.splitlines():
                m = re.search(r"PORT\s+(\d+)/(\w+)\s+(\w+)\s+(\w+)", line)
                if m:
                    results.append({
                        "port": int(m.group(1)), "protocol": m.group(2),
                        "state": m.group(3), "service": m.group(4)
                    })
        else:
            results.append({"raw": raw_output.strip()})
        return results
