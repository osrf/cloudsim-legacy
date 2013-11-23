node default {
#    file { '/etc/network/interfaces':
#        path => "/etc/network/interfaces",
#        owner => "root",
#        group => "root",
#        mode => 644,
#        source => 'puppet:///modules/network/interfaces';
#    }

    apt::source { 'openstack-grizzly':
        location => 'http://ubuntu-cloud.archive.canonical.com/ubuntu',
        release => 'precise-updates/grizzly',
        repos => 'main',
        required_packages => 'ubuntu-cloud-keyring',
    }

    package {
        'molly-guard': ensure => latest;
    }

    # Use Apache to serve Horizon (Openstack Dashboard)
    include 'apache'

    # Openstack
    class { 'openstack::all':
        public_address => $fqdn,
        public_interface => 'eth0',
        private_interface => 'br100',
        internal_address => '127.0.0.1',
        admin_email => 'esteve@apache.org',
        admin_password => 'cloudsim_admin_password',
        keystone_admin_token => 'cloudsim_keystone_admin_token',
        nova_user_password => 'cloudsim_nova_user_password',
        glance_user_password => 'cloudsim_glance_user_password',
        cinder_user_password => 'cloudsim_cinder_user_password',
        rabbit_password => 'cloudsim_rabbit_password',
        rabbit_user => 'cloudsim_rabbit',
        libvirt_type => 'kvm',
        fixed_range => '10.0.0.0/24',
        verbose => true,
        auto_assign_floating_ip => false,
        mysql_root_password => 'mysql',
        keystone_db_password => 'cloudsim_keystone_db_password',
        glance_db_password => 'cloudsim_glance_db_password',
        nova_db_password => 'cloudsim_nova_db_password',
        cinder_db_password => 'cloudsim_cinder_db_password',
        secret_key => '12345',
        quantum => false,
        purge_nova_config => true, 
        vnc_enabled => false,
        require => [Apt::Source['openstack-grizzly']],
    }

    class { 'openstack::auth_file':
        require => Class["openstack::all"],
        admin_password       => 'cloudsim',
        controller_node      => '127.0.0.1',
    }
}
