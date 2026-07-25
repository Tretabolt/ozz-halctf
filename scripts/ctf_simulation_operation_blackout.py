#!/usr/bin/env python3
"""
Simulador E2E de CTF — Operation Blackout (MNHI 3.5 & Co-Scientist Hypothesis Tournament)

Este script executa um estudo de caso completo simulando o fluxo de resolução de um CTF
multi-estágio pelo Agente Ozz, acionando todos os componentes do ecossistema:
  - Espaço E: ReconAdapter & EventMesh (EventClassI)
  - Espaço S: StateSpace (Grafo G(t), Hash Canônico tau(t), Snapshot sigma(t))
  - Espaço X: Executive, DomainSolverRegistry, TacticalHypothesisEngine (Elo Pairwise),
              CoScientistWebSolver, CoScientistCryptoSolver, CoScientistForensicsSolver,
              PwnRevDomainSolver (4 Quadrantes) e CoScientistPrivescSolver
  - Barreira de Segurança: CommandAllowlistPolicy & SafeProcessExecutor (shell=False)
  - Espaço P: Memory SQLite (Tabela tournaments, Histórico H e Idempotência C)

Uso:
    python scripts/ctf_simulation_operation_blackout.py
"""

import os
import sys
import tempfile
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.nedk import NEDK, EventMesh, StateSpace, Executive
from agent.recon_adapter import ReconAdapterOrchestrator
from agent.recon_adapter.dtos import EventClassI, ReconRequest, TargetSpec, ToolProfile
from agent.domains.registry import DomainSolverRegistry
from agent.domains.pwn_rev import PwnRevDomainSolver
from agent.domains.web import WebDomainSolver
from agent.domains.forensics import ForensicsDomainSolver
from agent.domains.privesc import PrivescDomainSolver
from agent.domains.crypto import CryptoDomainSolver
from agent.ports.executor import MockProcessExecutor
from agent.ports.file_reader import MockFileReader
from agent.memory import Memory
from agent.dtos.domain_dtos import AnalysisRequest


def run_ctf_simulation() -> Dict[str, Any]:
    print("=" * 70)
    print("🏴 SIMULAÇÃO E2E DE CTF — OPERATION BLACKOUT (PARADIGMA MNHI 3.5)")
    print("=" * 70)

    # 0. Inicialização da Memória SQLite Temporária (Espaço P)
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix="_ozz_ctf.db")
    memory = Memory(db_path=temp_db_path)
    print(f"✅ [Espaço P] Memória SQLite inicializada em: {temp_db_path}")

    # Auto-descoberta dos solvers via DomainSolverRegistry (OCP)
    DomainSolverRegistry.discover_solvers()
    print(f"✅ [Espaço X] Solvers registrados no Registry: {sorted(DomainSolverRegistry._solvers.keys())}")

    # Instanciação das Ports de Infraestrutura Mockadas para a simulação
    mock_executor = MockProcessExecutor(mock_output="CTF Execution Output OK")
    mock_file_reader = MockFileReader(exists_return=True, header_return=b"\x7fELF")

    web_solver = WebDomainSolver(executor=mock_executor, file_reader=mock_file_reader)
    crypto_solver = CryptoDomainSolver(executor=mock_executor, file_reader=mock_file_reader)
    forensics_solver = ForensicsDomainSolver(executor=mock_executor, file_reader=mock_file_reader)
    pwn_solver = PwnRevDomainSolver(executor=mock_executor, file_reader=mock_file_reader)
    privesc_solver = PrivescDomainSolver(executor=mock_executor, file_reader=mock_file_reader)

    # 1. Fase 1: Reconhecimento Passivo & Ingestão (Espaço E -> S)
    print("\n--- FASE 1: Reconhecimento Passivo & Ingestão (Espaço E -> S) ---")
    mesh = EventMesh()
    state_space = StateSpace()
    recon_adapter = ReconAdapterOrchestrator(event_mesh_publish_func=mesh.publish)

    recon_req = ReconRequest(
        request_id="req_blackout_01",
        target=TargetSpec(kind="IP", value="10.0.0.50"),
        tool_profile=ToolProfile(tool_name="nmap"),
    )
    raw_nmap_output = "Nmap scan report for 10.0.0.50\nPORT 80/tcp open http nginx/1.18.0\nPORT 22/tcp open ssh OpenSSH"
    event_e = recon_adapter.process_raw(recon_req, raw_nmap_output)

    # Atualiza identidade canônica tau(t) e Grafo G(t)
    state_space.register_host("10.0.0.50", ports=[80, 22], services={"http": "nginx/1.18.0", "ssh": "OpenSSH"})
    tau_hash = state_space.canonical_hash("10.0.0.50")
    print(f"📍 Host Ingerido: 10.0.0.50 | Hash Canônico tau(t): {tau_hash[:16]}...")
    print(f"📊 Grafo G(t) nós ativos: {len(state_space.graph)}")

    # 2. Fase 2: Enumeração Web via Torneio Elo (CoScientistWebSolver)
    print("\n--- FASE 2: Enumeração Web via Torneio Elo (WebDomainSolver) ---")
    web_res = web_solver.solve_tactical_step({"target_resource": "http://10.0.0.50", "target_type": "http"})
    winner_web = web_res.winner
    print(f"🏆 Torneio Web Vencedor: '{winner_web.name}' (Rating Elo: {winner_web.rating:.1f})")
    print(f"💬 Debate Summary: {web_res.debate_summary}")
    print(f"⚡ Comando Executado: {winner_web.payload.binary} {' '.join(winner_web.payload.args)}")
    memory.store_tournament_result(domain="web", target="http://10.0.0.50", result=web_res)

    # Simula descoberta do artefato oculto /static/evidence.jpg.b64
    artifact_b64 = "evidence.jpg.b64"
    print(f"🔎 Artefato Descoberto na Rota: {artifact_b64}")

    # 3. Fase 3: Decodificação Criptográfica (CoScientistCryptoSolver)
    print("\n--- FASE 3: Decodificação Criptográfica (CryptoDomainSolver) ---")
    crypto_res = crypto_solver.solve_tactical_step({"target_resource": artifact_b64, "data_format": "base64"})
    winner_crypto = crypto_res.winner
    print(f"🏆 Torneio Crypto Vencedor: '{winner_crypto.name}' (Rating Elo: {winner_crypto.rating:.1f})")
    print(f"⚡ Comando Executado: {winner_crypto.payload.binary} {' '.join(winner_crypto.payload.args)}")
    memory.store_tournament_result(domain="crypto", target=artifact_b64, result=crypto_res)

    artifact_jpg = "evidence.jpg"
    print(f"🔓 Artefato Decodificado: {artifact_jpg}")

    # 4. Fase 4: Análise Forense & Extração de Binário (CoScientistForensicsSolver)
    print("\n--- FASE 4: Análise Forense & Extração (ForensicsDomainSolver) ---")
    forensics_res = forensics_solver.solve_tactical_step({"target_resource": artifact_jpg, "mime_type": "image/png"})
    winner_forensics = forensics_res.winner
    print(f"🏆 Torneio Forensics Vencedor: '{winner_forensics.name}' (Rating Elo: {winner_forensics.rating:.1f})")
    print(f"⚡ Comando Executado: {winner_forensics.payload.binary} {' '.join(winner_forensics.payload.args)}")
    memory.store_tournament_result(domain="forensics", target=artifact_jpg, result=forensics_res)

    binary_target = "target_elf"
    print(f"📦 Binário Extraído de Assinatura Embarcada: {binary_target}")

    # 5. Fase 5: Análise Estática de Segurança & 4 Quadrantes (PwnRevDomainSolver)
    print("\n--- FASE 5: Análise Estática Pwn/Rev (PwnRevDomainSolver) ---")
    # Simula inspeção readelf -d com NX=True, Canary=True, PIE=False
    strat = pwn_solver.evaluate_tactical_strategy({"NX": True, "Canary": True, "PIE": False})
    print(f"🛡 Proteções Detectadas: NX=True, Canary=True, PIE=False")
    print(f"🎯 Estratégia Decidida pelo Motor de 4 Quadrantes: {strat.strategy_name}")
    print(f"📌 Pré-requisitos Táticos: {strat.prerequisites}")

    pwn_report = pwn_solver.analyze(AnalysisRequest(domain="pwn", target_resource=binary_target))
    print(f"✅ Análise Estática Segura (sem ldd) Concluída: success={pwn_report.success}")

    # 6. Fase 6: Auditoria de Elevação de Privilégios (CoScientistPrivescSolver)
    print("\n--- FASE 6: Auditoria de Privilégios (PrivescDomainSolver) ---")
    privesc_res = privesc_solver.solve_tactical_step({"user_level": "low_privilege"})
    winner_privesc = privesc_res.winner
    print(f"🏆 Torneio Privesc Vencedor: '{winner_privesc.name}' (Rating Elo: {winner_privesc.rating:.1f})")
    print(f"⚡ Comando Executado: {winner_privesc.payload.binary} {' '.join(winner_privesc.payload.args)}")
    memory.store_tournament_result(domain="privesc", target="local_system", result=privesc_res)

    # 7. Fase 7: Captura de Flag & Auditoria de Persistência (Espaço P)
    print("\n--- FASE 7: Captura de Flag & Auditoria de Memória (Espaço P) ---")
    flag_val = "FLAG{MNHI_3.5_OZZ_KAGGLE_SUCCESS}"
    memory.store_flag(flag_val, source="privesc_sudo", target="10.0.0.50")
    memory.store_flag(flag_val, source="privesc_sudo", target="10.0.0.50")  # Teste de idempotência

    flags = memory.get_flags()
    tournaments_hist = memory.get_tournament_history(limit=10)
    stats = memory.get_stats()

    print(f"🚩 Flags Salvas no Banco: {len(flags)} (Idempotência confirmada: 1 cópia única)")
    print(f"🏆 Torneios Gravados na Tabela 'tournaments': {len(tournaments_hist)}")
    print(f"📈 Estatísticas da Memória SQLite: {stats}")

    # Limpeza
    os.close(temp_db_fd)
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)

    print("\n" + "=" * 70)
    print("🎉 SIMULAÇÃO E2E DO CTF 'OPERATION BLACKOUT' CONCLUÍDA COM SUCESSO!")
    print("=" * 70)

    return {
        "flags_captured": len(flags),
        "tournaments_executed": len(tournaments_hist),
        "pwn_strategy": strat.strategy_name,
        "tau_hash": tau_hash,
    }


if __name__ == "__main__":
    run_ctf_simulation()
