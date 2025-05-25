# pixi image for building dependencies
FROM ghcr.io/prefix-dev/pixi:0.47.0-oracular AS build

# copy source code, pixi.toml and pixi.lock to the container
COPY . /app
WORKDIR /app

# extract deps using default env, install them in the prod env
RUN pixi run python pixi.py . && pixi install -e prod 

# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e prod > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

# production image for running jupyter
FROM ubuntu:24.04 AS production

# Maintainer 
LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"
LABEL dk.au.gitlab.group=franklin
ENV PYTHONDONTWRITEBYTECODE=true

# only copy the production environment into prod container
# please note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build /app/.pixi/envs/prod /app/.pixi/envs/prod
COPY --from=build /shell-hook.sh /shell-hook.sh
WORKDIR /app

# send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED=1


# RUN echo '#!/bin/sh' > /bin/test-notebook.sh \
#  && echo 'PYDEVD_DISABLE_FILE_VALIDATION=1 jupyter nbconvert --Application.log_level=50 --to notebook --execute --inplace exercise.ipynb || exit 1' >> /bin/test-notebook.sh\
#  && echo 'exec "$@"' >> /bin/test-notebook.sh

COPY test-notebook.sh /bin/test-notebook.sh
RUN chmod +x /bin/test-notebook.sh

COPY exercise.ipynb exercise.ipynb

ENV NUMEXPR_MAX_THREADS=8


# COPY entrypoint.sh /bin/entrypoint.sh
# RUN chmod +x /bin/entrypoint.sh
# ENTRYPOINT ["/bin/entrypoint.sh"]

# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]


# # docker build --platform linux/amd64 -t test .

# # docker run --rm -w /app -i -p 8050:8050 -p 8888:8888  test

