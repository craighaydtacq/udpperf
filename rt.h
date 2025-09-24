
/* hello */

#ifndef __RT_H__
#define __RT_H__
#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32

#else
#include <sched.h>
#include <unistd.h>
#endif

#include <assert.h>
#include <sys/types.h>
#include <sys/stat.h>


void goRealTime(int sched_fifo_priority)
{
    #ifdef _WIN32
        printf("goRealTime not defined on Windows.");
    #else
        struct sched_param p = {};
        p.sched_priority = sched_fifo_priority;

        int rc = sched_setscheduler(0, SCHED_FIFO, &p);

        if (rc){
                perror("failed to set RT priority");
        }
    #endif
}



#endif
