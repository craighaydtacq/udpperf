import argparse
import socket


if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = 53676
    MESSAGE = "hello world"
    PACKET_SIZE = 9000
    SOCKET_BUFFER_SIZE = 2000000

    parser = argparse.ArgumentParser(
        prog="udptx",
        description="Transmits UDP packet. If no message is given to fill the packet then it transmits the string hello world encoded as utf-8",
        epilog="UDP packet transmitter",
    )

    parser.add_argument("message", nargs="?", const=1, default=MESSAGE)
    parser.add_argument("-a", "--address", default=UDP_IP, help="IPv4 address to TX to")
    parser.add_argument("-p", "--port", default=UDP_PORT, help="UDP port to TX to")
    parser.add_argument(
        "-s", "--packet_size", default=PACKET_SIZE, help="TX packet size (bytes)"
    )
    parser.add_argument(
        "-b",
        "--buffer_size",
        default=SOCKET_BUFFER_SIZE,
        help="socket buffer size (bytes)",
    )
    args = parser.parse_args()

    print(args)

    print(f"UDP target IP: {args.address}")
    print(f"UDP target port: {args.port}")
    print(f"message: {args.message}")

    message = args.message

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, args.buffer_size)

    sock.sendto(message.encode("utf-8"), (args.address, int(args.port)))
