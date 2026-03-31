import sompy._commands


def test_sompy_without_regions(sompy_args_without_regions):
    expected = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass -o /out/truth_query --reference /in/reference.fa /in/truth.vcf.gz /in/query.vcf.gz"
    actual, _ = sompy._commands._sompy(**sompy_args_without_regions)
    assert actual == expected


def test_sompy(sompy_args_with_regions):
    expected = "/opt/hap.py/bin/som.py --no-count-unk --no-fixchr-truth --no-fixchr-query --include-nonpass -o /out/truth_query --restrict-regions /in/panel.bed --reference /in/reference.fa /in/truth.vcf.gz /in/query.vcf.gz"
    actual, _ = sompy._commands._sompy(**sompy_args_with_regions)
    assert actual == expected


def test_sompy_returns_host_output(tmp_path, sompy_args_with_regions):
    expected_output = tmp_path / "out" / "truth_query.stats.csv"
    _, host_output = sompy._commands._sompy(**sompy_args_with_regions)
    assert host_output == expected_output


def test_bcftools_sort(bcftools_sort_args):
    expected = "bcftools sort -W=tbi -Oz -o /out/test.sorted.vcf.gz /in/test.vcf.gz"
    actual, _ = sompy._commands._bcftools_sort(**bcftools_sort_args)
    assert actual == expected


def test_bcftools_sort_returns_host_output(tmp_path, bcftools_sort_args):
    expected_output = tmp_path / "out" / "test.sorted.vcf.gz"
    _, host_output = sompy._commands._bcftools_sort(**bcftools_sort_args)
    assert host_output == expected_output


def test_bcftools_norm(bcftools_norm_args):
    expected = "bcftools norm -m-any -f /in/test_reference.fa /in/test.vcf.gz | bcftools norm -d any -W=tbi -Oz -o /out/test.normalised.vcf.gz"
    actual, _ = sompy._commands._bcftools_norm(**bcftools_norm_args)
    assert actual == expected


def test_bcftools_norm_returns_host_output(tmp_path, bcftools_norm_args):
    expected_output = tmp_path / "out" / "test.normalised.vcf.gz"
    _, host_output = sompy._commands._bcftools_norm(**bcftools_norm_args)
    assert host_output == expected_output
