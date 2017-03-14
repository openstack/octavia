This file describes how to use Vagrant (http://www.vagrantup.com) to
create a devstack virtual environment that contains two nova instances
running a simple web server and a working Neutron LBaaS Version 2 load
balancer backed by Octavia.

1) Install vagrant on your host machine.  Vagrant is available for
Windows, Mac OS, and most Linux distributions.  Download and install
the package appropriate for your system.  On Ubuntu, simply type:

    sudo apt-get install vagrant

2) copy 'Vagrantfile' from this directory to any appropriate directory

    mkdir $HOME/lbaas-octavia-vagrant            # or any other appropriate directory
    cp -rfp $HOME/lbaas-octavia-vagrant

3) Continue either by the single node deployment (6GB RAM minimum), or by the
multinode deployment (12GB RAM minimum).

Single node deployment
~~~~~~~~~~~~~~~~~~~~~~

1) Create and deploy the environment VM

    cd $HOME/lbaas-octavia-vagrant/single
    vagrant up

    Alternatively, you can specify the number of vcpus or memory:
    VM_CPUS=4 VM_MEMORY=8192 vagrant up

2) Wait for the vagrant VM to boot and install, typically 20-30 minutes

3) SSH into the vagrant box

    vagrant ssh

4) Continue on the common section below

Multinode
~~~~~~~~~

This will create an environment where the octavia services are replicated
across two nodes, and in front of the octavia api, an haproxy is configured
to distribute traffic among both API servers, and provide failure tolerance.

Please note that the database is a single mysql instance, with no clustering.

1) Create and deploy the environment VMs

   cd $HOME/lbaas-octavia-vagrant/multinode
   vagrant up main

2) Wait for the main node to be deployed, and then start the second node

   vagrant up second

3) Log in to the main node, and run local-manual.sh now that everything is
   deployed

   vagrant ssh main
   cd devstack
   ./local-manual.sh
   logout

4) SSH in any of the vagrant boxes:

   vagrant ssh main
   vagrant ssh second

4) Continue on the common section bellow

Common to multinode and single node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1) Determine the loadbalancer IP:

    source openrc admin admin
    neutron lbaas-loadbalancer-show lb1 | grep vip_address

2) make HTTP requests to test your load balancer:

        curl <LB_IP>

where <LB_IP> is the VIP address for lb1.  The subsequent invocations of
"curl <LB_IP>" should demonstrate that the load balancer is alternating
between two member nodes.
