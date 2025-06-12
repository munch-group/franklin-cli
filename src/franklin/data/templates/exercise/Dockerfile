#############################################################################
## build: ###################################################################
#############################################################################

# pixi image for building dependencies
FROM registry.gitlab.au.dk/franklin/base-images/franklin-build-base:latest AS build

# copy source code, pixi.toml and pixi.lock to the container
COPY . /home/vscode
WORKDIR /home/vscode

# # extract deps using default env
# RUN pixi run python .pixi.py .

# install them in the prod env
RUN pixi install -e prod 

# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e prod > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

RUN echo '#!/usr/bin/env bash \n\
WORKSPACE_FOLDER="${1:-$PWD}" \n\
ENVIRONMENT="prod" \n\
echo "export PIXI_HOME=/home/vscode" >> /home/vscode/.bashrc \n\
echo "export PIXI_PROJECT_MANIFEST="$WORKSPACE_FOLDER/pixi.toml"" >> /home/vscode/.bashrc \n\
curl -fsSL https://pixi.sh/install.sh | bash \n\
/bin/bash -i -c "pixi run python -m ipykernel install --user --name prod --display-name Franklin" \n\
/bin/bash -i -c "pixi shell-hook --manifest-path $WORKSPACE_FOLDER --environment $ENVIRONMENT >> /home/vscode/.bashrc" \n\
' > /install_pixi.sh
RUN chmod 755 /install_pixi.sh

#############################################################################
## production: ##############################################################
#############################################################################

# # production image for running jupyter

# FROM ubuntu:24.04 AS production
# USER root
# RUN useradd -ms /bin/bash vscode
# RUN mkdir -p /home/vscode && chown vscode /home/vscode
# USER vscode
# WORKDIR /home/vscode

FROM registry.gitlab.au.dk/franklin/base-images/franklin-production-base:latest AS production
# FROM mcr.microsoft.com/devcontainers/base:alpine:latest AS production

LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"
LABEL dk.au.gitlab.group=franklin
ENV PYTHONDONTWRITEBYTECODE=true

# set some user and workdir settings to work nicely with vscode
USER vscode
WORKDIR /home/vscode

# only copy the production environment into prod container
# note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build --chown=vscode:vscode /home/vscode/.pixi/envs/prod /home/vscode/.pixi/envs/prod

# copy scripts (should be at root)
COPY --from=build --chown=vscode:vscode /shell-hook.sh /shell-hook.sh
COPY --from=build --chown=vscode:vscode /install_pixi.sh /install_pixi.sh

# copy the exercise notebook
COPY --from=build --chown=vscode:vscode /home/vscode/exercise.ipynb /home/vscode/exercise.ipynb

# copy the script to test-run exercise notebook
COPY --from=build --chown=vscode:vscode /home/vscode/.test-notebook.sh /home/vscode/test-notebook.sh

# send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED=1

# set max nr of threads to silence warning
ENV NUMEXPR_MAX_THREADS=8

# COPY .entrypoint.sh /bin/entrypoint.sh
# RUN chmod +x /bin/entrypoint.sh
# ENTRYPOINT ["/bin/entrypoint.sh"]

# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]


#docker run --platform linux/amd64 --rm --label dk.au.gitlab.group=franklin --mount type=bind,source=/Users/kmt/arg-dashboard,target=/Users/kmt/arg-dashboard -w /Users/kmt/arg-dashboard -i -p 8050:8050 -p 8888:8888 test

# # docker build --platform linux/amd64 -t test .

# # docker run --platform linux/amd64 --rm -w /home/vscode -i -p 8050:8050 ls-p 8888:8888  test

#docker run --platform linux/amd64 --rm --label dk.au.gitlab.group=franklin --mount type=bind,source=/Users/kmt/arg-dashboard,target=/Users/kmt/arg-dashboard -w /Users/kmt/arg-dashboard -i -p 8050:8050 -p 8888:8888 --tty test /bin/bash