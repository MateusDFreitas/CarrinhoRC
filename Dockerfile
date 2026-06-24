FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV APP_HOME=/workspace

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    make \
    python3-colcon-common-extensions \
    python3-opencv \
    ros-humble-rosbridge-server \
  && mkdir -p /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

COPY src ./src
COPY dashboard/package*.json ./dashboard/

RUN source /opt/ros/${ROS_DISTRO}/setup.bash \
  && colcon build \
  && npm ci --prefix dashboard

COPY dashboard ./dashboard
COPY Makefile README.md ./
COPY docker ./docker

RUN chmod +x docker/*.sh \
  && npm run build --prefix dashboard

EXPOSE 5173 9090

ENTRYPOINT ["/workspace/docker/entrypoint.sh"]
CMD ["/workspace/docker/run-system.sh"]
