# defaults
VM_MEMORY = ENV['VM_MEMORY'] || "8192"
VM_CPUS = ENV['VM_CPUS'] || "1"

def configure_providers(vm)

  vm.provider "virtualbox" do |vb, config|
     config.vm.box = "ubuntu/xenial64"
     vb.gui = true
     vb.memory = VM_MEMORY
     vb.cpus = VM_CPUS
  end

  vm.provider "libvirt" do |lb, config|
     config.vm.box = "celebdor/xenial64"
     config.vm.synced_folder './', '/vagrant', type: 'rsync'
     lb.nested = true
     lb.memory = VM_MEMORY
     lb.cpus = VM_CPUS
     lb.suspend_mode = 'managedsave'
  end
end
