#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

echo "!!!!!!!!!!!!!!!Do not use this script for deployments!!!!!!!!!!!!!"
echo "Single CA mode is insecure, do not use this! It is for testing only."
echo "Please use the Octavia Certificate Configuration guide:"
echo "https://docs.openstack.org/octavia/latest/admin/guides/certificates.html"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

# This script produces weak security PKI to save resources in the test gates.
# A single CA should never be used in a production deployment. This script
# exists purely to test legacy migrations / deployments where someone
# acidently used a single CA.

set -x -e

CA_PATH=single_ca

mkdir $CA_PATH
chmod 700 $CA_PATH
cd $CA_PATH

mkdir -p etc/octavia/certs
chmod 700 etc/octavia/certs

###### Client Root CA
mkdir client_ca
cd client_ca
mkdir certs crl newcerts private
chmod 700 private
touch index.txt
echo 1000 > serial

# Create the client CA private key
# Note: This uses short key lengths to save entropy in the test gates.
#       This is not recommended for deployment use!
openssl genrsa -aes128 -out private/ca.key.pem -passout pass:not-secure-passphrase 1024
chmod 400 private/ca.key.pem

# Create the client CA root certificate
openssl req -config ../../openssl.cnf -key private/ca.key.pem -new -x509 -sha256 -extensions v3_ca -days 7300 -out certs/ca.cert.pem -subj "/C=US/ST=Oregon/L=Corvallis/O=OpenStack/OU=Octavia/CN=ClientRootCA" -passin pass:not-secure-passphrase

###### Client Intermediate CA
mkdir intermediate_ca
mkdir intermediate_ca/certs intermediate_ca/crl intermediate_ca/newcerts intermediate_ca/private
chmod 700 intermediate_ca/private
touch intermediate_ca/index.txt
echo 1000 > intermediate_ca/serial

# Create the client intermediate CA private key
# Note: This uses short key lengths to save entropy in the test gates.
#       This is not recommended for deployment use!
openssl genrsa -aes128 -out intermediate_ca/private/intermediate.ca.key.pem -passout pass:not-secure-passphrase 1024
chmod 400 intermediate_ca/private/intermediate.ca.key.pem

# Create the client intermediate CA certificate signing request
openssl req -config ../../openssl.cnf -key intermediate_ca/private/intermediate.ca.key.pem -new -sha256 -out intermediate_ca/client_intermediate.csr -subj "/C=US/ST=Oregon/L=Corvallis/O=OpenStack/OU=Octavia/CN=ClientIntermediateCA" -passin pass:not-secure-passphrase

# Create the client intermediate CA certificate
openssl ca -config ../../openssl.cnf -name CA_intermediate -extensions v3_intermediate_ca -days 3650 -notext -md sha256 -in intermediate_ca/client_intermediate.csr -out intermediate_ca/certs/intermediate.cert.pem -passin pass:not-secure-passphrase -batch

# Create the client CA certificate chain
cat intermediate_ca/certs/intermediate.cert.pem certs/ca.cert.pem > intermediate_ca/ca-chain.cert.pem

###### Create the client key and certificate
# Note: This uses short key lengths to save entropy in the test gates.
#       This is not recommended for deployment use!
openssl genrsa -aes128 -out intermediate_ca/private/controller.key.pem -passout pass:not-secure-passphrase 1024
chmod 400 intermediate_ca/private/controller.key.pem

# Create the client controller certificate signing request
openssl req -config ../../openssl.cnf -key intermediate_ca/private/controller.key.pem -new -sha256 -out intermediate_ca/controller.csr -subj "/C=US/ST=Oregon/L=Corvallis/O=OpenStack/OU=Octavia/CN=OctaviaController" -passin pass:not-secure-passphrase

# Create the controller client certificate
openssl ca -config ../../openssl.cnf -name CA_intermediate -extensions usr_cert -days 1825 -notext -md sha256 -in intermediate_ca/controller.csr -out intermediate_ca/certs/controller.cert.pem -passin pass:not-secure-passphrase -batch

# Build the cancatenated client cert and key
openssl rsa -in intermediate_ca/private/controller.key.pem -out intermediate_ca/private/client.cert-and-key.pem -passin pass:not-secure-passphrase

cat intermediate_ca/certs/controller.cert.pem >> intermediate_ca/private/client.cert-and-key.pem

# We are done with the client CA
cd ..

###### Stash the octavia default cert files
cp client_ca/intermediate_ca/ca-chain.cert.pem etc/octavia/certs/client_ca.cert.pem
chmod 444 etc/octavia/certs/client_ca.cert.pem
cp client_ca/intermediate_ca/private/client.cert-and-key.pem etc/octavia/certs/client.cert-and-key.pem
chmod 600 etc/octavia/certs/client.cert-and-key.pem
cp client_ca/intermediate_ca/ca-chain.cert.pem etc/octavia/certs/server_ca.cert.pem
chmod 444 etc/octavia/certs/server_ca.cert.pem
cp client_ca/intermediate_ca/private/intermediate.ca.key.pem etc/octavia/certs/server_ca.key.pem
chmod 600 etc/octavia/certs/server_ca.key.pem

##### Validate the Octavia PKI files
set +x
echo "################# Verifying the Octavia files ###########################"
openssl verify -CAfile etc/octavia/certs/client_ca.cert.pem etc/octavia/certs/client.cert-and-key.pem
openssl verify -CAfile etc/octavia/certs/server_ca.cert.pem etc/octavia/certs/server_ca.cert.pem

echo "!!!!!!!!!!!!!!!Do not use this script for deployments!!!!!!!!!!!!!"
echo "Single CA mode is insecure, do not use this! It is for testing only."
echo "Please use the Octavia Certificate Configuration guide:"
echo "https://docs.openstack.org/octavia/latest/admin/guides/certificates.html"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
