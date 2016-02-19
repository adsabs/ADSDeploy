# ADSDeploy
Deployment, testing, and GUI pipeline for the ADS application tier
=======
[![Build Status](https://travis-ci.org/adsabs/ADSDeploy.svg)](https://travis-ci.org/adsabs/ADSDeploy)
[![Coverage Status](https://coveralls.io/repos/github/adsabs/ADSDeploy/badge.svg?branch=master)](https://coveralls.io/github/adsabs/ADSDeploy?branch=master)

ADSDeploy is the 'Green Button' for deploying microservices. It is made of several components.

- web UI + web microservice (gateway for the web UI) 
- pipeline (rabbitmq workers + database), they start jobs
- `eb-deploy` - executing jobs (our scripts that call Amazon AWS Api)


dev setup - vagrant (docker)
============================

1. vim ADSDeploy/local_config.py #edit, edit
1. `vagrant up db rabbitmq app --provider=docker`
1. `vagrant ssh app`
1. `cd /vagrant`

This will start the pipeline inside the `app` container - make sure you have configured endpoints and
access tokens correctly.

We are using 'docker' provider (ie. instead of virtualbox VM, you run the processes in docker).
On some systems, it is necessary to do: `export VAGRANT_DEFAULT_PROVIDER=docker` or always 
specify `--provider docker' when you run vagrant.
 
The  directory is synced to /vagrant/ on the guest.


dev setup - local editing
=========================

If you (also) hate when stuff is unnecessarily complicated, then you can run/develop locally
(using whatever editor/IDE/debugger you like)

1. ./manifests/production/app/eb-deploy-setup.sh
1. virtualenv python
1. source python/bin/activate
1. pip install -r requirements.txt
1. pip install -r dev-requirements.txt
1. vagrant `up db rabbitmq webapp --provider=docker`

This will setup python `virtualenv` and the database + rabbitmq. You can run the pipeline and 
tests locally. 


eb-deploy
=========

`$ ./manifests/production/app/eb-deploy-setup.sh`
 
The script will checkout the internal ADS repository (you will need access to it). The script will
also test if you have access. If not, it will initiate the setup. You will need to supply the 
AWS secret tokens. 


RabbitMQ
========

`vagrant up rabbitmq`

The RabbitMQ will be on localhost:6672. The administrative interface on localhost:25672.


Database
========

`vagrant up db`

PostgreSQL on localhost:6432

WebApp
======

`vagrant up webapp --provider=docker`

The API gateway (microservice) will be on localhost:9000.



production setup
================

`vagrant up prod`

Before running this command, you must obtain the `eb-deploy-key` (for accessing GitHub
repository) and `aws_config` with secrets for accessing AWS. These files have to placed
`into manifests/production/app`

The setup will automatically download/install the latest release from the github (no, not
your local changes - only from github).

If your /ADSDeploy/prod_config.py is available, it will copy and use it in place of
`local_config.py`

No ports are exposed, no SSH access is possible. New releases will deployed automatically.



production setup - docker way
=============================

1. cd manifests/production/app
1. create `aws_config` and `eb-deploy-key`
2. docker build -t prod .
3. cd ../../.. 
4. vim prod_config.py # edit, edit...
4. docker run -d -v .:/vagrant/ --cap-add SYS_ADMIN --security-opt apparmor:unconfined --name ADSDeploy prod /sbin/my_init


Here are some useful commands:

- restart service

	`docker exec ADSDeploy sv restart app`

- tail log from one of the workers

	`docker exec ADSDeploy tail -f /app/logs/ClaimsImporter.log`
