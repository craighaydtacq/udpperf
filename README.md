# udpperf

A simple UDP transmitter and receiver with sequence numbers added
to the otherwise unused payload. This allows detection of packet loss
and calculation of packet error rates (PER).

The code is collected from two publicly available repositories.

CLI library header files comes from https://github.com/CLIUtils/CLI11

All other files are adapted from https://github.com/ess-dmsc/event-formation-unit


## C++ version
### Build

    > mkdir build
    > cd build
    > cmake -DCMAKE_BUILD_TYPE=Release ..
    > make

### Run
On one host

    > ./udprx

On another host

    > ./udptx

## Python Port
This utility has been ported to Python for easy cross-platform use.

For high performance you should still compile the C++ version for your platform.

Compilation is currently supported for Linux platforms but could be easily adapted for others.

### Local test
To run a local test with a small test file available in this repo...

In one terminal run udprx:

```
python udprx.py --ssb 80 --spp 16 -c 16 -v 1
```

In another terminal run the test transmitter:

```
python udptx.py --ssb 80 --spp 16 udp_test_48_samples.bin
```

### Run for real
If for example you had a 32 channel system of 16-bits per channel and 4 SPAD words...

```
32 chan x 2b = 64 
 4 SPAD x 4b = 16
```

sample size in bytes = 80

This gives a "count column" (-c) parameter of 16.
This parameter needs to point the program to the beginning of the SPAD longword
(i.e. skip 16 longwords before reaching the SPAD longword).

```
| CH1 | CH2 | .. | CH32 | SPAD | ...
  2b    2b    ..    2b
```

You would therefore run a `udprx.py` command with the following arguments:

```
python udprx.py --ssb 80 --spp 16 -c 16 -v 1
```

To see the full help for udprx.py type:

```
python udprx.py -h
```