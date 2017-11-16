#!/bin/bash
nc_cmd=`which nc`
$nc_cmd -uzv -w1 $1 $2 > /dev/null
exit $?
