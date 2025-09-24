#define __STDC_FORMAT_MACROS 1
#include <iostream>
#include <string>
#include <vector>
#include <CLI/CLI.hpp>
#include <common/Socket.h>
#include <common/Timer.h>
#include "rt.h"

#ifdef _WIN32
  #include <winsock2.h>
  #pragma comment(lib, "ws2_32.lib") // Link with the Winsock library
#else
  #include <stdio.h>
  #include <unistd.h>
#endif

// Get current date/time, format is YYYY-MM-DD.HH:mm:ss
const std::string currentDateTime() {
    time_t     now = time(0);
    struct tm  tstruct;
    char       buf[80];
    tstruct = *localtime(&now);
    // Visit http://en.cppreference.com/w/cpp/chrono/c/strftime
    // for more information about date/time format
    strftime(buf, sizeof(buf), "%Y-%m-%d.%X", &tstruct);

    return buf;
}


struct {
  int UDPPort{9000};
  int DataSize{9000};
  int SocketBufferSize{2000000};
  int SamplesPerPacket{1};
  int SampleSizeBytes{64};
  int CountColumn{-1};
  int CountStep{1};
  int RtPrio{0};
  int outfd{-1};
  int quiet{0};
  int maxerrs{9};
  uint64_t maxsamples{0};
  std::string local_address{"0.0.0.0"};
  int verbose{0};
} Settings;
  
void fmtElapsedTime(char *str, int tick, int tock) {
  int elapsed = tock - tick;
  int hours = elapsed / 3600;
  
  elapsed %= 3600;
  int minutes = elapsed / 60 ;
 
  elapsed %= 60;
  int seconds = elapsed;
  
  snprintf(str,10,"%02i:%02i:%02i",hours,minutes,seconds);  
}

CLI::App app{"UDP receiver with 32 bit sequence number check."};

int main(int argc, char *argv[]) {

    #ifdef _WIN32
      // Must initialize winsock
      WSADATA wsaData;
      int iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
      if (iResult != 0) {
        printf("WSAStartup failed: %d\n", iResult);
        return 1;
      }
    #endif

    app.add_option("-p, --port", Settings.UDPPort, "UDP receive port")->capture_default_str();
    //app.add_option("-s, --size", Settings.DataSize, "User data size")->capture_default_str();
    app.add_option("-b, --socket_buffer_size", Settings.SocketBufferSize, "socket buffer size (bytes)")->capture_default_str();
    app.add_option("--spp", Settings.SamplesPerPacket, "Samples per packet")->capture_default_str();
    app.add_option("--ssb", Settings.SampleSizeBytes, "Sample size (bytes)")->capture_default_str();
    app.add_option("-c, --count_column", Settings.CountColumn, "Count column (indexed from 0)")->capture_default_str();
    app.add_option("-t, --step", Settings.CountStep, "Count step (default:1), but may be decimated")->capture_default_str();
    app.add_option("-R, --rt_prio", Settings.RtPrio, "set POSIX RT priority (0: no set)")->capture_default_str();
    app.add_option("-o, --output", Settings.outfd, "1: output data to stdout")->capture_default_str();
    app.add_option("-q, --quiet", Settings.quiet, "1: stop reporting")->capture_default_str();
    app.add_option("-S, --max_samples", Settings.maxsamples, "stop after this many samples, 0: no limit")->capture_default_str();
    app.add_option("-M, --max_errs", Settings.maxerrs, "stop after this many errors")->capture_default_str();
    app.add_option("-a, --local_address", Settings.local_address, "optional local address\neg multiple NICs, one port")->capture_default_str();
    app.add_option("-v, --verbose", Settings.verbose, "increase to get more chatty")->capture_default_str();    CLI11_PARSE(app, argc, argv);

    static const int BUFFERSIZE{9200};
    char buffer[BUFFERSIZE];
    uint64_t RxBytesTotal{0};
    uint64_t RxBytes{0};
    uint64_t RxPackets{0};
    uint64_t RxPacketsLastError{0};
    uint32_t SpadTracker{1};
    uint32_t SpadCount{1};
    uint32_t PktsLost{0};
    int ErrCount{0};
    int SpadIndex{0};
    char elapsed_str[10];
    const int intervalUs = 10000000;
    const int interval_s = intervalUs / 1000000;
    const int B1M = 1000000;
    time_t tick{0};
    time_t tock{0};
    bool deviation = false;

    if (Settings.RtPrio){
        goRealTime(Settings.RtPrio);
    }
    Socket::Endpoint local(Settings.local_address, Settings.UDPPort);
    UDPReceiver Receive(local);
    Receive.setBufferSizes(Settings.SocketBufferSize, Settings.SocketBufferSize);
    Receive.setRecvTimeout(30, 0); // set a 30 second timeout on socket
    Receive.printBufferSizes();

    Settings.DataSize = Settings.SampleSizeBytes*Settings.SamplesPerPacket;

    Timer UpdateTimer;
    auto USecs = UpdateTimer.timeus();

    // Print the config as a string (can also be used to save the config to a file)
    std::cout << "--- Configuration from arguments ---" << std::endl;
    std::string config_string = app.config_to_str();
    std::cout << config_string << std::endl;

    // Print the config to a string with any default arguments included
    std::cout << "--- Configuration from defaults ---" << std::endl;
    std::string full_config_string = app.config_to_str(true, true);
    std::cout << full_config_string << std::endl;


    for (uint64_t samples = 0;
         Settings.maxsamples == 0 || samples < Settings.maxsamples;
         samples+=Settings.SamplesPerPacket)
    {
        int ReadSize = Receive.receive(buffer, BUFFERSIZE);
        if (ReadSize == -1) {
            printf("exiting as no data received...");
            exit(1);
        }

        assert(ReadSize > 0);
        assert(ReadSize == Settings.DataSize);

        RxBytes += ReadSize;
        RxPackets++;
        if (RxPackets == 1){
            tick = time(0);
            printf("tick");
        }

        if (Settings.CountColumn >= 0){
            // Grab the first SPAD Count in case we're not starting from 1
            if (RxPackets == 1) {
                SpadTracker = *((uint32_t *)( buffer + 4*Settings.CountColumn ));
            }

            for (int i = 0; i <= Settings.SamplesPerPacket-1; i++) {
                SpadIndex = i*Settings.SampleSizeBytes + 4*Settings.CountColumn;

                SpadCount = *((uint32_t *)( buffer + SpadIndex ));
                if ((Settings.verbose && samples+i < 5) || deviation == true) {
                    fprintf(stderr, "%#010x    %i %s\n", SpadCount, SpadCount, deviation? "dev":"ini");
                deviation = false;
                }
                if (SpadTracker != SpadCount) {
                    deviation = true;
                    ErrCount = ErrCount + 1;
                    fprintf(stderr, "Deviation! Err=%i Expected=%i Received=%i " \
                            "Packets=%li PacketsSinceLast=%li " \
                            "SampleJump=%i PacketsLost=%i Bytes=%i\n", 
                            ErrCount,
                            SpadTracker,
                            SpadCount,
                            RxPackets-1,
                            RxPackets-1-RxPacketsLastError,
                            (SpadCount - SpadTracker),
                            (SpadCount - SpadTracker)/Settings.SamplesPerPacket, 
                            (Settings.SampleSizeBytes * (SpadCount - SpadTracker)));
                    fflush(stderr);
                    PktsLost = PktsLost + (SpadCount - SpadTracker)/Settings.SamplesPerPacket;
                    RxPacketsLastError = RxPackets;
                    SpadTracker = SpadCount; // Ignore error, reinitialise tracker variable
                    if (ErrCount > Settings.maxerrs) {
                        fprintf(stderr, "Maximum error count reached, quitting\n");
                        exit(0);
                    }
                }
                SpadTracker = SpadTracker + Settings.CountStep;
            }
        }
        if (Settings.outfd >= 0){
            #ifdef _WIN32
              // TODO: implement on windows
              printf("Not implemented on windows version");
            #else
              write(Settings.outfd, buffer, ReadSize);
            #endif
        }
        if ((RxPackets % 100) == 0){
            USecs = UpdateTimer.timeus();
        }

        if (!Settings.quiet && USecs >= intervalUs) {
            RxBytesTotal += RxBytes;
            time_t tock = time(0);
            fmtElapsedTime(elapsed_str,tick,tock);
            fprintf(stderr, "%s ", currentDateTime().c_str());
            if (Settings.CountColumn >= 0){
                // TODO: Fix floating point misbehaviour on the PER calculation
                fprintf(stderr, "RxRate: %" PRIu64 " MB/s (total: %" PRIu64 " MB) Elapsed %s PktRec = %i ErrCount = %i PktsLost = %i PER %4.3e\n",
                        RxBytes / B1M / interval_s,
                        RxBytesTotal / B1M, elapsed_str,
                        RxPackets, 
                        ErrCount,
                        PktsLost,
                        (1.0 * PktsLost / (RxPackets + PktsLost)));
            } else {
                    if (USecs == 0) {  // protect against divide by zero
                        fprintf(stderr, "Rx rate: %.2f Mbps, rx %" PRIu64 " MB/s (total: %" PRIu64 " MB), Elapsed %s, PktRec = %i\n",
                                RxBytes * 8.0 / B1M,
                                RxBytes / B1M / interval_s,
                                RxBytesTotal / B1M,
                                elapsed_str, 
                                RxPackets);
                    } else {
                        fprintf(stderr, "Rx rate: %.2f Mbps, rx %" PRIu64 " MB/s (total: %" PRIu64 " MB), Elapsed %s, PktRec = %i\n",
                                RxBytes * 8.0 / (USecs / 1000000.0) / B1M,
                                RxBytes / B1M / interval_s,
                                RxBytesTotal / B1M,
                                elapsed_str,
                                RxPackets);
                    }
            }
            RxBytes = 0;
            UpdateTimer.now();
            USecs = UpdateTimer.timeus();
        }
    
  } // for (samples)

    #ifdef _WIN32
    // clean up winsock
      WSACleanup();
    #endif

    return 0;
}
