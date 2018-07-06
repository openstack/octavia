This element removes any default network interfaces from the interface
configuration in the image. These are not needed in the amphora as cloud-init
will create the required default interface configuration files.

For Ubuntu this element will remove the network
configuration files from /etc/network/interfaces.d.
