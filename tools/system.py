"""System tools: battery, CPU, GPU, RAM, storage, temperature, processes."""

import asyncio
import subprocess

from claude_agent_sdk import tool


def _system_stats() -> str:
    import psutil

    lines = []
    lines.append(f"CPU usage: {psutil.cpu_percent(interval=0.4)}%")
    mem = psutil.virtual_memory()
    lines.append(
        f"RAM: {mem.used / 1e9:.1f} / {mem.total / 1e9:.1f} GB ({mem.percent}%)"
    )
    for part in psutil.disk_partitions(all=False):
        try:
            du = psutil.disk_usage(part.mountpoint)
            lines.append(
                f"Disk {part.device} {du.used / 1e9:.0f} / {du.total / 1e9:.0f} GB "
                f"({du.percent}%)"
            )
        except OSError:
            pass
    battery = psutil.sensors_battery()
    if battery:
        plug = "plugged in" if battery.power_plugged else "on battery"
        lines.append(f"Battery: {battery.percent}% ({plug})")
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,"
             "memory.total,temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if gpu.returncode == 0 and gpu.stdout.strip():
            name, util, mused, mtotal, temp = [
                x.strip() for x in gpu.stdout.strip().split(",")
            ]
            lines.append(f"GPU: {name}, {util} load, {mused}/{mtotal} VRAM, {temp}C")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return "\n".join(lines)


def _list_processes(sort_by: str) -> str:
    import psutil

    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            procs.append((
                p.info["name"],
                p.info["cpu_percent"] or 0.0,
                (p.info["memory_info"].rss if p.info["memory_info"] else 0) / 1e6,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    key = 1 if sort_by == "cpu" else 2
    procs.sort(key=lambda x: x[key], reverse=True)
    lines = [f"{name}: {cpu:.0f}% CPU, {mem:.0f} MB" for name, cpu, mem in procs[:15]]
    return "\n".join(lines)


@tool("system_stats", "Get current CPU, RAM, disk, GPU, temperature and battery "
      "status of this PC.", {})
async def system_stats(args: dict) -> dict:
    text = await asyncio.to_thread(_system_stats)
    return {"content": [{"type": "text", "text": text}]}


@tool("list_processes", "List the top running processes on this PC by CPU or "
      "memory usage.", {"sort_by": str})
async def list_processes(args: dict) -> dict:
    text = await asyncio.to_thread(_list_processes, args.get("sort_by", "cpu"))
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [system_stats, list_processes]
