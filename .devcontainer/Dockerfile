# https://hub.docker.com/r/hadolint/hadolint/tags
FROM hadolint/hadolint:v2.14.0-alpine AS hadolint
# https://hub.docker.com/r/transformia/task/tags
FROM transformia/task:3.45.4 AS task
# https://hub.docker.com/_/node
FROM transformia/claude-code:2.0.28

# Build arguments for user UID/GID
ARG UID=1000
ARG GID=1000

COPY --from=hadolint /bin/hadolint /bin/hadolint
COPY --from=task /usr/local/bin/task /bin/task

RUN apk add --no-cache \
    git \
    sudo \
    docker-cli

ENV HOME=/home/code

# Create code user with matching UID/GID
RUN addgroup -g "${GID}" code && \
    adduser -h /home/code -D -u "${UID}" -G code -s /bin/bash code

# Switch to code user
USER code