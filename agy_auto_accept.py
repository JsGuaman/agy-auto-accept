"""Auto-aceptador de peticiones de aprobacion del agente AGY (Gemini CLI / Antigravity) en Herdr.

Por que existe:
Herdr no detecta el prompt de permisos de AGY como estado "blocked", ya que
el manifiesto de Herdr busca patrones en ingles como "requesting permission for:",
mientras que AGY despliega un selector interactivo tipo:
    Allow creation of this file?
    > 1. Yes, allow creation
      2. No, deny creation
    ...
    esc to cancel

Este script monitorea el panel asignado (o detecta automaticamente la sesion de AGY),
analiza la salida reciente de la terminal de Herdr buscando dicho dialogo, y
envia la tecla 'Enter' (seleccionando la opcion predeterminada "1. Yes") de forma segura.

Uso rapido:
    # Auto-detectar agente AGY:
    python agy_auto_accept.py

    # Especificar un panel puntual:
    python agy_auto_accept.py --target w4:p6

    # Listar todos los agentes activos en Herdr:
    python agy_auto_accept.py --list
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime

# Regex de deteccion del dialogo interactivo de AGY
PROMPT_YES_RE = re.compile(r">\s*1\.\s*Yes", re.IGNORECASE)
PROMPT_ESC_RE = re.compile(r"esc to cancel", re.IGNORECASE)


def log(msg: str) -> None:
    """Imprime un mensaje con timestamp en stdout con flush inmediato."""
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def run_herdr(args: list[str]) -> str | None:
    """Ejecuta un subcomando de herdr y devuelve stdout, o None si falla."""
    try:
        proc = subprocess.run(
            ["herdr", *args],
            capture_output=True,
            text=True,
            timeout=25,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        log("ERROR: El comando 'herdr' no se encuentra en el PATH del sistema.")
        return None
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"ERROR invocando herdr: {exc}")
        return None

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        log(f"herdr {' '.join(args)} fallo (rc={proc.returncode}): {err[:300]}")
        return None
    return proc.stdout


def get_all_agents() -> list[dict]:
    """Obtiene la lista completa de agentes reportados por Herdr."""
    out = run_herdr(["agent", "list"])
    if not out:
        return []
    try:
        data = json.loads(out)
        return (data.get("result") or {}).get("agents", [])
    except json.JSONDecodeError:
        return []


def list_agents_table() -> None:
    """Muestra una tabla con los agentes y paneles activos en Herdr."""
    agents = get_all_agents()
    if not agents:
        print("No se encontraron agentes activos en Herdr o el CLI no respondio.")
        return

    print("\n=== AGENTES ACTIVOS EN HERDR ===")
    print(f"{'PANE ID':<10} {'AGENTE':<12} {'ESTADO':<10} {'FOCO':<6} {'DIR / TITULO'}")
    print("-" * 75)
    for a in agents:
        pane = a.get("pane_id", "-")
        agent_name = a.get("agent", "-")
        status = a.get("agent_status", "-")
        focused = "Si" if a.get("focused") else "No"
        cwd = a.get("cwd") or a.get("terminal_title_stripped") or ""
        print(f"{pane:<10} {agent_name:<12} {status:<10} {focused:<6} {cwd}")
    print("-" * 75 + "\n")


def find_agy_pane() -> str | None:
    """Busca automaticamente el pane_id de un agente 'agy' activo."""
    agents = get_all_agents()
    if not agents:
        return None

    agy_agents = [a for a in agents if a.get("agent") == "agy"]
    if not agy_agents:
        return None

    # Si hay mas de uno, preferir el que tenga el foco
    for a in agy_agents:
        if a.get("focused"):
            return a.get("pane_id")

    return agy_agents[0].get("pane_id")


def read_pane(target: str, lines: int = 40) -> str | None:
    """Lee el texto reciente del panel indicado."""
    return run_herdr(["agent", "read", target, "--source", "recent", "--lines", str(lines)])


def get_agent(target: str) -> dict | None:
    """Consulta los metadatos y estado del agente en el target indicado."""
    out = run_herdr(["agent", "get", target])
    if not out:
        return None
    try:
        data = json.loads(out)
        return (data.get("result") or {}).get("agent")
    except json.JSONDecodeError:
        return None


def looks_like_approval(text: str) -> bool:
    """Verifica si el contenido de la pantalla coincide con el dialogo de aprobacion de AGY."""
    return bool(PROMPT_YES_RE.search(text) and PROMPT_ESC_RE.search(text))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-aceptador de permisos para el agente AGY en Herdr."
    )
    parser.add_argument(
        "--target",
        default="auto",
        help="Pane ID o nombre del agente a vigilar (ej: w4:p6). Por defecto 'auto' para autodetectar.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Segundos entre cada sondeo de la terminal (por defecto 1.5).",
    )
    parser.add_argument(
        "--heartbeat",
        type=float,
        default=60.0,
        help="Segundos entre logs de estado 'sigo vivo' (0 = desactivar).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todos los agentes y paneles activos en Herdr y sale.",
    )
    args = parser.parse_args()

    if args.list:
        list_agents_table()
        sys.exit(0)

    target = args.target
    if target.lower() == "auto":
        log("Buscando agente AGY activo en Herdr...")
        detected = find_agy_pane()
        if not detected:
            log("No se encontro ningun agente 'agy' activo actualmente.")
            log("Puedes usar --list para ver agentes disponibles o especificar --target <pane_id>.")
            sys.exit(1)
        target = detected
        log(f"Agente AGY detectado automaticamente en panel: {target}")

    log(f"Iniciando vigilancia en '{target}' cada {args.interval:.1f}s. Presiona Ctrl+C para detener.")

    waiting_clear = False
    last_heartbeat = time.monotonic()

    try:
        while True:
            agent = get_agent(target)
            if agent is None:
                # Target sin agente o Herdr temporalmente ocupado
                time.sleep(args.interval * 2)
                continue

            if agent.get("agent") != "agy":
                log(f"Aviso: {target} ahora aloja '{agent.get('agent')}' (se esperaba 'agy'); en pausa...")
                while True:
                    time.sleep(5)
                    agent = get_agent(target)
                    if agent and agent.get("agent") == "agy":
                        log("AGY regreso al panel. Reanudando vigilancia.")
                        break
                continue

            text = read_pane(target) or ""
            prompted = looks_like_approval(text)

            if prompted and not waiting_clear:
                log(f"Dialogo de aprobacion detectado (estado Herdr: {agent.get('agent_status')}). Enviando Enter...")
                if run_herdr(["agent", "send-keys", target, "enter"]) is not None:
                    log("Aprobacion enviada exitosamente (Enter sobre '1. Yes').")
                    waiting_clear = True
            elif not prompted and waiting_clear:
                waiting_clear = False
                log("Dialogo resuelto. Detector rearmado.")

            if args.heartbeat > 0 and (time.monotonic() - last_heartbeat >= args.heartbeat):
                last_heartbeat = time.monotonic()
                log(
                    f"Heartbeat OK | target: {target} | estado: {agent.get('agent_status')} | "
                    f"dialogo visible: {'SI' if prompted else 'NO'}"
                )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        log("Detenido por el usuario (Ctrl+C). Salida limpia.")


if __name__ == "__main__":
    main()
