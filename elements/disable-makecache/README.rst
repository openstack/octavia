This element disables the dnf makecache hourly timer.

The amphora typically do not have internet access nor access to DNS servers.
We want to disable this makecache timer to stop the amphora from attempting
to update/download the dnf cache every hour. Without this element it will
run and log a failure every hour.
