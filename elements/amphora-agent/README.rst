Element to install an Octavia Amphora agent.

By default, it installs the agent from source. To enable installation from
distribution repositories, define the following:
    export DIB_INSTALLTYPE_amphora_agent=package

Note: this requires a system base image modified to include OpenStack
repositories
