
CONF = {
    'cache_dir': '/tmp/pydeps-cache'
}


GITHUB_REPOS = {
    'stackforge': [
        'murano',
        'murano-dashboard'
    ],
    'murano-project': [
        'murano-app-incubator'
    ],
    'openstack': [
        'oslo.messaging'
    ]
}


KNOWN_PACKAGES = {
    'argparse': {
        'github_repo': None,
        'rpm': 'python-argparse',
        'deb': 'python'
    },
}


PACKAGE_REPOS = {
    'fuel-5.1-stable': {
        'deb': 'http://fuel-repository.mirantis.com/fwm/5.1/ubuntu',
        'rpm': 'http://fuel-repository.mirantis.com/fwm/5.1/centos'
    }
}