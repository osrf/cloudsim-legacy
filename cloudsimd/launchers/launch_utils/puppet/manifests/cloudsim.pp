
node default {

    package {
        'redis-server': ensure=> latest;
        'python-redis': ensure => latest;
        'expect': ensure => latest;
        'wget': ensure => latest;
        'tar': ensure => latest;
        'bzip2': ensure => latest;
        'git': ensure => latest;
        'iptables-persistent': ensure => latest;
        'zip': ensure => latest;
        'boto' : provider => pip, ensure  => latest;
        'softlayer' : provider => pip, ensure  => latest;
        'ipython' : provider => pip, ensure  => latest;
    }

    cloudsim::install { "cloudsim": version => "1.7.3"; }

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
        require => Package['tar', 'bzip2'],
    }
}

define cloudsim::deploy($version, $target_dir, $authentication='-b') {
	
	exec {"deploy cloudsim":
		command => "${target_dir}/cloudsim-${version}/deploy.sh ${authentication}",
		creates => "/var/www-cloudsim-auth",
		require => Package['zip'],
	}
}

define cloudsim::install($version, $target_dir='/var/tmp') {
    	cloudsim::download {$name: version => $version, target_dir => $target_dir; }
    	cloudsim::unpack   {$name: version => $version, target_dir => $target_dir, require=> Cloudsim::Download[$name]; } 
		cloudsim::deploy   {$name: version => $version, target_dir => $target_dir, require=> cloudsim::unpack[$name];}
}

