import argparse
import asyncio
import sys

from attacks import normal_traffic, http_flood, brute_force, like_flood, slowloris

def main():
    parser = argparse.ArgumentParser(description="Attack Generator for MiniLink IDS Project")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Normal traffic
    p_normal = subparsers.add_parser("normal", help="Generate normal user traffic")
    p_normal.add_argument("--duration", type=int, default=60, help="Duration in seconds")

    # HTTP Flood
    p_flood = subparsers.add_parser("http-flood", help="HTTP DDoS attack")
    p_flood.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    p_flood.add_argument("--concurrency", type=int, default=50, help="Concurrent workers")

    # Brute-force
    p_brute = subparsers.add_parser("brute-force", help="Password brute-force")
    p_brute.add_argument("--user", type=str, default="alice", help="Target username")
    p_brute.add_argument("--attempts", type=int, default=500, help="Number of attempts")

    # Like Flood
    p_like = subparsers.add_parser("like-flood", help="Like spam attack")
    p_like.add_argument("--user", type=str, default="bob", help="Bot username")
    p_like.add_argument("--post-id", type=int, default=1, help="Target post ID")
    p_like.add_argument("--count", type=int, default=500, help="Number of likes")

    # Slowloris
    p_slow = subparsers.add_parser("slowloris", help="Slowloris attack")
    p_slow.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    p_slow.add_argument("--connections", type=int, default=100, help="Number of connections")

    args = parser.parse_args()

    if args.command == "normal":
        asyncio.run(normal_traffic.run_normal_traffic(args.duration))
    elif args.command == "http-flood":
        asyncio.run(http_flood.run_http_flood(args.duration, args.concurrency))
    elif args.command == "brute-force":
        asyncio.run(brute_force.run_brute_force(args.user, args.attempts))
    elif args.command == "like-flood":
        asyncio.run(like_flood.run_like_flood(args.user, args.post_id, args.count))
    elif args.command == "slowloris":
        asyncio.run(slowloris.run_slowloris(args.duration, args.connections))
    else:
        print("Unknown command")
        sys.exit(1)

if __name__ == "__main__":
    main()