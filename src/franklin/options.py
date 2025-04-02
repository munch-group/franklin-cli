import click

allow_subdirs = click.option(
    "--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
    default=False,
    help="Allow subdirs in current directory mounted by Docker.")

no_update = click.option(
    '--update/--no-update', 
    default=True,
    help="Override check for package updates")