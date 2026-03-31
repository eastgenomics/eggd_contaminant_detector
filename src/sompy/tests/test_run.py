import pytest
from pathlib import Path

from pytest_mock import MockerFixture

import sompy._commands  # type: ignore
import sompy._paths     # type: ignore
import sompy._run       # type: ignore


def test_run_tool_is_using_right_mounts(
    mocker: MockerFixture, tmp_path: Path, sompy_args_with_regions: dict[str, str]
) -> None:
    # In the run_tool function, there's an `ambergris.run_container` call. I don't want to actually
    # launch Docker, I just want to make sure that it's receiving the bindmounts object in the format
    # I expect. So what we're doing here is patching ambergris.run_container, and replacing it with a fake
    # function that allows you to inspect what was passed into it. That's the reason for the mocker.patch call.
    # The fake function (i.e. `mock_runcontainer`, which is a Mocker object) has a `call_args` attribute
    # which does just that. That's the north star for this test case.
    # I know this is a lot of commentary, but this I'm a total beginner to mocking, and if I ever return to this,
    # I'll be completely lost as to what this test is doing.
    mock_runcontainer = mocker.patch("ambergris.run_container")
    mock_runcontainer.return_value = None

    # We also need to make up a fake function that returns a tuple of ("command string", Path(some_path)),
    # because that's what the functions in `sompy.commands` return.
    # We'll pass this into the `command` argument of `sompy._run.run_tool`.
    mock_command = mocker.Mock(return_value=("some command", tmp_path / "out"))

    # Since sompy._run.TOOL_REGISTRY controls which functions get called, we also need to replace it with a mock.
    # sompy._run.run_tool is expecting one of "sompy", "bcftools norm", and "bcftools sort". So if we make the registry
    # return the mock command instead of sompy, we can get around the validation block and capture the mounts later on.
    #mocker.patch.dict("sompy._run.TOOL_REGISTRY", {"sompy": mock_command})

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    expected_mounts = sompy._paths._make_mounts(in_dir, out_dir)

    # I put a "mounts" attribute in the sompy args fixture, which we don't want to use (it'll break the test, because
    # `sompy._run.run_tool` has an `out_dir` argument instead of asking for the bindmounts). We're testing whether this function
    # handles mounts correctly by itself.
    del sompy_args_with_regions["mounts"]

    sompy._run._run_tool(
        "nonexistent_image", mock_command, out_dir, **sompy_args_with_regions # type: ignore
    )

    # At this point, `sompy._run.run_tool` will have called `ambergris.run_container`, which we ended up patching out.
    # This means we caught our fish, and can look at what it ate.
    # In the original function, the function call would've been ambergris.run_container("something", "some_command", *[<bindmounts list>]).
    # We're using the "explode list" operator, so this translates to ambergris.run_container("nonexistent_image", "some command", mounts[0], mounts[1])
    # This means the mounts are the third and fourth positional args (hence `[args[2], args[3]]`).
    args, _ = mock_runcontainer.call_args
    actual_mounts = [args[2], args[3]]

    assert actual_mounts == expected_mounts


def test_run_tool_is_passing_tool_kwargs_to_command_correctly(
    mocker: MockerFixture, tmp_path: Path, sompy_args_with_regions: list[dict[str, str | bool]] # type: ignore
) -> None:
    # This time, we want to make sure that the command that gets passed to ambergris.run_container is correct.
    # We can repeat what we did before, and instead of looking at args[2], we can look at args[1] and make
    # sure the sompy command is correct.
    mock_runcontainer = mocker.patch("ambergris.run_container")
    mock_runcontainer.return_value = None
    out_dir = tmp_path / "out"
    del sompy_args_with_regions["mounts"] # type: ignore

    sompy._run._run_tool(
        "nonexistent_image",
        sompy._commands._sompy,
        out_dir=out_dir,
        **sompy_args_with_regions, # type: ignore
    )

    args, _ = mock_runcontainer.call_args

    expected_command = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass -o /out/truth_query --restrict-regions /in/panel.bed --reference /in/reference.fa /in/truth.vcf.gz /in/query.vcf.gz"
    actual_command = args[1]

    assert actual_command == expected_command


def test_run_tool_is_passing_tool_args_to_command_correctly(
    mocker: MockerFixture, tmp_path: Path, sompy_args_with_regions: list[dict[str, str | bool]] # type: ignore
) -> None:
    # Somebody might run this command manually (you never know). Since we're in control of what gets submitted to sompy_command,
    # we don't need to delete anything from the fixture (as this time we're cherry-picking, not submitting the entire dict).
    mock_runcontainer = mocker.patch("ambergris.run_container")
    mock_runcontainer.return_value = None
    out_dir = tmp_path / "out"

    truth_vcf = sompy_args_with_regions["truth"] # type: ignore
    query_vcf = sompy_args_with_regions["query"] # type: ignore
    reference = sompy_args_with_regions["reference"] # type: ignore

    expected_statsfile = tmp_path / "out" / "truth_query.stats.csv"
    # When I said "they might run the command manually", I mean they might do the *tool_args thing instead of/in addition to
    # the **tool_kwargs thing. Just to be thorough, let's mess up the order a little, and omit the bed file
    actual_statsfile = sompy._run._run_tool(
        "nonexistent_image",
        sompy._commands._sompy,
        out_dir,
        truth_vcf,
        reference=reference,
        query=query_vcf,
    )
    assert actual_statsfile == expected_statsfile

    # Next, we can repeat what we did in the previous test and make sure the command that `ambergris.run_container` is receiving
    # is as we expect. This time, there's no `--restrict-regions <panel.bed>` argument, since we omitted the panel file
    args, _ = mock_runcontainer.call_args

    expected_command = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass -o /out/truth_query --reference /in/reference.fa /in/truth.vcf.gz /in/query.vcf.gz"
    actual_command = args[1]

    assert actual_command == expected_command
