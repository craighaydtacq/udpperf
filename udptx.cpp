/** Copyright (C) 2016 - 2020 European Spallation Source ERIC */
#define __STDC_FORMAT_MACROS 1

#include <CLI/CLI.hpp>
#include <cinttypes>
#include <iostream>
#include <common/Socket.h>
#include <common/TSCTimer.h>
#include <common/Timer.h>
#include <stdio.h>
#include <chrono>
#include <thread>


#ifdef _WIN32

#else
  #include <unistd.h>
#endif


struct {
  std::string IpAddress{"127.0.0.1"};
  int UDPPort{9000};
  int DataSize{9000};
  int SocketBufferSize{4000000};
} Settings;

CLI::App app{"UDP transmitter with 32 bit sequence number."};

char Buffer[10000];


// Assumes you have an rdtsc() function available
// This function should be called once at the start of your program.
uint64_t get_tsc_freq() {
    auto start = std::chrono::high_resolution_clock::now();
    uint64_t tsc_start = rdtsc();

    // Sleep for a fixed, known duration
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    uint64_t tsc_end = rdtsc();
    auto end = std::chrono::high_resolution_clock::now();

    uint64_t tsc_delta = tsc_end - tsc_start;
    double time_delta_s = std::chrono::duration<double>(end - start).count();

    return static_cast<uint64_t>(tsc_delta / time_delta_s);
}


int main(int argc, char *argv[]) {

    uint64_t tsc_freq_hz = get_tsc_freq();
    const uint64_t reporting_interval_ticks = tsc_freq_hz; // For a 1-second interval

  #ifdef _WIN32
    // Must initialize winsock
    WSADATA wsaData;
    int iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (iResult != 0) {
      printf("WSAStartup failed: %d\n", iResult);
      return 1;
    }
  #endif

  app.add_option("-p, --port", Settings.UDPPort, "UDP transmit port")->capture_default_str();
  app.add_option("-d, --data_size", Settings.DataSize, "Size of UDP payload (bytes)")->capture_default_str();
  app.add_option("-b, --socket_buffer_size", Settings.SocketBufferSize, "socket buffer size (bytes)")->capture_default_str();
  CLI11_PARSE(app, argc, argv);

  uint64_t TxBytesTotal{0};
  uint64_t TxBytes{0};
  uint64_t TxPackets{0};
  const int B1M{1000000};

  Socket::Endpoint Local("0.0.0.0", 0);
  Socket::Endpoint Remote(Settings.IpAddress.c_str(), Settings.UDPPort);
  UDPTransmitter UDPTx(Local, Remote);
  UDPTx.setBufferSizes(Settings.SocketBufferSize, Settings.SocketBufferSize);
  UDPTx.printBufferSizes();


  Timer RateTimer;
  TSCTimer ReportTimer;
  uint32_t SeqNo{1};

  // Print the config as a string (can also be used to save the config to a file)
  std::cout << "--- Configuration from arguments ---" << std::endl;
  std::string config_string = app.config_to_str();
  std::cout << config_string << std::endl;

  // Print the config to a string with any default arguments included
  std::cout << "--- Configuration from defaults ---" << std::endl;
  std::string full_config_string = app.config_to_str(true, true);
  std::cout << full_config_string << std::endl;

  for (;;) {
    *((uint32_t *)Buffer) = SeqNo;
    auto TxTmpBytes = UDPTx.send(Buffer, Settings.DataSize);

    if (TxTmpBytes > 0) {
      SeqNo++;
      TxPackets++;
      TxBytes += TxTmpBytes;
    }

    if (ReportTimer.timetsc() >= reporting_interval_ticks) {
      auto USecs = RateTimer.timeus();
      TxBytesTotal += TxBytes;
      printf("Tx rate: %f Mbps, %f pps, tx %llu MB (total: %llu MB) %llu usecs\n",
             TxBytes * 8.0 / USecs,
             TxPackets * 1000000.0 / USecs,
             TxBytes / B1M,
             TxBytesTotal / B1M,
             USecs);
      TxBytes = 0;
      TxPackets = 0;
      RateTimer.now();
      ReportTimer.now();
    }
  }

  #ifdef _WIN32
    // clean up winsock
    WSACleanup();
  #endif
}
