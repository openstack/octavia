#!/bin/bash

GEN_DIR=/tmp/certs
rm -rf $GEN_DIR
bash ../../bin/create_certificates.sh $GEN_DIR $(pwd)/../../etc/certificates/openssl.cnf
for file in client.key client.pem ca_01.pem private/cakey.pem; do
    cp -v $GEN_DIR/$file certs/$file
done

echo ""
echo Validating client cert with CA:
openssl verify -verbose -CAfile certs/ca_01.pem certs/client.pem

echo ""
echo CA expiration time:
openssl x509 -enddate -noout -in certs/ca_01.pem

echo ""
echo Client cert expiration time:
openssl x509 -enddate -noout -in certs/client.pem

