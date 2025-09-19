import argparse
import socket
import time


def go_realtime(sched_fifo_priority):
    """
    struct sched_param p = {};
    p.sched_priority = sched_fifo_priority;

    int rc = sched_setscheduler(0, SCHED_FIFO, &p);

    if (rc){
            perror("failed to set RT priority");
    }
    """
    # TODO
    pass


if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = 53676
    PACKET_SIZE = 9000
    SOCKET_BUFFER_SIZE = 2000000

    parser = argparse.ArgumentParser(
        prog="udprx", description="Receives UDP packets", epilog="UDP packet receiver"
    )

    parser.add_argument(
        "-p", "--port", default=UDP_PORT, type=int, help="UDP receive port"
    )
    parser.add_argument(
        "-s", "--size", default=PACKET_SIZE, type=int, help="User data size"
    )
    parser.add_argument(
        "-b,",
        "--socket_buffer_size",
        default=SOCKET_BUFFER_SIZE,
        type=int,
        help="socket buffer size (bytes)",
    )
    parser.add_argument("--spp", default=1, type=int, help="Samples per packet")
    parser.add_argument("--ssb", default=64, type=int, help="Sample size (bytes)")
    parser.add_argument(
        "-c",
        "--count_column",
        default=-1,
        type=int,
        help="Count column (indexed from 0)",
    )
    parser.add_argument(
        "-t",
        "--step",
        default=1,
        type=int,
        help="Count step (default:1), but may be decimated",
    )
    parser.add_argument(
        "-R", "--rt_prio", default=0, type=int, help="set POSIX RT priority (0: no set)"
    )
    parser.add_argument(
        "-o", "--output", default=-1, type=int, help="1: output data to stdout"
    )
    parser.add_argument("-q", "--quiet", default=0, type=int, help="1: stop reporting")
    parser.add_argument(
        "-S",
        "--max_samples",
        default=0,
        type=int,
        help="stop after this many samples, 0: no limit",
    )
    parser.add_argument(
        "-M", "--max_errs", default=9, type=int, help="stop after this many errors"
    )
    parser.add_argument(
        "-a",
        "--local_address",
        default="0.0.0.0",
        help="optional local address\ne.g. multiple NICs, one port",
    )
    parser.add_argument(
        "-v", "--verbose", default=0, type=int, help="increase to get more chatty"
    )

    args = parser.parse_args()
    print(args)

    """
    Socket::Endpoint local(Settings.local_address, Settings.UDPPort);
    UDPReceiver Receive(local);
    Receive.setBufferSizes(Settings.SocketBufferSize, Settings.SocketBufferSize);
    Receive.printBufferSizes();
    """

    data_size = args.ssb * args.spp
    rx_bytes = 0
    rx_packets = 0
    deviation = False
    error_count = 0
    rx_packets_last_error = 0
    packets_lost = 0
    """
    Timer UpdateTimer;
    auto USecs = UpdateTimer.timeus();
    """
    update_timer = time.time()

    print(f"Expecting data size: {data_size}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, int(args.port)))

    if args.rt_prio:
        go_realtime(args.rt_prio)

    # TODO: figure out how to make this run forever is max_samples isn't set
    samples = 0
    while True:
        # Your condition to stop the loop
        if args.max_samples != 0 and samples >= args.max_samples:
            print(f"Reached max samples ({samples}). Stopping.")
            break

        data, addr = sock.recvfrom(args.socket_buffer_size)
        """
        int ReadSize = Receive.receive(buffer, BUFFERSIZE); /* cpp */
        """
        read_size = len(data)

        assert read_size > 0
        assert read_size == data_size

        rx_bytes += read_size
        rx_packets += 1
        if rx_packets == 1:
            # tick = time(0) /* cpp */
            tick = time.time()
        tock = time.time()

        print(f"received message {data}")

        if args.count_column >= 0:
            # Grab the first SPAD Count in case we're not starting from 1
            if rx_packets == 1:
                spad_tracker = buffer + 4 * args.count_column

            for i in range(0, args.spp - 1):
                spad_index = i * args.ssb + 4 * args.count_column

                spad_count = buffer + spad_index
                if (args.verbose and (samples + i < 5)) or deviation == True:
                    if deviation:
                        dev_or_ini = "dev"
                    else:
                        dev_or_ini = "ini"
                    print(f"%#010x    %i %s\n", spad_count, spad_count, dev_or_ini)
                    deviation = False
                if spad_tracker != spad_count:
                    deviation = True
                    error_count = error_count + 1
                    print(
                        f"Deviation! Err=%i Expected=%i Received=%i "
                        "Packets=%li PacketsSinceLast=%li "
                        "SampleJump=%i PacketsLost=%i Bytes=%i\n",
                        error_count,
                        spad_tracker,
                        spad_count,
                        rx_packets - 1,
                        rx_packets - 1 - rx_packets_last_error,
                        (spad_count - spad_tracker),
                        (spad_count - spad_tracker) / args.spp,
                        (args.ssb * (spad_count - spad_tracker)),
                    )
                    packets_lost = packets_lost + (spad_count - spad_tracker) / args.spp
                    rx_packets_last_error = rx_packets
                    spad_tracker = (
                        spad_count  # Ignore error, reinitialise tracker variable
                    )
                    if error_count > args.maxerrs:
                        print("Maximum error count reached, quitting\n")
                        exit(0)
                spad_tracker = spad_tracker + args.CountStep
    samples += args.spp

    if args.output >= 0:
        print(args.outfd, read_size)

    if (rx_packets % 100) == 0:
        update_timer = time.time()
