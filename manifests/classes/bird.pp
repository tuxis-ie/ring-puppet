class bird_peers {

######
# add IPv4 peers here
# format is DESCR,IPv6,ASN
# note that DESCR must not contain spaces or other weird shit like dashes
#####

$lg_peers_v4 = [
'BIT1,213.136.1.132,12859',
'BLIX1,178.255.145.243,50304',
'BOXED_IT1,195.200.224.1,50156',
'DUOCAST1,89.188.4.1,31477',
'DUOCAST2,89.188.4.2,31477',
'GBXS1,193.27.64.13,9009',
'LEASEWEB1,62.212.80.80,16265',
'LEASEWEB2,85.17.100.100,16265',
'SIXDEGREES1,82.147.0.11,20547',
'SPACEDUMP1,212.63.222.254,30880',
'TDC1,194.100.40.50,3292',
'TILAA1,164.138.24.1,196752',
'TUXIS1,31.3.104.1,197731',
'YACAST1,213.205.109.251,24963',
'YOURORG1,216.14.98.5,19255',
]

#####
# add IPv6 peers here
# format is DESCR,IPv6,ASN
# note that DESCR must not contain spaces or other weird shit
#####

$lg_peers_v6 = [
'BIT1,2001:7b8:0:fffe::2,12859',
'TUXIS1,2a03:7900::1,197731',
'BLIX1,2A02:20C8:1F:1::4,50304',
'BOXED_IT1,2001:67c:344::1,50156',
'DUOCAST1,2A01:01B0:1::1,31477',
'DUOCAST2,2A01:01B0:1::2,31477',
'GBXS1,2a01:300::13,9009',
'LEASEWEB1,2001:1af8::62:212:80:80,16265',
'LEASEWEB2,2001:1af8::85:17:100:100,16265',
'SIXDEGREES1,2A02:298:80:1339::1,20547',
'SPACEDUMP1,2A01:298:FFFF:5::1,30880',
'TDC1,2001:6E8:8C0:100::2,3292',
'TILAA1,2a02:2770:1::1,196752',
'YACAST1,2a02:3e8::4,24963',
'YOURORG1,2001:4978:1:10::ffff,19255',
]

}

class bird {
    include bird_peers
    exec { "add_bird_repo":
        path    => "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        timeout => 3600,
        command => "add-apt-repository -y ppa:cz.nic-labs/bird; apt-get update",
        unless  => "/usr/bin/test -f /etc/apt/sources.list.d/cz_nic-labs-bird-precise.list",
        before  => Package["bird", "bird6"],
    }

    package { ["bird", "bird6"]:
        ensure => latest,
    }
    
   file { ["/etc/init.d/bird","/etc/init.d/bird6"]:
        ensure  => absent,
    }

    file { "/etc/init/bird.conf":
        ensure  => file,
        mode    => 0644,
        owner   => root,
        group   => root,
        source  => "puppet:///files/etc/init/bird.conf",
    }

    file { "/etc/init/bird6.conf":
        ensure  => file,
        mode    => 0644,
        owner   => root,
        group   => root,
        source  => "puppet:///files/etc/init/bird6.conf",
    }

    service { "bird":
        ensure      => running,
        subscribe   => File["/etc/bird.conf"],
        require     => File["/etc/init/bird.conf"],
        provider    => "upstart",
        hasstatus   => true,
        restart     => "service bird reload",
    }

    service { "bird6":
        ensure      => running,
        subscribe   => File["/etc/bird6.conf"],
        require     => File["/etc/init/bird6.conf"],
        provider    => "upstart",
        restart     => "service bird6 reload",
        hasstatus   => true,
    }

    file { "/etc/bird.conf":
        owner   => root,
        group   => root,
        mode    => 0755,
        content => template("bird.conf.rb"),
        ensure  => file,
    }
    
    file { "/etc/bird6.conf":
        owner   => root,
        group   => root,
        mode    => 0755,
        content => template("bird6.conf.rb"),
        ensure  => file,
    }

    file { "/usr/local/bin/birdshell":
        owner   => root,
        group   => root,
        mode    => 0755,
        source  => "puppet:///files/usr/local/bin/birdshell",
        ensure  => file,
    }

    line { "birdshell_in_shells":
        file    => "/etc/shells",
        line    => "/usr/local/bin/birdshell",
        ensure  => present,
    }

}