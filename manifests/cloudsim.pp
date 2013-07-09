Exec {
  path => "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}

exec { 'apt-update':
  command => '/usr/bin/apt-get update';
}

Exec["apt-update"] -> Package <| |>

node default {

    package {
        'redis-server': ensure=> latest;
        'python-redis': ensure => latest;
        'expect': ensure => latest;
        'wget': ensure => latest;
        'tar': ensure => latest;
        'bzip2': ensure => latest;
        'git': ensure => latest;
    }

    cloudsim::install { "cloudsim": version => "1.5.2"; }

    class {'python':
        version => 'system',
        virtualenv => true,
    }

    puppet::vcsrepo::install { "cloudsim": }

    puppet::python::install { "cloudsim": }

    devstack::setup { "cloudsim": }
}

define network::setup() {
    file {
        '/etc/network/interfaces':
            path => '/etc/network/interfaces',
            owner => 'root',
            group => 'root',
            mode => 644,
            source => 'puppet:///modules/network/interfaces';
    }
}


define devstack::clone() {
    vcsrepo { "/home/vagrant/devstack":
        ensure => present,
        provider => git,
        source => "git://github.com/openstack-dev/devstack.git",
        user => 'vagrant',
        require => Package['git'];
    }
}

define devstack::setup() {
    file {'/home/vagrant/devstack/localrc':
            path => '/home/vagrant/devstack/localrc',
            owner => 'vagrant',
            group => 'vagrant',
            mode => 644,
            source => 'puppet:///modules/devstack/localrc',
            require => Devstack::Clone["${name}"];
    }

    devstack::clone { "${name}":
        require => Puppet::Vcsrepo::Install["${name}"];
    }

    exec {"devstack-unstack-${name}":
        command => "/home/vagrant/devstack/unstack.sh",
        user => "vagrant",
        require => Devstack::Clone["${name}"];
    }

    exec {"devstack-stack-${name}":
        command => "/home/vagrant/devstack/stack.sh",
        user => "vagrant",
        require => [Devstack::Clone["${name}"], Exec["devstack-unstack-${name}"], File['/home/vagrant/devstack/localrc']];
    }
}

define puppet::python::install() {
    vcsrepo { "/etc/puppet/modules/python":
        ensure => present,
        provider => git,
        source => "git://github.com/stankevich/puppet-python.git",
        require => [Package['git'], Puppet::Vcsrepo::Install[$name]];
    }
}

#    exec {"puppet-python-install-${name}":
#        command => "git clone git://github.com/stankevich/puppet-python.git ~/.puppet/modules/python",
#        require => [Package['git'], Puppet::Vcsrepo::Install[$name]];
#    }
#}

define puppet::vcsrepo::install() {
    file { "/etc/puppet/modules" : ensure => directory }

    exec {"puppet-vcsrepo-install-${name}":
        command => "/opt/vagrant_ruby/bin/puppet module install puppetlabs/vcsrepo",
        require => [File["/etc/puppet/modules"], Package['git']],
        creates => "/etc/puppet/modules/vcsrepo/Gemfile";
    }
}

define cloudsim::download($version, $target_dir) {
    exec {"download-latest-cloudsim-${name}":
        command => "wget -O ${target_dir}/cloudsim-${version}.tar.bz2 http://gazebosim.org/assets/distributions/cloudsim-${version}.tar.bz2",
        creates => "${target_dir}/cloudsim-${version}.tar.bz2",
        require => Package['wget'];
    }
}

define cloudsim::unpack($version, $target_dir) {
    exec {"unpack-latest-cloudsim-${name}":
        command => "tar -xjf ${target_dir}/cloudsim-${version}.tar.bz2 -C ${target_dir}",
        creates => "${target_dir}/cloudsim-${version}/VERSION",
        require => Package['tar', 'bzip2'];
    }
}

define cloudsim::install($version, $target_dir='/var/tmp') {
    cloudsim::download {$name: version => $version, target_dir => $target_dir; }

    cloudsim::unpack {$name: version => $version, target_dir => $target_dir, require=> Cloudsim::Download[$name]; }
}
