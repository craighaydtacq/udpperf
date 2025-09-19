import argparse
import socket
import time
import struct


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


class Timer:
    def __init__(self):
        # Store the initial time in nanoseconds
        self.t1 = time.perf_counter_ns()

    def now(self):
        self.t1 = time.perf_counter_ns()

    def timeus(self):
        # Get the current time in nanoseconds
        t2 = time.perf_counter_ns()
        
        # Calculate the difference and convert to microseconds
        # 1 microsecond = 1000 nanoseconds
        return (t2 - self.t1) // 1000

def elapsed_time(t0, t1):
    return t1 - t0

if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = 53676
    PACKET_SIZE = 9000
    SOCKET_BUFFER_SIZE = 2000000
    SAMPLES_PER_PACKET = 1
    SAMPLE_SIZE_IN_BYTES = 64
    MAX_ERRORS = 9

    parser = argparse.ArgumentParser(
        prog="udprx", description="Receives UDP packets", epilog="UDP packet receiver"
    )

    parser.add_argument(
        "-p",
        "--port",
        default=UDP_PORT,
        type=int,
        help=f"UDP receive port (default: {UDP_PORT})",
    )
    parser.add_argument(
        "-s",
        "--size",
        default=PACKET_SIZE,
        type=int,
        help=f"User data size (default: {PACKET_SIZE})",
    )
    parser.add_argument(
        "-b,",
        "--socket_buffer_size",
        default=SOCKET_BUFFER_SIZE,
        type=int,
        help=f"socket buffer size in bytes (default: {SOCKET_BUFFER_SIZE})",
    )
    parser.add_argument("--spp", default=SAMPLES_PER_PACKET, type=int, help=f"Samples per packet (default: {SAMPLES_PER_PACKET})")
    parser.add_argument("--ssb", default=SAMPLE_SIZE_IN_BYTES, type=int, help=f"Sample size in bytes (default: {SAMPLE_SIZE_IN_BYTES})")
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
        "-M",
        "--max_errs",
        default=MAX_ERRORS,
        type=int,
        help=f"stop after this many errors (default: {MAX_ERRORS})",
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

    data_size = args.ssb * args.spp
    rx_bytes = 0
    rx_packets = 0
    rx_bytes_total = 0
    deviation = False
    error_count = 0
    rx_packets_last_error = 0
    packets_lost = 0
    interval_us = 10000000
    interval_s = interval_us / 1000000
    B1M = 1000000

    update_timer = Timer()
    usecs = update_timer.timeus()

    # print(f"Expecting data size: {data_size}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.local_address, args.port))

    if args.rt_prio:
        go_realtime(args.rt_prio)

    # TODO: figure out how to make this run forever is max_samples isn't set
    samples = 0
    while True:
        # Condition to stop the loop
        if args.max_samples != 0 and samples >= args.max_samples:
            print(f"Reached max samples ({samples}). Stopping.")
            break

        data, addr = sock.recvfrom(args.socket_buffer_size)

        read_size = len(data)

        rx_bytes += read_size
        rx_packets += 1
        if rx_packets == 1:
            tick = time.time()

        if args.count_column >= 0:
            # Grab the first SPAD Count in case we're not starting from 1
            if rx_packets == 1:
                # print("rx_packets == 1")
                offset = 4 * args.count_column
                spad_tracker = struct.unpack_from("<I", data, offset)[0]
                # print(f"spad_tracker = {spad_tracker}")

            for i in range(0, args.spp):
                # print(f"i={i}")
                spad_index = i * args.ssb + 4 * args.count_column
                # print(f"spad_index = {spad_index} and len(data)={len(data)}")

                spad_count = struct.unpack_from("<I", data, spad_index)[0]
                # print(f"spad_index={spad_index}")
                # print(f"spad_count = {spad_count}")
                if (args.verbose and (samples + i < args.spp+1)) or deviation == True:
                    if deviation:
                        dev_or_ini = "dev"
                    else:
                        dev_or_ini = "ini"
                    print(f"{spad_count:010x} {spad_count} {dev_or_ini}")
                    deviation = False
                if (spad_tracker) != spad_count:
                    # print(f"spad_tracker=={spad_tracker} and spad_count={spad_count}")
                    deviation = True
                    error_count = error_count + 1
                    print(
                        f"Deviation! Err={error_count} Expected={spad_tracker} Received={spad_count} "
                        f"Packets={rx_packets-1} PacketsSinceLastError={rx_packets - 1 - rx_packets_last_error} "
                        f"SampleJump={spad_count - spad_tracker} PacketsLost={(spad_count - spad_tracker) // args.spp} BytesLost={args.ssb * (spad_count - spad_tracker)}\n",
                    )
                    packets_lost = packets_lost + (spad_count - spad_tracker) / args.spp
                    rx_packets_last_error = rx_packets
                    spad_tracker = spad_count  # Ignore error, reinitialise tracker variable
                    if error_count > args.max_errs:
                        print("Maximum error count reached, quitting\n")
                        exit(0)
                spad_tracker = spad_tracker + args.step
        samples += args.spp

        if args.output >= 0:
            raise NotImplementedError(
                "Outputting to stdout from this program is not yet implemented"
            )

        if (rx_packets % 100) == 0:
            usecs = update_timer.timeus()

        print(f"usecs={usecs} interval_us={interval_us}")
        if args.verbose and usecs >= interval_us:
            rx_bytes_total += rx_bytes
            tock = time.time()
            elapsed_str = elapsed_time(tick,tock)
            if (args.count_column >= 0):
                print(f"RxRate: % {rx_bytes / B1M / interval_s}MB/s (total: % {rx_bytes_total / B1M}  MB) Elapsed {elapsed_str} PktRec = {rx_packets} ErrCount = {error_count} PktsLost = {packets_lost} PER {(1.0 * packets_lost / (rx_packets + packets_lost))} \n")
            else:
                print(f"Rx rate: {rx_bytes * 8.0 / (usecs / 1000000.0) / B1M} Mbps, rx % {rx_bytes / B1M / interval_s} MB/s (total: % {rx_bytes_total / B1M} MB), Elapsed {elapsed_str} , PktRec = {rx_packets} \n")
            rx_bytes = 0
            update_timer.now()
            usecs = update_timer.timeus()
