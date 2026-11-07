from types import SimpleNamespace

import pytest

from SigProfilerMatrixGenerator.scripts import build_refseq_references as builder


def write_assembly_report(path, chromosomes=None):
    chromosomes = chromosomes or [
        *(str(chromosome) for chromosome in range(1, 23)),
        "X",
        "Y",
    ]
    rows = [
        "# RefSeq assembly accession: GCF_009914755.1",
        "# synthetic fixture",
    ]
    for index, chromosome in enumerate(chromosomes, start=1):
        rows.append(
            "\t".join(
                [
                    chromosome,
                    "assembled-molecule",
                    chromosome,
                    "Chromosome",
                    f"GB_{index}",
                    "=",
                    f"RS_{index}",
                    "Primary Assembly",
                    "1000",
                    f"chr{chromosome}",
                ]
            )
        )
    path.write_text("\n".join(rows) + "\n")


def test_chm13_assembly_map_requires_every_nuclear_chromosome(tmp_path):
    report = tmp_path / "assembly_report.txt"
    write_assembly_report(report)
    mapping = builder.read_accession_map(report)

    builder.assert_assembly_accession(report, "GCF_009914755.1")
    builder.assert_complete_chromosome_map(mapping)
    assert mapping["RS_1"] == "chr1"
    assert set(mapping.values()) == {
        *(f"chr{chromosome}" for chromosome in range(1, 23)),
        "chrX",
        "chrY",
    }

    write_assembly_report(report, [*(str(i) for i in range(1, 23)), "X"])
    with pytest.raises(SystemExit, match="missing=.*Y"):
        builder.assert_complete_chromosome_map(builder.read_accession_map(report))


def test_exome_coordinates_are_one_based_inclusive(tmp_path):
    gff = tmp_path / "annotation.gff"
    gff.write_text(
        "#!annotation-source NCBI RefSeq GCF_009914755.1-RS_2025_08\n"
        "RS_1\tRefSeq\tCDS\t10\t20\t.\t+\t.\tID=one\n"
        "RS_1\tRefSeq\tCDS\t21\t30\t.\t+\t.\tID=two\n"
    )

    intervals = builder.read_intervals(gff, {"RS_1": "chr1"}, "CDS")

    assert intervals["chr1"] == [(10, 20), (21, 30)]
    assert builder.merge(intervals["chr1"]) == [[10, 30]]


def test_transcript_grouping_uses_stable_gene_id_not_duplicate_symbol(tmp_path):
    gtf = tmp_path / "annotation.gtf"
    gtf.write_text(
        "RS_1\tBestRefSeq\ttranscript\t10\t20\t.\t-\t.\t"
        'gene_id "CLN3"; transcript_id "NM_1"; gene "CLN3"; '\
        'transcript_biotype "mRNA";\n'
        "RS_1\tGnomon\ttranscript\t30\t40\t.\t+\t.\t"
        'gene_id "CLN3_1"; transcript_id "XM_2"; gene "CLN3"; '\
        'transcript_biotype "mRNA";\n'
    )

    rows = builder.read_transcripts(gtf, {"RS_1": "1"})["1"]

    assert [row[1][6] for row in rows] == ["CLN3", "CLN3_1"]
    assert [row[1][3] for row in rows] == ["-1", "1"]


def test_exome_builder_rejects_missing_chromosome_records(tmp_path):
    report = tmp_path / "assembly_report.txt"
    gff = tmp_path / "annotation.gff"
    output = tmp_path / "exome.interval_list"
    write_assembly_report(report)
    gff.write_text(
        "#!annotation-source NCBI RefSeq GCF_009914755.1-RS_2025_08\n"
        "RS_1\tRefSeq\tCDS\t10\t20\t.\t+\t.\tID=one\n"
    )
    args = SimpleNamespace(
        assembly_report=str(report),
        gff=str(gff),
        feature="CDS",
        description="fixture",
        output=str(output),
        expect_release="NCBI RefSeq GCF_009914755.1-RS_2025_08",
        expect_assembly="GCF_009914755.1",
        expect_assembly_report_sha256=None,
        expect_annotation_sha256=None,
    )

    with pytest.raises(SystemExit, match="no 'CDS' records found"):
        builder.build_exome_list(args)
    assert not output.exists()
