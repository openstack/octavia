This file describes how to use Vagrant (http://www.vagrantup.com) to
create a devstack virtual machine that contains two nova instances
running a simple web server and a working Neutron LBaaS Version 2 load
balancer backed by Octavia.

1) Install vagrant on your host machine.  Vagrant is available for
Windows, Mac OS, and most Linux distributions.  Download and install
the package appropriate for your system.  On Ubuntu, simply type:

    sudo apt-get install vagrant

2) copy 'Vagrantfile' from this directory to any appropriate directory
and run 'vagrant up':

    mkdir $HOME/lbaas-octavia-vagrant            # or any other appropriate directory
    cp Vagrantfile $HOME/lbaas-octavia-vagrant
    cd $HOME/lbaas-octavia-vagrant
    vagrant up

3) Wait for the vagrant VM to boot and install, typically 20-30 minutes

4) SSH into the vagrant box

    vagrant ssh

5) Determine the loadbalancer IP:

    source openrc admin admin
    neutron lbaas-loadbalancer-show lb1 | grep vip_address

6) make HTTP requests to test your load balancer:

        curl <LB_IP>

where <LB_IP> is the VIP address for lb1.  The subsequent invocations of
"curl <LB_IP>" should demonstrate that the load balancer is alternating
between two member nodes.
