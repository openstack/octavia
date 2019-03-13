#!/bin/bash

# USAGE: <certificate directory> <openssl.cnf (example in etc/certificate)
#Those are certificates for testing will be generated
#
#* ca_01.pem is a certificate authority file
#* server.pem combines a key and a cert from this certificate authority
#* client.key the client key
#* client.pem the client certificate
#
#You will need to copy them to places the agent_api server/client can find and
#specify it in the config.
#
#Example for client use:
#
#curl -k -v --key client.key --cacert ca_01.pem --cert client.pem https://0.0.0.0:9443/
#
#
#Notes:
#For production use the ca issuing the client certificate and the ca issuing the server cetrificate
#need to be different so a hacker can't just use the server certificate from a compromised amphora
#to control all the others.
#
#Sources:
#* https://communities.bmc.com/community/bmcdn/bmc_atrium_and_foundation_technologies/
#discovery/blog/2014/09/03/the-pulse-create-your-own-personal-ca-with-openssl
#  This describes how to create a CA and sign requests
#* https://www.digitalocean.com/community/tutorials/
#openssl-essentials-working-with-ssl-certificates-private-keys-and-csrs -
#how to issue csr and much more

## Create CA

# Create directories
CERT_DIR=$1
OPEN_SSL_CONF=$2 # etc/certificates/openssl.cnf
VALIDITY_DAYS=${3:-18250} # defaults to 50 years

echo $CERT_DIR


mkdir -p $CERT_DIR
cd $CERT_DIR
mkdir newcerts private
chmod 700 private

# prepare files
touch index.txt
echo 01 > serial


echo "Create the CA's private and public keypair (2k long)"
openssl genrsa -passout pass:foobar -des3 -out private/cakey.pem 2048

echo "You will be asked to enter some information about the certificate."
openssl req -x509 -passin pass:foobar -new -nodes -key private/cakey.pem \
        -config $OPEN_SSL_CONF \
        -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" \
        -days $VALIDITY_DAYS \
        -out ca_01.pem


echo "Here is the certificate"
openssl x509 -in ca_01.pem -text -noout


## Create Server/Client CSR
echo "Generate a server key and a CSR"
openssl req \
       -newkey rsa:2048 -nodes -keyout client.key \
       -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" \
       -out client.csr

echo "Sign request"
openssl ca -passin pass:foobar -config $OPEN_SSL_CONF -in client.csr \
           -days $VALIDITY_DAYS -out client-.pem -batch

echo "Generate single pem client.pem"
cat client-.pem client.key > client.pem

echo "Note: For production use the ca issuing the client certificate and the ca issuing the server"
echo "certificate need to be different so a hacker can't just use the server certificate from a"
echo "compromised amphora to control all the others."
echo "To use the certificates copy them to the directory specified in the octavia.conf"
