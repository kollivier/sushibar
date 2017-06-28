Deployment using docker-machine
===============================

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



### Using docker on the remote docker host

In order to configure docker to build and run containers on `sushibarhost`, we must
inject the appropriate env variables which will tell the local docker command
where it should work:

    eval $(docker-machine env sushibarhost)

After running this command we must build the docker image on `awshost`:

    docker build webapp/  --tag screenshot-docker-img

Before we run the container, make sure the env contains the S3 credentials by
running `source credentials/aws-keys.env` if needed.

To start the container from the image tagged `screenshot-docker-img` on `awshost`,
run the following command:

    docker run \
      -p 5000:5000 \
      -e S3_AWS_ACCESS_KEY_ID=$S3_AWS_ACCESS_KEY_ID \
      -e S3_AWS_SECRET_ACCESS_KEY=$S3_AWS_SECRET_ACCESS_KEY \
      -e S3_BUCKET_NAME="web-screenshot-service" \
      -e S3_BUCKET_BASE_URL="https://s3.ca-central-1.amazonaws.com/web-screenshot-service/" \
      -d screenshot-docker-img

Make sure `S3_BUCKET_NAME` and `S3_BUCKET_BASE_URL` are set appropriately.

This will run the entry CMD `python3 screenshotservice.py` to start the service.



### Open port 5000

From the ec2 web interface, choose "NETWORK & SECURITY" from the side menu, then
"Security Groups", and click on the security group called "docker-machine".

![docs/aws_steps/open_port_5000/step1.png](docs/aws_steps/open_port_5000/step1.png)

In the bottom panel, select "Inbound" then "Edit" and add a custom TCP rule for
port 5000 coming from anywhere (`0.0.0.0/0`).

![docs/aws_steps/open_port_5000/step2.png](docs/aws_steps/open_port_5000/step2.png)



### Find ec2 host's public IP and test API

    docker-machine ip sushibarhost
    xx.yy.zz.ww

Add DNS `sushibar.learningequality.org --> xx.yy.zz.ww`.


Deploy new version
------------------

    source credentials/aws-keys.env
    eval $(docker-machine env sushibarhost)
    docker ps                      # to find the container ID
    docker stop <container_id>
    docker build webapp/  --tag screenshot-docker-img
    docker run \
      -p 5000:5000 \
      -e S3_AWS_ACCESS_KEY_ID=$S3_AWS_ACCESS_KEY_ID \
      -e S3_AWS_SECRET_ACCESS_KEY=$S3_AWS_SECRET_ACCESS_KEY \
      -e S3_BUCKET_NAME="web-screenshot-service" \
      -e S3_BUCKET_BASE_URL="https://s3.ca-central-1.amazonaws.com/web-screenshot-service/" \
      -d screenshot-docker-img


Shutting down
-------------

To stop the container:

    eval $(docker-machine env sushibarhost)
    docker ps                     # to find the container ID
    docker stop <container_id>

To destroy the machine:

    source credentials/aws-keys.env
    docker-machine rm sushibarhost

