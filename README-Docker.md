### Building the docker image for vw-py

* Download and Install Docker ToolBox from https://www.docker.com/products/docker-toolbox.
* go to vw-py dir and build the image with:
```bash
  docker build -t yourrepo/vw-py:yourtag .
```
For example,
```bash
docker build -t mt/vw-py:1.0 .
```

* Once the image is built, to test out, run a docker container using the image with an interactive shell open:

```bash
  docker run --name vw-py-0.1 -it --entrypoint=/bin/bash yourrepo/vw-py:yourtag -i
```
