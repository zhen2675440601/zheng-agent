import click
from zheng_agent.cli.commands.run import run
from zheng_agent.cli.commands.chat import chat


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """zheng-agent: Harness-first agent execution system."""
    pass


cli.add_command(run)
cli.add_command(chat)


if __name__ == "__main__":
    cli()