import argparse
import os
import socket
import sys

if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = 53676
    JUMBO_FRAME_MAX_SIZE = 9000  # TODO: find the exact value of this
    MESSAGE = "hello world"
    PACKET_SIZE = 9000
    SOCKET_BUFFER_SIZE = 2000000  # TODO: Make this 2MB?

    parser = argparse.ArgumentParser(
        prog="udptx",
        description="Transmits UDP packet. If no message is given to fill the packet then it transmits the string hello world encoded as utf-8",
        # description="Reads a binary file, chunks it into packets, and transmits it via UDP."
        epilog="UDP packet transmitter",
        # epilog="Example: python udptx.py my_data.bin -a 192.168.1.10 -p 5005 --sample-bytes 128 --samples-per-packet 64"
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("file", help="Path to the binary data file to transmit.")
    # parser.add_argument("message", nargs="?", const=1, default=MESSAGE)
    parser.add_argument(
        "-a",
        "--address",
        default=UDP_IP,
        help=f"IPv4 address to TX to (default: {UDP_IP})",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=UDP_PORT,
        type=int,
        help=f"UDP port to TX to (default: {UDP_PORT})",
    )
    parser.add_argument(
        "--ssb", required=True, type=int, help="The size of a single sample in bytes."
    )
    parser.add_argument(
        "--spp",
        required=True,
        type=int,
        help="The number of samples to bundle into one UDP packet.",
    )
    parser.add_argument(
        "--max-udp-size",
        default=JUMBO_FRAME_MAX_SIZE,
        type=int,
        help=f"Max allowed UDP payload size (default: {JUMBO_FRAME_MAX_SIZE})",
    )
    parser.add_argument(
        "-s",
        "--packet_size",
        default=PACKET_SIZE,
        type=int,
        help="TX packet size (bytes)",
    )
    parser.add_argument(
        "-b",
        "--buffer_size",
        default=SOCKET_BUFFER_SIZE,
        type=int,
        help=f"Socket send buffer size in bytes (default: {SOCKET_BUFFER_SIZE})",
    )
    args = parser.parse_args()

    packet_payload_size = args.ssb * args.spp

    print("--- UDP Transmitter Configuration ---")
    print(f"Source File:          {args.file}")
    print(f"Target IP:            {args.address}")
    print(f"Target Port:          {args.port}")
    print(f"Sample Size:          {args.ssb} bytes")
    print(f"Samples per Packet:   {args.spp}")
    print(f"Calculated Payload:   {packet_payload_size} bytes")
    print(f"Max Allowed Payload:  {args.max_udp_size} bytes")
    print(f"Socket Send Buffer:   {args.buffer_size} bytes")
    print("-----------------------------------")

    # Check that the calculated packet size doesn't exceed the max allowed size
    if packet_payload_size > args.max_udp_size:
        print(
            f"Error: Calculated packet size ({packet_payload_size}) exceeds the maximum of {args.max_udp_size}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check that the file exists
    if not os.path.isfile(args.file):
        print(f"Error: File not found at '{args.file}'", file=sys.stderr)
        sys.exit(1)

    # message = args.message

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, args.buffer_size)
        print("\n Starting transmission")
        packet_count = 0
        total_bytes_sent = 0

        with open(args.file, "rb") as f:
            while True:
                chunk = f.read(packet_payload_size)
                if not chunk:
                    break  # EOF

                sock.sendto(chunk, (args.address, args.port))
                packet_count += 1
                total_bytes_sent += len(chunk)
                print(
                    f"\rSent packet #{packet_count} ({len(chunk)} bytes). Total sent: {total_bytes_sent} bytes.",
                    end="",
                )
    except socket.error as e:
        print(f"\nSocket Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"\nFile Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if "sock" in locals():
            sock.close()

    print(f"\n\n Transmission complete.")
    print(f"Sent {total_bytes_sent} bytes in {packet_count} packets.")

    # sock.sendto(message.encode("utf-8"), (args.address, args.port))
