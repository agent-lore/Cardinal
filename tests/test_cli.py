from cardinal.cli import cli


def test_hello_default(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output


def test_hello_with_name(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["hello", "--name", "Cardinal"])
    assert result.exit_code == 0
    assert "Hello, Cardinal!" in result.output

