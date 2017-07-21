Deployment using docker-machine
===============================

The `sushibar` docker deployment was originally tested on `AWS`, but it works
essentially the same way on `GCP` (the new setup). The long term plan is to
deploy to a kubernetes server using `bake`.



Provisioning on GCP
===================

We'll use the command line tool `docker-machine` for the following two tasks:
  - Provision an instance (a virtual machine rented from GCP) which will
    serve as the docker host
  - Set appropriate environment variables to make `docker` command line tools
    talk to the remote docker host instead of localhost


STEP0: Login

    gcloud auth application-default login


STEP1: Create a static IP for the docker host:

    gcloud compute addresses create gcpsushibarhost-address --region us-east1


STEP2: Use `docker-machine`'s [GCE driver](https://docs.docker.com/machine/drivers/gce/)
to setup a docker host called `gcpsushibarhost` in the Google cloud.

    docker-machine create --driver google \
       --google-project kolibri-demo-servers \
       --google-zone us-east1-d \
       --google-machine-type n1-standard-1 \
       --google-machine-image debian-cloud/global/images/debian-9-stretch-v20170717 \
       --google-disk-size 100 \
       --google-username admin \
       --google-tags http-server,https-server \
       --google-address gcpsushibarhost-address \
       gcpsushibarhost


Assuming everything goes to plan, a new instance should be running, with docker
installed on it and the docker daemon listening on port `2375`.

STEP 3: You need to manually edit the inbound firewall rules to allow access to this port.


The security of the connection to the remote docker daemon is established by the
TLS certificates in `~/.docker/machine/machines/gcpsushibarhost/`.
The settings required to configure docker to build and deploy containers on the
remote host `gcpsushibarhost` can be displayed using the command:

    docker-machine env gcpsushibarhost




Using docker on the remote docker host
======================================

In order to configure docker to build and run containers on `gcpsushibarhost`, we must
inject the appropriate env variables which will tell the local docker command
where it should work:

    eval $(docker-machine env gcpsushibarhost)

After running this, all docker commands will be send to the remote `gcpsushibarhost`.


Start/update/deploy
-------------------
See [docker-compose.md](./docker-compose.md).



Shutting down
-------------

To stop the running container:

    eval $(docker-machine env gcpsushibarhost)
    docker ps                     # to find the running container IDs
    docker stop <container_id>

To destroy the machine:

    docker-machine rm gcpsushibarhost







Provisioning on AWS
===================

We'll use the command line tool `docker-machine` for the following two tasks:
  - Provision an `ec2` instance (a virtual machine rented from AWS) which will
    serve as the docker host
  - Set appropriate environment variables to make `docker` command line tools
    talk to the remote docker host instead of localhost


AWS credentials
---------------
The commands depend on an IAM user existing in AWS and its associated credentials
being available as environment variables. The  user must have full `ec2` and `VPC`
access for use by docker machine. When creating this user, use the following
[custom policy](docs/docker_machine_user_IAM_policy.txt), by filling in the region
(e.g. `us-east-1` and account id (numeric id associated with AWS account).
These credentials must be provided as the environment variables:

    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY

For convenience, you can create an `.env` file in the directory `credentials/`
to store all four environment variables. For example `credentials/aws-keys.env`
should contain:

    export AWS_ACCESS_KEY_ID=232384i84
    export AWS_SECRET_ACCESS_KEY=asoijadmscio9i4940dpsdlsidjsoidjji

and all variables can be loaded into the current shell environment using

    source credentials/aws-keys.env


Creating the docker host on AWS
-------------------------------
Deprecated: see GCP instructions above.

Use `docker-machine`'s [AWS driver](https://docs.docker.com/machine/drivers/aws/)
to setup a docker host called `sushibarhost` in the AWS cloud

docker-machine create -d amazonec2 \
    --amazonec2-region ca-central-1 \
    --amazonec2-instance-type t2.small \
    sushibarhost

Note this command depends on the env variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
for the `docker-machine-user` IAM role being present in the environment.

The above command will do "magically" all the work of setting up a basic linux box
and installing docker on it (that's why it takes 5-10 minutes):

    Creating machine...
    (sushibarhost) Launching instance...
    Waiting for machine to be running, this may take a few minutes...
    Detecting operating system of created instance...
    Waiting for SSH to be available...
    Detecting the provisioner...
    Provisioning with ubuntu(systemd)...
    Installing Docker...
    Copying certs to the local machine directory...
    Copying certs to the remote machine...
    Setting Docker configuration on the remote daemon...
    Checking connection to Docker...
    Docker is up and running!
    To see how to connect your Docker Client to the Docker Engine running on this virtual machine,
    run: docker-machine env sushibarhost

Assuming everything goes to plan, a new `t2.small` instance should be running,
with docker installed on it and the docker daemon listening on port `2375`.
The security of the connection to the remote docker daemon is established by the
TLS certificates in `~/.docker/machine/machines/sushibarhost/`.

The settings required to configure docker to build and deploy containers on the
remote host `sushibarhost` can be displayed using the command:

      docker-machine env sushibarhost



