"""Unified Command Line Interface for QuantumGuard Honeypot System."""

import sys
import time
import argparse
import json

from .tokens.generator import generate_honeytoken
from .tokens.registry import REGISTRY
from .tokens.verifier import verify_token_access
from .traps.http_trap import DecoyHTTPTrap
from .traps.ssh_trap import DecoySSHTrap
from .traps.canary_trap import CanaryFilesystemTrap
from .reporting.analytics import run_quantum_benchmark, generate_analytics_charts
from .reporting.pdf_report import build_upgraded_pdf
from .detection.siem_logger import SIEM_LOG_FILE

def cmd_status(args):
    REGISTRY.bootstrap_default_decoys()
    tokens = REGISTRY.list_tokens()
    print("\n" + "=" * 70)
    print(" [*] QUANTUM HONEYPOT SYSTEM - OPERATIONAL STATUS")
    print("=" * 70)
    print(f" Total Registered Honeytokens : {len(tokens)}")
    print(f" SIEM Log Location           : {SIEM_LOG_FILE}")
    print("-" * 70)
    print(f" {'Token ID':<18} {'Type':<12} {'Target Service':<26} {'Status':<10}")
    print("-" * 70)
    for t in tokens:
        print(f" {t['token_id']:<18} {t['token_type']:<12} {t['target_service']:<26} {t['status']:<10}")
    print("=" * 70 + "\n")

def cmd_deploy(args):
    REGISTRY.bootstrap_default_decoys()
    canary = CanaryFilesystemTrap()
    files = canary.deploy_canaries()
    print(f"\n[+] Successfully deployed {len(files)} quantum decoy canary files:")
    for f in files:
        print(f"    - {f}")
    print("[+] Canary tripwires armed and synchronized with quantum register.\n")

def cmd_traps(args):
    print("\n" + "=" * 70)
    print(" [*] STARTING QUANTUM DECOY TRAP DAEMONS")
    print("=" * 70)
    REGISTRY.bootstrap_default_decoys()
    
    http_trap = DecoyHTTPTrap(host=args.host, port=args.http_port)
    ssh_trap = DecoySSHTrap(host=args.host, port=args.ssh_port)
    canary = CanaryFilesystemTrap()
    canary.deploy_canaries()

    http_trap.start()
    ssh_trap.start()

    print(f"[+] HTTP Decoy Gateway : http://{args.host}:{args.http_port}/")
    print(f"[+] Decoy Secrets Leak : http://{args.host}:{args.http_port}/.env")
    print(f"[+] SSH Honeytrap Port : {args.ssh_port}")
    print("[+] Press Ctrl+C to terminate trap daemons...\n")

    try:
        while True:
            time.sleep(1)
            canary.check_canaries()
    except KeyboardInterrupt:
        print("\n[*] Shutting down traps...")
        http_trap.stop()
        ssh_trap.stop()
        print("[*] Daemons stopped cleanly.")

def cmd_simulate(args):
    print(f"\n[*] Executing Monte-Carlo benchmark ({args.trials} trials, {args.qubits} qubits)...")
    data = run_quantum_benchmark(n_trials=args.trials, n_qubits=args.qubits, noise_floor=args.noise)
    print("[*] Generating statistical visualization charts...")
    chart_paths = generate_analytics_charts(data, output_dir=args.chart_dir)
    print(f"[+] Charts generated in '{args.chart_dir}/':")
    for name, p in chart_paths.items():
        print(f"    - {name}: {p}")

    if args.pdf:
        print(f"[*] Compiling technical scientific PDF report...")
        pdf_path = build_upgraded_pdf(data, chart_paths, out_pdf=args.pdf_out)
        print(f"[+] PDF Report generated: {pdf_path}")

    print("\n" + "-" * 60)
    print(f" {'Vector':<22} {'Mean Fidelity':<15} {'Detection Rate':<15}")
    print("-" * 60)
    fids = data["fidelities"]
    for k in fids:
        avg = float(sum(fids[k]) / len(fids[k]))
        rate = float(sum(1 for f in fids[k] if f < 0.85) / len(fids[k]) * 100.0)
        print(f" {k:<22} {avg:<15.4f} {rate:<15.1f}%")
    print("-" * 60 + "\n")

def cmd_verify(args):
    from .detection.alerts import DISPATCHER
    REGISTRY.bootstrap_default_decoys()
    token = REGISTRY.get_by_id(args.token_id) or REGISTRY.list_tokens()[0]
    if isinstance(token, dict):
        token = REGISTRY.get_by_id(token["token_id"])
    
    print(f"\n[*] Verifying token {token.token_id} with strategy: '{args.strategy}'...")
    res = verify_token_access(token, strategy=args.strategy, channel_noise=args.noise)
    
    DISPATCHER.dispatch(
        event_type=token.token_type,
        token_id=token.token_id,
        target_service=token.target_service,
        source_ip="127.0.0.1 (CLI Operator)",
        fidelity=res.mean_fidelity,
        threshold=res.threshold,
        is_attack=res.is_intrusion,
        extra={"strategy": args.strategy, "qubits": len(token.qubits)}
    )

    print(f"[+] Mean Fidelity : {res.mean_fidelity:.4f}")
    print(f"[+] Threshold     : {res.threshold:.2f}")
    print(f"[+] Intrusion     : {'[BREACH DETECTED]' if res.is_intrusion else '[CLEAN / VERIFIED]'}")
    print(f"[+] Confidence    : {res.confidence * 100:.2f}%")
    if res.chsh_data:
        print(f"[+] Bell CHSH S   : {res.chsh_data['S']:.4f} (Quantum Bound: 2.828, Classical: 2.000)")
    print()

def main():
    parser = argparse.ArgumentParser(description="Quantum Honeypot System v2.0 - Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="View active tokens and system telemetry")
    p_status.set_defaults(func=cmd_status)

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy decoy canary credential files")
    p_deploy.set_defaults(func=cmd_deploy)

    # run-traps
    p_traps = subparsers.add_parser("run-traps", help="Launch live decoy trap servers (HTTP & SSH)")
    p_traps.add_argument("--host", default="127.0.0.1", help="Bind host")
    p_traps.add_argument("--http-port", type=int, default=8080, help="HTTP trap port")
    p_traps.add_argument("--ssh-port", type=int, default=2222, help="SSH trap port")
    p_traps.set_defaults(func=cmd_traps)

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Run multi-vector quantum simulation benchmark")
    p_sim.add_argument("--trials", type=int, default=50, help="Number of trials per attack vector")
    p_sim.add_argument("--qubits", type=int, default=8, help="Number of qubits per register")
    p_sim.add_argument("--noise", type=float, default=0.02, help="Channel depolarizing noise floor")
    p_sim.add_argument("--chart-dir", default="charts", help="Output directory for charts")
    p_sim.add_argument("--pdf", action="store_true", default=True, help="Compile PDF scientific report")
    p_sim.add_argument("--pdf-out", default="honeypot_report.pdf", help="Output PDF filename")
    p_sim.set_defaults(func=cmd_simulate)

    # verify
    p_verify = subparsers.add_parser("verify", help="Inspect and measure a quantum honeytoken")
    p_verify.add_argument("--token-id", default="", help="Token ID to test")
    p_verify.add_argument("--strategy", choices=["legit", "random", "fixed_basis", "cloning_uqcm", "asymmetric_clone"], default="random")
    p_verify.add_argument("--noise", type=float, default=0.02, help="Channel noise floor")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)

if __name__ == "__main__":
    main()
