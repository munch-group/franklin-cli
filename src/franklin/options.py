import click

subdirs_allowed = click.option(
    "--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
    default=False,
    help="Allow subdirs in current directory mounted by Docker.",
    hidden=True,
    )

update = click.option(
    '--update/--no-update', 
    default=True,
    help="Override check for package updates",
    hidden=True,
    )

git_commands = click.option(
    '--commands/--no-commands', 
    default=False,
    help="Show git commands executed",
    )