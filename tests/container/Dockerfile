FROM ubuntu:18.04
RUN apt update && apt install sudo && sudo apt install btrfs-progs --yes


RUN mkdir /app
WORKDIR /app
COPY run.sh .
CMD [ "bash", "run.sh" ]
