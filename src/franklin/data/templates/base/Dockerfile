
# FROM continuumio/miniconda3:4.6.14
FROM continuumio/miniconda3:25.1.1-2

LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"

# change franklin to franklin-something if running on a different institute
LABEL dk.au.gitlab.group=franklin

ENV PYTHONDONTWRITEBYTECODE=true

RUN conda install -c conda-forge --yes --freeze-installed \
        nomkl git gh conda-build openssh zip \
        nbdime nbformat jupyterlab notebook nodejs ipynbname \
    && find /opt/conda/ -follow -type f -name '*.a' -delete \
    && find /opt/conda/ -follow -type f -name '*.pyc' -delete \
    && find /opt/conda/ -follow -type f -name '*.js.map' -delete 

# send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED=1

COPY entrypoint.sh /bin/entrypoint.sh
RUN chmod +x /bin/entrypoint.sh

ENTRYPOINT ["/bin/entrypoint.sh"]
CMD ["/bin/bash", "-c", "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]


# FROM ghcr.io/prefix-dev/pixi:0.47.0-oracular AS build

# # copy source code, pixi.toml and pixi.lock to the container
# COPY . /app
# WORKDIR /app

# RUN pixi install -e default

# # Create the shell-hook bash script to activate the environment
# RUN pixi shell-hook -e default > /shell-hook.sh

# # extend the shell-hook script to run the command passed to the container
# RUN echo 'exec "$@"' >> /shell-hook.sh

# FROM ubuntu:24.04 AS production

# LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"
# LABEL dk.au.gitlab.group=franklin
# ENV PYTHONDONTWRITEBYTECODE=true

# # only copy the production environment into prod container
# # please note that the "prefix" (path) needs to stay the same as in the build container
# COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
# COPY --from=build /shell-hook.sh /shell-hook.sh
# WORKDIR /app

# # send stdout and stderr straight to terminal
# ENV PYTHONUNBUFFERED=1

# # set the entrypoint to the shell-hook script (activate the environment and run the command)
# # no more pixi needed in the prod container
# ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
# CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]



# # docker build --platform linux/amd64 -t test .

# # docker run --rm -w /app -i -p 8050:8050 -p 8888:8888  test