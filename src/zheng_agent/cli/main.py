import click
from zheng_agent.cli.commands.chat import chat
from zheng_agent.cli.commands.pause import pause
from zheng_agent.cli.commands.replay import replay
from zheng_agent.cli.commands.resume import resume
from zheng_agent.cli.commands.run import run


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """zheng-agent: Harness-first agent execution system."""
    pass


cli.add_command(run)
cli.add_command(chat)
cli.add_command(pause)
cli.add_command(resume)
cli.add_command(replay)


if __name__ == "__main__":
    cli()