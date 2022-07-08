Element to enable optimizations for vertical scaling

This element configures the Linux kernel to isolate all but the first
vCPU of the system, so that they are used by HAProxy threads exclusively.
It also installs and activates a customized TuneD profile that should further
tweak vertical scaling performance.
