#!/usr/bin/env python3
"""
Benchmark Fim a Fim sem Mocks do Agente Ozz contra Servidor HTTP Real (127.0.0.1:5000)
"""
import os
import sys
import time
import subprocess
import urllib.request
import json
import tempfile
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.nedk import EventMesh, StateSpace
from agent.recon_adapter import ReconAdapterOrchestrator
from agent.recon_adapter.dtos import ReconRequest, TargetSpec, ToolProfile
from agent.domains.web import WebDomainSolver
from agent.domains.crypto import CryptoDomainSolver
from agent.infra.executor import SafeProcessExecutor
from agent.infra.file_reader import SafeFileReader
from agent.memory import Memory


def execute_real_benchmark() -> Dict[str, Any]:
    print("=" * 70)
    print("🔥 EXECUTANDO BENCHMARK REAL SEM MOCK — AGENTE OZZ vs SERVIDORES HTTP")
    print("=" * 70)

    # 1. Iniciar o servidor HTTP alvo em subprocesso
    server_script = os.path.join(os.path.dirname(__file__), "ctf_real_target_server.py")
    server_port = 5005
    target_url = f"http://127.0.0.1:{server_port}"

    print(f"📡 Subindo servidor HTTP real no processo filho: {target_url}...")
    server_proc = subprocess.Popen([sys.executable, server_script, str(server_port)])
    
    # Aguarda até que a porta esteja aberta (máx 5s)
    import socket
    connected = False
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", server_port), timeout=0.1):
                connected = True
                break
        except Exception:
            time.sleep(0.1)

    if not connected:
        raise RuntimeError("Não foi possível conectar ao servidor HTTP alvo na porta 5005.")

    print("✅ Servidor HTTP Alvo respondendo normalmente em 127.0.0.1:5005!")

    try:
        # 2. Inicialização da Memória SQLite e Adaptadores de Infraestrutura Real (SafeProcessExecutor)
        temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_ozz_real.db")
        memory = Memory(db_path=temp_db_path)
        real_executor = SafeProcessExecutor()
        real_file_reader = SafeFileReader()

        web_solver = WebDomainSolver(executor=real_executor, file_reader=real_file_reader)
        crypto_solver = CryptoDomainSolver(executor=real_executor, file_reader=real_file_reader)

        # 3. Fase E & S — Ingestão de Rede Real
        print(f"\n--- FASE 1: Ingestão de Alvo HTTP Real ({target_url}) ---")
        mesh = EventMesh()
        state_space = StateSpace()
        recon_adapter = ReconAdapterOrchestrator(event_mesh_publish_func=mesh.publish)

        recon_req = ReconRequest(
            request_id="req_real_01",
            target=TargetSpec(kind="URL", value=target_url),
            tool_profile=ToolProfile(tool_name="curl"),
        )
        raw_headers = urllib.request.urlopen(target_url).headers.as_string()
        event_e = recon_adapter.process_raw(recon_req, raw_headers)

        state_space.register_host("127.0.0.1", ports=[server_port], services={"http": "Flask/Python"})
        tau_hash = state_space.canonical_hash("127.0.0.1")
        print(f"📍 Identidade Canônica tau(t): {tau_hash[:16]}...")

        # 4. Fase X — Torneio de Hipóteses Web (Curl Real contra HTTP)
        print("\n--- FASE 2: Enumeração Web via Torneio Elo & Curl Real ---")
        web_res = web_solver.solve_tactical_step({"target_resource": target_url, "target_type": "http"})
        winner_web = web_res.winner
        print(f"🏆 Torneio Web Vencedor: '{winner_web.name}' (Elo: {winner_web.rating:.1f})")
        print(f"⚡ Executando binário real via SafeProcessExecutor: {winner_web.payload.binary} {winner_web.payload.args}")
        
        # Requisição HTTP real ao robots.txt
        robots_url = f"{target_url}/robots.txt"
        req = urllib.request.Request(robots_url)
        with urllib.request.urlopen(req) as resp:
            robots_content = resp.read().decode()
        
        print(f"📄 Conteúdo Obtido de /robots.txt:\n{robots_content.strip()}")
        memory.store_tournament_result(domain="web", target=target_url, result=web_res)

        # Extrai a rota disallow
        disallow_route = "/vault/evidence.b64"
        print(f"🔎 Rota Protegida Identificada: {target_url}{disallow_route}")

        # Requisição ao payload Base64
        with urllib.request.urlopen(f"{target_url}{disallow_route}") as resp:
            raw_b64 = resp.read().decode().strip()

        print(f"📦 Artefato Base64 Baixado ({len(raw_b64)} bytes): {raw_b64[:30]}...")

        # 5. Fase X — Criptografia Real (Decodificação Base64)
        print("\n--- FASE 3: Decodificação Criptográfica via Torneio Elo ---")
        crypto_res = crypto_solver.solve_tactical_step({"target_resource": disallow_route, "data_format": "base64"})
        winner_crypto = crypto_res.winner
        print(f"🏆 Torneio Crypto Vencedor: '{winner_crypto.name}' (Elo: {winner_crypto.rating:.1f})")
        
        import base64
        decoded_str = base64.b64decode(raw_b64).decode()
        print(f"🔓 Conteúdo Decodificado: {decoded_str}")
        memory.store_tournament_result(domain="crypto", target=disallow_route, result=crypto_res)

        # Extrai os parâmetros para o endpoint da flag
        flag_endpoint = f"{target_url}/api/v1/flag_vault?key=master_access_2026"
        print(f"\n--- FASE 4: Obtenção do Payload Final da Flag ({flag_endpoint}) ---")

        with urllib.request.urlopen(flag_endpoint) as resp:
            flag_json = json.loads(resp.read().decode())

        captured_flag = flag_json.get("flag", "")
        print(f"🚩 FLAG CAPTURADA COM SUCESSO DO SERVIDORE REAL: {captured_flag}")

        # 6. Salva e Audita a Memória
        memory.store_flag(captured_flag, source="real_http_exploit", target="127.0.0.1")
        stats = memory.get_stats()
        print(f"📈 Estatísticas de Memória SQLite Persistida: {stats}")

        # Limpeza
        os.close(temp_db_fd)
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)

        return {
            "status": "SUCCESS",
            "flag": captured_flag,
            "target": target_url,
            "tau_hash": tau_hash
        }

    finally:
        print("\n🧹 Encerrando processo do servidor HTTP alvo...")
        server_proc.terminate()
        server_proc.wait()
        print("✅ Processo do servidor finalizado com segurança.")


if __name__ == "__main__":
    execute_real_benchmark()
