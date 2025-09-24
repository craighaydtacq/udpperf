# udpperf

A simple UDP transmitter and receiver with sequence numbers added
to the otherwise unused payload. This allows detection of packet loss
and calculation of packet error rates (PER).

The code is collected from two publicly available repositories.

CLI library header files comes from https://github.com/CLIUtils/CLI11

All other files are adapted from https://github.com/ess-dmsc/event-formation-unit

## Build

    > mkdir build
    > cd build
    > cmake -DCMAKE_BUILD_TYPE=Release ..
    > make

## Run
On one host

    > ./udprx

On another host

    > ./udptx



# Windows compilation
You need to have installed the Visual Studio C++ Build Tools.

They can be found on this page:
https://visualstudio.microsoft.com/downloads/

Or a direct link to installer:

https://aka.ms/vs/17/release/vs_BuildTools.exe

Only the basic installation is required, no additional features (they can be unticked during the installation process).

Once installed, open a "Developer Command Prompt for VS 2022" from the Start Menu, navigate to the udpperf directory and run this command:

```
cl /std:c++17 /I. /EHsc udprx.cpp common\Socket.cpp common\Timer.cpp ws2_32.lib /Feudprx.exe
```

To compile the companion TX program run:
```
cl /std:c++17 /I. /EHsc udptx.cpp common\Socket.cpp common\Timer.cpp ws2_32.lib /Feudptx.exe
```
