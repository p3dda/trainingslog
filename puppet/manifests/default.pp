Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

exec { 'apt-get update':
  command => 'apt-get update',
  timeout => 60,
  tries   => 3
}

package { ['vim', 'python-django', 'python-dateutil']:
  ensure  => 'installed',
  require => Exec['apt-get update'],
}

class {'nginx': }

nginx::resource::vhost {'trainingslog':
  listen_port => 8000,
  proxy => 'http://127.0.0.1:8888',
  add_header => {'X-Static' => 'miss'},
  proxy_set_header => ['Host $http_host']
}

nginx::resource::location { 'trainingslog_static':
  ensure => present,
  location => '/static',
  vhost => 'trainingslog',
  www_root => '/vagrant/'
}

nginx::resource::location { 'trainingslog_media':
  ensure => present,
  location => '/media',
  vhost => 'trainingslog',
  www_root => '/vagrant/'
}
