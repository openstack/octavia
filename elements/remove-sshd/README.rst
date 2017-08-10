===========
remove-sshd
===========
This element ensures that openssh server is uninstalled and will not start.

Note
----
Most cloud images come with the openssh server service installed and enabled
during boot. However, sometimes this is not appropriate. In these cases,
using this element may be helpful to ensure your image will not accessible via
SSH.
