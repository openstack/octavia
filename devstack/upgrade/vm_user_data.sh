#!/bin/sh -v
Body=$(hostname)
Response="HTTP/1.1 200 OK\r\nContent-Length: ${#Body}\r\n\r\n$Body"
while true ; do echo -e $Response | nc -llp 80; done
