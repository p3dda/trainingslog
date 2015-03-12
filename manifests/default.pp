Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

exec { 'apt-get update':
  command => 'apt-get update',
  timeout => 60,
  tries   => 3
}

package { ['vim', 'python-django', 'python-dateutil', 'python-requests', 'python-setuptools', 'python-crypto', 'python-pip']:
  ensure  => 'installed',
  require => Exec['apt-get update'],
  before  => Exec['pip_requirements_install']
}

exec { "pip_requirements_install":
  command => "pip install -r /vagrant/requirements.txt",
}
