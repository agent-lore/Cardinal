import click


@click.group()
@click.version_option(package_name="cardinal")
def cli() -> None:
    """Cardinal CLI."""


@cli.command()
@click.option("--name", default="World", help="Name to greet.")
def hello(name: str) -> None:
    """Say hello."""
    click.echo(f"Hello, {name}!")
