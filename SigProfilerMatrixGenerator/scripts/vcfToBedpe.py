#!/usr/bin/env python

import sys
import math, time, re
import pandas as pd
import os


# --------------------------------------
# define functions
def _infer_bnd_strands(alt):
    """Infer BRASS-style breakend strands from VCF BND ALT notation."""
    if "[" in alt:
        bracket = "["
    elif "]" in alt:
        bracket = "]"
    else:
        return ".", "."

    bracket_is_after_local_sequence = alt.find(bracket) > 0
    if bracket == "]" and bracket_is_after_local_sequence:
        return "+", "+"
    if bracket == "[" and bracket_is_after_local_sequence:
        return "-", "-"
    if bracket == "]":
        return "-", "+"
    return "+", "-"


def _classify_sv(svtype, chrom1, chrom2, strand1=".", strand2="."):
    mapping = {
        "DEL": "deletion",
        "INS": "insertion",
        "DUP": "tandem-duplication",
        "CPX": "unknown",
        "INV": "inversion",
        "CNV": "unknown",
        "CTX": "translocation",
    }
    if svtype != "BND":
        return mapping.get(svtype, "unknown")
    if str(chrom1) != str(chrom2):
        return "translocation"
    if strand1 == "+" and strand2 == "+":
        return "deletion"
    if strand1 == "-" and strand2 == "-":
        return "tandem-duplication"
    if (strand1 == "+" and strand2 == "-") or (strand1 == "-" and strand2 == "+"):
        return "inversion"
    return "unknown"


class Vcf(object):
    def __init__(self):
        self.file_format = "VCFv4.2"
        # self.fasta = fasta
        self.reference = ""
        self.sample_list = []
        self.info_list = []
        self.format_list = []
        self.alt_list = []
        self.add_format("GT", 1, "String", "Genotype")

    def add_header(self, header):
        for line in header:
            if line.split("=")[0] == "##fileformat":
                self.file_format = line.rstrip().split("=")[1]
            elif line.split("=")[0] == "##reference":
                self.reference = line.rstrip().split("=")[1]
            elif line.split("=")[0] == "##INFO":
                a = line[line.find("<") + 1 : line.find(">")]
                r = re.compile(r"(?:[^,\"]|\"[^\"]*\")+")
                self.add_info(*[b.split("=")[1] for b in r.findall(a)])
            elif line.split("=")[0] == "##ALT":
                a = line[line.find("<") + 1 : line.find(">")]
                r = re.compile(r"(?:[^,\"]|\"[^\"]*\")+")
                self.add_alt(*[b.split("=")[1] for b in r.findall(a)])
            elif line.split("=")[0] == "##FORMAT":
                a = line[line.find("<") + 1 : line.find(">")]
                r = re.compile(r"(?:[^,\"]|\"[^\"]*\")+")
                self.add_format(*[b.split("=")[1] for b in r.findall(a)])
            elif line[0] == "#" and line[1] != "#":
                self.sample_list = line.rstrip().split("\t")[9:]

    # return the VCF header
    def get_header(self):
        header = "\n".join(
            [
                "##fileformat=" + self.file_format,
                "##fileDate=" + time.strftime("%Y%m%d"),
                "##reference=" + self.reference,
            ]
            + [i.hstring for i in self.info_list]
            + [a.hstring for a in self.alt_list]
            + [f.hstring for f in self.format_list]
            + [
                "\t".join(
                    [
                        "#CHROM",
                        "POS",
                        "ID",
                        "REF",
                        "ALT",
                        "QUAL",
                        "FILTER",
                        "INFO",
                        "FORMAT",
                    ]
                    + self.sample_list
                )
            ]
        )
        return header

    def add_info(self, id, number, type, desc):
        if id not in [i.id for i in self.info_list]:
            inf = Info(id, number, type, desc)
            self.info_list.append(inf)

    def add_alt(self, id, desc):
        if id not in [a.id for a in self.alt_list]:
            alt = Alt(id, desc)
            self.alt_list.append(alt)

    def add_format(self, id, number, type, desc):
        if id not in [f.id for f in self.format_list]:
            fmt = Format(id, number, type, desc)
            self.format_list.append(fmt)

    def add_sample(self, name):
        self.sample_list.append(name)


class Info(object):
    def __init__(self, id, number, type, desc):
        self.id = str(id)
        self.number = str(number)
        self.type = str(type)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = (
            "##INFO=<ID="
            + self.id
            + ",Number="
            + self.number
            + ",Type="
            + self.type
            + ',Description="'
            + self.desc
            + '">'
        )


class Alt(object):
    def __init__(self, id, desc):
        self.id = str(id)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = "##ALT=<ID=" + self.id + ',Description="' + self.desc + '">'


class Format(object):
    def __init__(self, id, number, type, desc):
        self.id = str(id)
        self.number = str(number)
        self.type = str(type)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = (
            "##FORMAT=<ID="
            + self.id
            + ",Number="
            + self.number
            + ",Type="
            + self.type
            + ',Description="'
            + self.desc
            + '">'
        )


class Variant(object):
    def __init__(self, var_list, vcf):
        self.chrom = var_list[0]
        self.pos = int(var_list[1])
        self.var_id = var_list[2]
        self.ref = var_list[3]
        self.alt = var_list[4]
        self.qual = var_list[5]
        self.filter = var_list[6]
        self.sample_list = vcf.sample_list
        self.info_list = vcf.info_list
        self.info = dict()
        self.format_list = vcf.format_list
        self.active_formats = list()
        self.gts = dict()
        # make a genotype for each sample at variant
        for i in range(len(self.sample_list)):
            s_gt = var_list[9 + i].split(":")[0]
            s = self.sample_list[i]
            self.gts[s] = Genotype(self, s, s_gt)
        # import the existing fmt fields
        for i in range(len(self.sample_list)):
            s = self.sample_list[i]
            for j in zip(var_list[8].split(":"), var_list[9 + i].split(":")):
                self.gts[s].set_format(j[0], j[1])

        self.info = dict()
        i_split = [
            a.split("=") for a in var_list[7].split(";")
        ]  # temp list of split info column
        for i in i_split:
            if len(i) == 1:
                i.append(True)
            self.info[i[0]] = i[1]

    def set_info(self, field, value):
        if field in [i.id for i in self.info_list]:
            self.info[field] = value
        else:
            sys.stderr.write('\nError: invalid INFO field, "' + field + '"\n')
            exit(1)

    def get_info(self, field):
        return self.info[field]

    def get_info_string(self):
        i_list = list()
        for info_field in self.info_list:
            if info_field.id in self.info.keys():
                if info_field.type == "Flag":
                    i_list.append(info_field.id)
                else:
                    i_list.append("%s=%s" % (info_field.id, self.info[info_field.id]))
        return ";".join(i_list)

    def get_format_string(self):
        f_list = list()
        for f in self.format_list:
            if f.id in self.active_formats:
                f_list.append(f.id)
        return ":".join(f_list)

    def genotype(self, sample_name):
        if sample_name in self.sample_list:
            return self.gts[sample_name]
        else:
            sys.stderr.write('\nError: invalid sample name, "' + sample_name + '"\n')

    def get_var_string(self):
        s = "\t".join(
            map(
                str,
                [
                    self.chrom,
                    self.pos,
                    self.var_id,
                    self.ref,
                    self.alt,
                    "%0.2f" % self.qual,
                    self.filter,
                    self.get_info_string(),
                    self.get_format_string(),
                    "\t".join(
                        self.genotype(s).get_gt_string() for s in self.sample_list
                    ),
                ],
            )
        )
        return s


class Genotype(object):
    def __init__(self, variant, sample_name, gt):
        self.format = dict()
        self.variant = variant
        self.set_format("GT", gt)

    def set_format(self, field, value):
        if field in [i.id for i in self.variant.format_list]:
            self.format[field] = value
            if field not in self.variant.active_formats:
                self.variant.active_formats.append(field)
                # sort it to be in the same order as the format_list in header
                self.variant.active_formats.sort(
                    key=lambda x: [f.id for f in self.variant.format_list].index(x)
                )
        # else:
        #     sys.stderr.write('\nError: invalid FORMAT field, \"' + field + '\"\n')
        #     exit(1)

    def get_format(self, field):
        return self.format[field]

    def get_gt_string(self):
        g_list = list()
        for f in self.variant.active_formats:
            if f in self.format:
                if type(self.format[f]) == float:
                    g_list.append("%0.2f" % self.format[f])
                else:
                    g_list.append(self.format[f])
            else:
                g_list.append(".")
        return ":".join(map(str, g_list))


# primary function
def vcfToBedpe(vcf_path, output_path):

    sample = vcf_path.split("/")[-1].split(".")[0]

    vcf_file = open(vcf_path, "r")
    bedpe_out = open(os.path.join(output_path, sample + ".bedpe.tsv"), "w")

    vcf = Vcf()
    in_header = True
    sample_list = []
    processed_bnd_ids = set()

    for line in vcf_file:
        if in_header:
            if line[0] == "#":
                if line[1] != "#":
                    sample_list = line.rstrip().split("\t")[9:]
                continue
            else:
                # print header
                headerVal = [
                    "#CHROM_A",
                    "START_A",
                    "END_A",
                    "CHROM_B",
                    "START_B",
                    "END_B",
                    "ID",
                    "QUAL",
                    "STRAND_A",
                    "STRAND_B",
                    "TYPE",
                    "FILTER",
                    "INFO",
                ]

                if len(sample_list) > 0:
                    headerVal.append("FORMAT")
                    headerVal.extend(sample_list)

                bedpe_out.write("\t".join(headerVal) + "\n")

                in_header = False

        v = line.rstrip().split("\t")
        var = Variant(v, vcf)

        chrom2 = var.chrom
        b1 = var.pos
        name = v[2]
        if var.info["SVTYPE"] != "BND":
            b2 = int(var.info["END"])
        else:
            if "SECONDARY" in var.info:
                continue
            if var.var_id in processed_bnd_ids:
                continue
            processed_bnd_ids.add(var.var_id)
            if "MATEID" in var.info:
                processed_bnd_ids.update(var.info["MATEID"].split(","))
            sep = "["
            if sep not in var.alt:
                sep = "]"
            r = re.compile(r"\%s(.+?)\%s" % (sep, sep))
            if len(r.findall(var.alt)) > 0:
                chrom2, b2 = r.findall(var.alt)[0].split(":")
                b2 = int(b2)
            else:
                b2 = b1

            if "EVENT" in var.info:
                name = var.info["EVENT"]

        o1 = "."
        o2 = "."
        if "STRANDS" in var.info:
            strands = var.info["STRANDS"]
            o1 = strands[0]
            o2 = strands[1]
        elif var.info["SVTYPE"] == "BND":
            o1, o2 = _infer_bnd_strands(var.alt)

        span = [0, 0]
        if "CIPOS" in var.info:
            span = map(int, var.info["CIPOS"].split(","))
        span = list(span)
        s1 = b1 + span[0] - 1
        e1 = b1 + span[1]

        span = [0, 0]
        if "CIEND" in var.info:
            span = map(int, var.info["CIEND"].split(","))
        span = list(span)
        s2 = b2 + span[0] - 1
        e2 = b2 + span[1]

        # write bedpe
        bedpe_out.write(
            "\t".join(
                map(
                    str,
                    [
                        var.chrom,
                        s1,
                        e1,
                        chrom2,
                        s2,
                        e2,
                        name,
                        var.qual,
                        o1,
                        o2,
                        var.info["SVTYPE"],
                        var.filter,
                    ]
                    + v[7:],
                )
            )
            + "\n"
        )

    # close the files
    bedpe_out.close()
    vcf_file.close()

    # PREPARE INPUT FOR SIGPROFILERMATRIXGENERATOR
    df = pd.read_csv(os.path.join(output_path, sample + ".bedpe.tsv"), sep="\t")

    l = list(df.columns)

    cols = l[0:6] + [l[8], l[9], l[10]]
    df = df[cols]
    df.columns = [
        "chrom1",
        "start1",
        "end1",
        "chrom2",
        "start2",
        "end2",
        "strand1",
        "strand2",
        "svtype",
    ]

    # deletion, translocation, tandem-duplication, or inversion
    df["svclass"] = [
        _classify_sv(svtype, chrom1, chrom2, strand1, strand2)
        for svtype, chrom1, chrom2, strand1, strand2 in zip(
            df["svtype"], df["chrom1"], df["chrom2"], df["strand1"], df["strand2"]
        )
    ]
    df = df[
        ["chrom1", "start1", "end1", "chrom2", "start2", "end2", "svclass"]
    ]
    df2 = df[df["svclass"] != "unknown"]  # classified confidently
    unclassified = df[df["svclass"] == "unknown"]  # not classified confidentlyprint
    dropped = int(df.shape[0] - df2.shape[0])
    print(
        "Note that there were "
        + str(dropped)
        + " SV entries dropped from the VCF for sample "
        + sample
        + " because they could not be confidently classified as deletion, translocation, tandem-duplication, or inversion"
    )
    s = [sample for x in range(df2.shape[0])]
    df2.insert(0, column="sample", value=s)

    # unclassified events
    s = [sample for x in range(unclassified.shape[0])]
    unclassified.insert(0, column="sample", value=s)

    return df2, unclassified
