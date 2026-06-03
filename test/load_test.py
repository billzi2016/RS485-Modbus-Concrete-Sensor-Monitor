from __future__ import annotations

import argparse
import asyncio
import signal
import statistics
import time

import httpx

_stop_event: asyncio.Event | None = None


async def worker(
    client: httpx.AsyncClient,
    path: str,
    stop: asyncio.Event,
    latencies: list[float],
    failures: list[int],
) -> int:
    completed = 0
    while not stop.is_set():
        started = time.perf_counter()
        try:
            response = await client.get(path)
            response.raise_for_status()
        except Exception:
            failures.append(1)
        else:
            latencies.append((time.perf_counter() - started) * 1000.0)
            completed += 1
    return completed


async def worker_timed(
    client: httpx.AsyncClient,
    path: str,
    deadline: float,
    latencies: list[float],
    failures: list[int],
) -> int:
    completed = 0
    while time.perf_counter() < deadline:
        started = time.perf_counter()
        try:
            response = await client.get(path)
            response.raise_for_status()
        except Exception:
            failures.append(1)
        else:
            latencies.append((time.perf_counter() - started) * 1000.0)
            completed += 1
    return completed


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * ratio) - 1))
    return ordered[index]


def print_stats(
    base_url: str,
    path: str,
    concurrency: int,
    elapsed: float,
    latencies: list[float],
    failures: list[int],
    label: str = "Load test result",
) -> None:
    total = len(latencies) + len(failures)
    rps = round(total / max(elapsed, 1), 2)
    print(f"\n{label}")
    print(f"  base_url:          {base_url}")
    print(f"  path:              {path}")
    print(f"  concurrency:       {concurrency}")
    print(f"  elapsed_seconds:   {round(elapsed, 1)}")
    print(f"  requests_total:    {total}")
    print(f"  requests_success:  {len(latencies)}")
    print(f"  requests_failed:   {len(failures)}")
    print(f"  rps:               {rps}")
    print(f"  latency_ms_avg:    {round(statistics.fmean(latencies), 2) if latencies else 0.0}")
    print(f"  latency_ms_p95:    {round(percentile(latencies, 0.95), 2)}")
    print(f"  latency_ms_max:    {round(max(latencies), 2) if latencies else 0.0}")


async def run_loop(base_url: str, path: str, concurrency: int, interval: int) -> None:
    """无限循环压测，每 interval 秒打印一次阶段统计，Ctrl+C 退出并打印汇总。"""
    stop = asyncio.Event()
    timeout = httpx.Timeout(5.0, connect=5.0)
    all_latencies: list[float] = []
    all_failures: list[int] = []
    start_all = time.perf_counter()
    round_num = 0

    def _handle_signal() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, _handle_signal)
    loop.add_signal_handler(signal.SIGTERM, _handle_signal)

    print(f"Infinite loop mode — interval={interval}s  concurrency={concurrency}  Ctrl+C to stop\n")

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        while not stop.is_set():
            round_num += 1
            round_latencies: list[float] = []
            round_failures: list[int] = []
            deadline = time.perf_counter() + interval
            round_start = time.perf_counter()

            tasks = [
                asyncio.create_task(
                    worker_timed(client, path, deadline, round_latencies, round_failures)
                )
                for _ in range(concurrency)
            ]

            done, _ = await asyncio.wait(
                tasks,
                timeout=interval + 1,
                return_when=asyncio.ALL_COMPLETED,
            )

            elapsed = time.perf_counter() - round_start
            all_latencies.extend(round_latencies)
            all_failures.extend(round_failures)

            if not stop.is_set():
                print_stats(base_url, path, concurrency, elapsed,
                            round_latencies, round_failures,
                            label=f"Round {round_num}")

    total_elapsed = time.perf_counter() - start_all
    print_stats(base_url, path, concurrency, total_elapsed,
                all_latencies, all_failures, label="=== Final summary ===")


async def run_once(base_url: str, path: str, concurrency: int, duration: int) -> None:
    """固定时长压测，结束后打印一次结果。"""
    timeout = httpx.Timeout(5.0, connect=5.0)
    latencies: list[float] = []
    failures: list[int] = []
    deadline = time.perf_counter() + duration

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        tasks = [
            asyncio.create_task(
                worker_timed(client, path, deadline, latencies, failures)
            )
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)

    print_stats(base_url, path, concurrency, duration, latencies, failures)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Async load test for mock FastAPI endpoints. --duration 0 = infinite loop."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--path", default="/api/matrix/strain")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--duration", type=int, default=10,
                        help="Test duration in seconds. 0 = run forever (Ctrl+C to stop).")
    parser.add_argument("--interval", type=int, default=10,
                        help="Stats print interval in seconds (only used when --duration 0).")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.duration == 0:
        await run_loop(args.base_url, args.path, args.concurrency, args.interval)
    else:
        await run_once(args.base_url, args.path, args.concurrency, args.duration)


if __name__ == "__main__":
    asyncio.run(main())
