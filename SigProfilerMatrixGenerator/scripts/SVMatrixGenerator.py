import os
import string

import sys
import warnings
import sigProfilerPlotting as sigPlt
from math import nan
import numpy as np
import pandas as pd
from numpy import matlib
from scipy import signal as scisig
from scipy.stats import binom
from SigProfilerMatrixGenerator.scripts.vcfToBedpe import vcfToBedpe


pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore")


def unique_py(seqlist):
    seen = set()
    seen_add = seen.add
    return [x for x in seqlist if not (x in seen or seen_add(x))]


##COMPUTATION OF INTERMUTATIONAL DISTANCE
# check computation of IMD
# major difference is whether its the closest breakpoint or the breakpoint immediately preceding it


def calcIntermutDist2(subs_type, first_chrom_na=False):
    subs_type_processed = subs_type.copy()
    chr_list = unique_py(subs_type["chr"])
    pos_array_im = subs_type["position"].values
    index_orig_df = np.arange(len(subs_type_processed))
    # args_pos_list = np.argsort(pos_array_im)
    args_pos_list = []
    distPrev_list = []
    prevPos_list = []

    for c in chr_list:
        inds_chr = np.where(subs_type["chr"] == c)
        pos_array_im_c = np.sort(pos_array_im[inds_chr])
        index_orig_df[inds_chr] = index_orig_df[inds_chr][
            np.argsort(pos_array_im[inds_chr])
        ]

        if first_chrom_na:
            prevPos_arr_c = np.hstack((np.nan, pos_array_im_c.flatten()[:-1]))
        else:
            prevPos_arr_c = np.hstack((0, pos_array_im_c.flatten()[:-1]))
        distPrev_arr_c = pos_array_im_c - prevPos_arr_c
        distPrev_arr_c[distPrev_arr_c == 0] = 1
        distPrev_list = np.append(distPrev_list, distPrev_arr_c.astype(int)).flatten()
        prevPos_list = np.append(prevPos_list, prevPos_arr_c.astype(int)).flatten()
        prevPos_arr_c = []
        distPrev_arr_c = []
    subs_type_processed = subs_type_processed.reindex(index_orig_df).reset_index(
        drop=True
    )
    subs_type_processed["prevPos"] = prevPos_list
    subs_type_processed["distPrev"] = distPrev_list
    return subs_type_processed


def calcIntermutDist(subs_type, first_chrom_na=False):
    subs_type_processed = pd.DataFrame()
    for c in unique_py(subs_type["chr"]):
        subs_type_chrom = subs_type[subs_type["chr"] == c].sort_values("position")
        if first_chrom_na:
            subs_type_chrom["prevPos"] = np.hstack(
                (np.nan, subs_type_chrom["position"].values.flatten()[:-1])
            )
        else:
            subs_type_chrom["prevPos"] = np.hstack(
                (0, subs_type_chrom["position"].values.flatten()[:-1])
            )
        subs_type_chrom["distPrev"] = (
            subs_type_chrom["position"].values - subs_type_chrom["prevPos"].values
        )
        subs_type_processed = subs_type_processed.append(subs_type_chrom)
        subs_type_processed["distPrev"][subs_type_processed["distPrev"] == 0] = 1
    return subs_type_processed


def computeIMD2(chrom_df, chromosome):
    # keep track of partners

    d1 = dict(zip(list(chrom_df["start1"]), list(chrom_df["start2"])))
    d2 = dict(zip(list(chrom_df["start2"]), list(chrom_df["start1"])))
    # d = {**d1, **d2} #combine dictionaries, THIS ONLY WORKS IN PYTHON 3.5+
    d = d1.copy()
    d.update(d2)

    lb = chrom_df.iloc[:, 0:2]  # get chrom1 and start1
    rb = chrom_df.iloc[:, 3:5]  # get chrom2 and start2
    rest = chrom_df.iloc[:, 6:]

    lb = pd.DataFrame(np.concatenate((lb.values, rest.values), axis=1))
    rb = pd.DataFrame(np.concatenate((rb.values, rest.values), axis=1))

    # BREAKPOINTS ARE CONSIDERED INDIVIDUALLY

    # ['chrom1', 'start1', 'end1', 'chrom2', 'start2', 'end2', 'sample', 'svclass', 'size_bin', 'length']
    lb.columns = ["chrom1", "start1", "sample", "svclass", "size_bin", "length"]
    rb.columns = ["chrom2", "start2", "sample", "svclass", "size_bin", "length"]

    chr_lb = lb[lb.chrom1 == chromosome]
    chr_rb = rb[rb.chrom2 == chromosome]
    # print(chr_lb)
    # print(chr_rb)
    chrom_df = pd.DataFrame(np.concatenate((chr_lb.values, chr_rb.values), axis=0))
    chrom_df.columns = ["chrom", "start", "sample", "svclass", "size_bin", "length"]
    if chrom_df.shape[0] >= 10:
        # print(chrom_df['chrom'].unique())
        # assert(chrom_df['chrom'].nunique() == 1)

        # sort on 2nd column which is start coordinate
        chrom_df = chrom_df.sort_values(chrom_df.columns[1])  # CHROM, START

        coords = list(chrom_df[chrom_df.columns[1]])
        svtype = list(chrom_df.svclass)

        chrom_inter_distances = []

        # defined as the number of base pairs from one rearrangement breakpoint to the one immediately preceding it that is not its partner
        for i in range(1, len(coords)):
            j = i - 1
            while (
                j >= 0 and coords[j] == d[coords[i]]
            ):  # check if previous breakpoint is partner of this breakpoint, if it is, avoid it
                j = j - 1
            dist = coords[i] - coords[j]
            chrom_inter_distances.append(dist)

        # now we take care of the edge cases of the first and last breakpoint
        if coords[1] == d[coords[0]]:
            first_dist = coords[2] - coords[0]
        else:
            first_dist = coords[1] - coords[0]

        chrom_inter_distances = [coords[0]] + chrom_inter_distances
        chrom_df["IMD"] = chrom_inter_distances

    #     #INTERLEAVED VS NESTED CONFIGURATION
    #     configuration = ['interleaved' for i in range(len(coords))]
    #     for i in range(1, len(coords)):
    #         j = i-1
    #         while coords[j] == d[coords[i]] and not (d[coords[i]] < max(d[coords[j]], coords[j]) and coords[i] < max(d[coords[j]], coords[j]) and d[coords[i]] > min(d[coords[j]], coords[j]) and coords[i] > min(d[coords[j]], coords[j])): #check if previous breakpoint is partner of this breakpoint, if it is, avoid it
    #             j=j-1
    #         if j >= 0: #determine if we have a nested or interleaved configuration
    #             if d[coords[i]] < max(d[coords[j]], coords[j]) and coords[i] < max(d[coords[j]], coords[j]) and d[coords[i]] > min(d[coords[j]], coords[j]) and coords[i] > min(d[coords[j]], coords[j]):
    #                 configuration[i] = "nested"

    #     chrom_df["Configuration"] = configuration
    return chrom_df


# major difference is whether its the closest breakpoint or the breakpoint immediately preceding it
# distance in bp to nearest breakpoint that is not it's partner (not distance to breakpoint immediately preceding)
def computeIMD3(chrom_df, chromosome):
    # keep track of partners

    d1 = dict(zip(list(chrom_df["start1"]), list(chrom_df["start2"])))
    d2 = dict(zip(list(chrom_df["start2"]), list(chrom_df["start1"])))
    d = {**d1, **d2}  # combine dictionaries

    lb = chrom_df.iloc[:, 0:2]  # get chrom1 and start1
    rb = chrom_df.iloc[:, 3:5]  # get chrom2 and start2
    rest = chrom_df.iloc[:, 6:]

    lb = pd.DataFrame(np.concatenate((lb.values, rest.values), axis=1))
    rb = pd.DataFrame(np.concatenate((rb.values, rest.values), axis=1))

    # BREAKPOINTS ARE CONSIDERED INDIVIDUALLY

    # ['chrom1', 'start1', 'end1', 'chrom2', 'start2', 'end2', 'sample', 'svclass', 'size_bin', 'length']
    lb.columns = ["chrom1", "start1", "sample", "svclass", "size_bin", "length"]
    rb.columns = ["chrom2", "start2", "sample", "svclass", "size_bin", "length"]

    chr_lb = lb[lb.chrom1 == chromosome]
    chr_rb = rb[rb.chrom2 == chromosome]
    # print(chr_lb)
    # print(chr_rb)
    chrom_df = pd.DataFrame(np.concatenate((chr_lb.values, chr_rb.values), axis=0))
    chrom_df.columns = ["chrom", "start", "sample", "svclass", "size_bin", "length"]

    # print(chrom_df['chrom'].unique())
    # assert(chrom_df['chrom'].nunique() == 1)

    # sort on last column which is start coordinate
    chrom_df = chrom_df.sort_values(chrom_df.columns[1])  # CHROM, START

    # take care of mirrored translocations
    to_drop = []
    starts = list(chrom_df["start"])
    svtypes = list(chrom_df["svclass"])
    for i, (s, svtype) in enumerate(zip(starts, svtypes)):
        if (
            i + 1 < len(starts)
            and abs(starts[i + 1] - s) <= 100
            and svtype == "translocation"
        ):
            to_drop.append(i)

    chrom_df = chrom_df.drop(to_drop)
    chrom_df = chrom_df.sort_values(chrom_df.columns[1])

    coords = list(chrom_df[chrom_df.columns[1]])
    svtype = list(chrom_df.svclass)

    chrom_inter_distances = []

    # defined as the number of base pairs from one rearrangement breakpoint to the one closest to it that is not it's partner
    for i in range(1, len(coords) - 1):
        j = i - 1
        k = i + 1
        while (
            j >= 0 and coords[j] == d[coords[i]]
        ):  # check if previous breakpoint is partner of this breakpoint, if it is, avoid it
            j = j - 1
        while k < len(coords) and coords[k] == d[coords[i]]:
            k = k + 1
        if j >= 0 and k < len(coords):
            if coords[i] - coords[j] == 0:
                dist = coords[k] - coords[i]
            elif coords[k] - coords[i] == 0:
                dist = coords[i] - coords[j]
            else:
                dist = min(coords[i] - coords[j], coords[k] - coords[i])
        elif j < 0:
            dist = coords[k] - coords[i]
        else:
            dist = coords[i] - coords[j]

        if dist == 0 and svtype[i] == "translocation":
            print(coords[j], coords[i], coords[k], dist)
            # print(len(coords))
        chrom_inter_distances.append(dist)
        if dist == 1:
            print(coords[j], coords[i], coords[k], svtype[i])

    # now we take care of the edge cases of the first and last breakpoint

    if coords[1] == d[coords[0]]:
        first_dist = coords[2] - coords[0]
    else:
        first_dist = coords[1] - coords[0]

    if coords[-2] == d[coords[-1]]:
        last_dist = coords[-1] - coords[-3]
    else:
        last_dist = coords[-1] - coords[-2]

    chrom_inter_distances = [first_dist] + chrom_inter_distances
    chrom_inter_distances.append(last_dist)
    chrom_df["IMD"] = chrom_inter_distances

    # INTERLEAVED VS NESTED CONFIGURATION
    configuration = ["interleaved" for i in range(len(coords))]
    for i in range(1, len(coords)):
        j = i - 1
        while coords[j] == d[coords[i]] and not (
            d[coords[i]] < max(d[coords[j]], coords[j])
            and coords[i] < max(d[coords[j]], coords[j])
            and d[coords[i]] > min(d[coords[j]], coords[j])
            and coords[i] > min(d[coords[j]], coords[j])
        ):  # check if previous breakpoint is partner of this breakpoint, if it is, avoid it
            j = j - 1
        if j >= 0:  # determine if we have a nested or interleaved configuration
            if (
                d[coords[i]] < max(d[coords[j]], coords[j])
                and coords[i] < max(d[coords[j]], coords[j])
                and d[coords[i]] > min(d[coords[j]], coords[j])
                and coords[i] > min(d[coords[j]], coords[j])
            ):
                configuration[i] = "nested"

    chrom_df["Configuration"] = configuration
    return chrom_df


def unique_py(seqlist):
    seen = set()
    seen_add = seen.add
    return [x for x in seqlist if not (x in seen or seen_add(x))]


def calcIntermutDist(subs_type, first_chrom_na=False):
    subs_type_processed = pd.DataFrame()
    for c in unique_py(subs_type["chr"]):
        subs_type_chrom = subs_type[subs_type["chr"] == c].sort_values("position")
        if first_chrom_na:
            subs_type_chrom["prevPos"] = np.hstack(
                (np.nan, subs_type_chrom["position"].values.flatten()[:-1])
            )
        else:
            subs_type_chrom["prevPos"] = np.hstack(
                (0, subs_type_chrom["position"].values.flatten()[:-1])
            )
        subs_type_chrom["distPrev"] = (
            subs_type_chrom["position"].values - subs_type_chrom["prevPos"].values
        )
        subs_type_processed = subs_type_processed.append(subs_type_chrom)
        subs_type_processed["distPrev"][subs_type_processed["distPrev"] == 0] = 1
    return subs_type_processed


def calcIntermutDist2(subs_type, first_chrom_na=False):
    subs_type_processed = subs_type.copy()
    chr_list = unique_py(subs_type["chr"])
    pos_array_im = subs_type["position"].values
    index_orig_df = np.arange(len(subs_type_processed))
    # args_pos_list = np.argsort(pos_array_im)
    args_pos_list = []
    distPrev_list = []
    prevPos_list = []

    for c in chr_list:
        inds_chr = np.where(subs_type["chr"] == c)
        pos_array_im_c = np.sort(pos_array_im[inds_chr])
        index_orig_df[inds_chr] = index_orig_df[inds_chr][
            np.argsort(pos_array_im[inds_chr])
        ]

        if first_chrom_na:
            prevPos_arr_c = np.hstack((np.nan, pos_array_im_c.flatten()[:-1]))
        else:
            prevPos_arr_c = np.hstack((0, pos_array_im_c.flatten()[:-1]))
        distPrev_arr_c = pos_array_im_c - prevPos_arr_c
        distPrev_arr_c[distPrev_arr_c == 0] = 1
        distPrev_list = np.append(distPrev_list, distPrev_arr_c.astype(int)).flatten()
        prevPos_list = np.append(prevPos_list, prevPos_arr_c.astype(int)).flatten()
        prevPos_arr_c = []
        distPrev_arr_c = []
    subs_type_processed = subs_type_processed.reindex(index_orig_df).reset_index(
        drop=True
    )
    subs_type_processed["prevPos"] = prevPos_list
    subs_type_processed["distPrev"] = distPrev_list
    return subs_type_processed


def computeMAD(v):
    mad = np.median(np.abs(v - np.median(v)))
    return mad


def getMad(x, k=25):
    # Remove observations that are equal to zero; are likely to be imputed, should not contribute to sd:
    x = x[x != 0]
    runMedian = scisig.medfilt(x, k)
    dif = x - runMedian
    # SD = stats.median_abs_deviation(dif)
    SD = computeMAD(dif)
    return SD


def exactPcf(y, kmin, gamma, flag=True):
    if flag:
        yest = np.random.rand(len(y))
    else:
        yest = flag
    N = len(y)
    yhat = np.zeros(N)
    if N < 2 * kmin:
        if flag:
            results = {
                "Lengde": N,
                "sta": 1,
                "mean": np.mean(y),
                "nIntervals": 1,
                "yhat": np.repeat(np.mean(y), N, axis=0),
            }
            return results
        else:
            results = {"Lengde": N, "sta": 1, "mean": np.mean(y), "nIntervals": 1}
            return results

    initSum = sum(y[0:kmin])
    initKvad = sum(y[0:kmin] ** 2)
    initAve = initSum / kmin
    bestCost = np.zeros(N)
    bestCost[kmin - 1] = initKvad - initSum * initAve
    bestSplit = np.zeros(N)
    bestAver = np.zeros(N)
    bestAver[kmin - 1] = initAve
    Sum = np.zeros(N)
    Kvad = np.zeros(N)
    Aver = np.zeros(N)
    Cost = np.zeros(N)
    kminP1 = kmin + 1
    for k in range(kminP1, 2 * kmin):
        Sum[kminP1 - 1 : k] = Sum[kminP1 - 1 : k] + y[k - 1]
        Aver[kminP1 - 1 : k] = Sum[kminP1 - 1 : k] / (range((k - kmin), 0, -1))
        Kvad[kminP1 - 1 : k] = Kvad[kminP1 - 1 : k] + (y[k - 1] ** 2)
        bestAver[k - 1] = (initSum + Sum[kminP1 - 1]) / k
        bestCost[k - 1] = (initKvad + Kvad[kminP1 - 1]) - (k * bestAver[k - 1] ** 2)

    for n in range(2 * kmin, N + 1):
        yn = y[n - 1]
        yn2 = y[n - 1] ** 2
        Sum[kminP1 - 1 : n] = Sum[kminP1 - 1 : n] + yn
        Aver[kminP1 - 1 : n] = Sum[kminP1 - 1 : n] / (range((n - kmin), 0, -1))
        Kvad[kminP1 - 1 : n] = Kvad[kminP1 - 1 : n] + yn2
        nMkminP1 = n - kmin + 1
        Cost[kminP1 - 1 : nMkminP1] = (
            bestCost[kmin - 1 : (n - kmin)]
            + Kvad[kminP1 - 1 : nMkminP1]
            - Sum[kminP1 - 1 : nMkminP1] * Aver[kminP1 - 1 : nMkminP1]
            + gamma
        )
        Pos = np.argmin(Cost[kminP1 - 1 : nMkminP1]) + kmin
        cost = Cost[Pos]
        aver = Aver[Pos]
        totAver = (Sum[kminP1 - 1] + initSum) / n
        totCost = (Kvad[kminP1 - 1] + initKvad) - n * totAver * totAver
        # if len(totCost)==0 or len(cost)==0 :
        #     raise ValueError('Something is Wrong')
        if totCost < cost:
            Pos = 1
            cost = totCost
            aver = totAver
        bestCost[n - 1] = cost
        bestAver[n - 1] = aver
        bestSplit[n - 1] = Pos
    n = N
    antInt = 1
    yest = np.array(yest, dtype=bool)
    bestSplit = np.array(bestSplit, dtype=int)

    if yest.any():
        while n > 0:
            yhat[(bestSplit[n - 1]) : n] = bestAver[n - 1]
            n = bestSplit[n - 1]
            antInt = antInt + 1
    else:
        while n > 0:
            n = bestSplit[n - 1]
            antInt = antInt + 1

    antInt = antInt - 1
    # """
    n = N
    lengde = np.repeat(0, antInt, axis=0)
    start = np.repeat(0, antInt, axis=0)
    verdi = np.repeat(0, antInt, axis=0)
    oldSplit = n
    antall = antInt
    while n > 0:
        start[antall - 1] = bestSplit[n - 1] + 1
        lengde[antall - 1] = oldSplit - bestSplit[n - 1]
        verdi[antall - 1] = bestAver[n - 1]
        n = bestSplit[n - 1]
        oldSplit = n
        antall = antall - 1
    if yest.any():
        results = {
            "Lengde": lengde,
            "sta": start,
            "mean": verdi,
            "nIntervals": antInt,
            "yhat": yhat,
        }
        return results
    else:
        results = {"Lengde": lengde, "sta": start, "mean": verdi, "nIntervals": antInt}
        return results


def unique_py(seqlist):
    seen = set()
    seen_add = seen.add
    return [x for x in seqlist if not (x in seen or seen_add(x))]


def pbinom(q, size, prob=0.5):
    """
    Calculates the cumulative of the binomial distribution
    """
    result = binom.cdf(k=q, n=size, p=prob, loc=0)
    return result


def assignPvalues(kat_regions, chrom_bps, bp_rate=np.nan):
    if len(kat_regions) > 0:
        if np.isnan(bp_rate):
            left_bp = min(chrom_bps["pos"])
            right_bp = max(chrom_bps["pos"])
            bp_rate = len(chrom_bps.values) / (right_bp - left_bp)
        kat_regions["pvalue"] = 1 - pbinom(
            kat_regions["number_bps"].values,
            kat_regions["end_bp"].values - kat_regions["start_bp"].values,
            bp_rate,
        )
        kat_regions["d_seg"] = kat_regions["number_bps"].values / (
            kat_regions["end_bp"].values - kat_regions["start_bp"].values
        )
        kat_regions["rate_factor"] = kat_regions["d_seg"] / bp_rate
    return kat_regions


def assignPvalues2(kat_regions, chrom_bps, bp_rate=np.nan):
    if len(kat_regions) > 0:
        if np.isnan(bp_rate):
            bp_vals = chrom_bps["pos"].values
            left_bp = np.min(bp_vals)
            right_bp = np.max(bp_vals)
            bp_rate = len(bp_vals) / (right_bp - left_bp)
        kat_regions["pvalue"] = 1 - pbinom(
            kat_regions["number_bps"].values,
            kat_regions["end_bp"].values - kat_regions["start_bp"].values,
            bp_rate,
        )
        kat_regions["d_seg"] = kat_regions["number_bps"].values / (
            kat_regions["end_bp"].values - kat_regions["start_bp"].values
        )
        kat_regions["rate_factor"] = kat_regions["d_seg"] / bp_rate
    return kat_regions


def hotspotInfo(kat_regions_all, subs, segInterDist):
    if len(kat_regions_all) > 0:
        kat_regions_all = kat_regions_all.reset_index(drop=True)
        for index in range(len(kat_regions_all)):
            subs_hotspot = subs[
                int(kat_regions_all["firstBp"][index]) : int(
                    kat_regions_all["lastBp"][index]
                )
                + 1
            ]
            kat_regions_all["start_bp"][index] = min(subs_hotspot["pos"])
            kat_regions_all["end_bp"][index] = max(subs_hotspot["pos"])
            kat_regions_all["length_bp"][index] = (
                kat_regions_all["end_bp"][index] - kat_regions_all["start_bp"][index]
            )
            kat_regions_all["number_bps"][index] = len(subs_hotspot)
            if "is_clustered" in subs_hotspot:
                kat_regions_all["number_bps_clustered"][index] = sum(
                    subs_hotspot["is_clustered"]
                )
            else:
                kat_regions_all["number_bps_clustered"][index] = 0
            if len(segInterDist) > 0 & np.isnan(kat_regions_all["avgDist_bp"][index]):
                kat_regions_all["avgDist_bp"][index] = np.mean(
                    segInterDist[
                        int(kat_regions_all["firstBp"][index]) : (
                            int(kat_regions_all["lastBp"][index]) + 1
                        )
                    ]
                )
            kat_regions_all["no_samples"][index] = len(
                unique_py(list(subs_hotspot["sample"]))
            )
            if "pf" in subs_hotspot:
                kat_regions_all["no_del"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 2]
                )
                kat_regions_all["no_dup"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 4]
                )
                kat_regions_all["no_inv"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 1 | subs_hotspot["pf"] == 8]
                )
                kat_regions_all["no_trn"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 32]
                )
    return kat_regions_all


def hotspotInfo2(kat_regions_all, subs, segInterDist):
    if len(kat_regions_all) > 0:
        pos_arr = subs["pos"].values
        kat_firstBp = kat_regions_all["firstBp"].values
        kat_lastBp = kat_regions_all["lastBp"].values
        kat_start_bp = kat_regions_all["start_bp"].values
        kat_end_bp = kat_regions_all["end_bp"].values
        kat_samples = list(subs["sample"])
        kat_regions_all = kat_regions_all.reset_index(drop=True)
        for index in range(len(kat_regions_all)):
            subs_hotspot = pos_arr[int(kat_firstBp[index]) : int(kat_lastBp[index]) + 1]
            kat_regions_all["start_bp"][index] = np.min(subs_hotspot)
            kat_regions_all["end_bp"][index] = np.max(subs_hotspot)
            kat_regions_all["length_bp"][index] = (
                kat_end_bp[index] - kat_start_bp[index]
            )
            kat_regions_all["number_bps"][index] = len(subs_hotspot)
            if "is_clustered" in kat_regions_all:
                subs_is_clust = kat_regions_all["is_clustered"].values[
                    int(kat_firstBp[index]) : int(kat_lastBp[index]) + 1
                ]
                kat_regions_all["number_bps_clustered"][index] = np.sum(subs_is_clust)
            else:
                kat_regions_all["number_bps_clustered"][index] = 0
            if len(segInterDist) > 0 & np.isnan(kat_regions_all["avgDist_bp"][index]):
                kat_regions_all["avgDist_bp"][index] = np.mean(
                    segInterDist[int(kat_firstBp[index]) : (int(kat_lastBp[index]) + 1)]
                )
            kat_regions_all["no_samples"][index] = len(
                unique_py(
                    [
                        kat_samples[val]
                        for val in range(
                            int(kat_firstBp[index]), int(kat_lastBp[index]) + 1
                        )
                    ]
                )
            )
            if "pf" in kat_regions_all:
                kat_regions_all["no_del"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 2]
                )
                kat_regions_all["no_dup"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 4]
                )
                kat_regions_all["no_inv"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 1 | subs_hotspot["pf"] == 8]
                )
                kat_regions_all["no_trn"][index] = len(
                    subs_hotspot[subs_hotspot["pf"] == 32]
                )
    return kat_regions_all


def extract_kat_regions(
    res,
    imd,
    subs,
    kmin_samples,
    pvalue_thresh,
    rate_factor_thresh,
    doMerging,
    kmin_filter,
    bp_rate,
):
    segInterDist = res["yhat"]
    kataegis_threshold = imd
    kat_regions_all = pd.DataFrame()
    positions = subs["pos"]
    katLoci = (
        segInterDist <= kataegis_threshold
    )  # flag specifying if a point is in a peak
    if sum(katLoci > 0):
        start_regions = (
            np.asarray(
                np.where(
                    katLoci[1:] & ~(katLoci[:-1])
                    | (
                        (katLoci[1:] & (katLoci[:-1]))
                        & (segInterDist[1:] != segInterDist[: len(katLoci) - 1])
                    )
                )
            )[0]
            + 1
        )
        if katLoci[0]:
            start_regions = np.hstack((0, start_regions))
        end_regions = np.asarray(
            np.where(
                ~katLoci[1:] & (katLoci[:-1])
                | (
                    (katLoci[1:] & (katLoci[:-1]))
                    & (segInterDist[1:] != segInterDist[:-1])
                )
            )
        )[0]
        if katLoci[-1]:
            end_regions = np.hstack((end_regions, len(katLoci) - 1))

        # handling Special cases
        if (
            len(end_regions) + len(start_regions) > 0
        ):  # if there are any discontinuities in the segmentation at all
            if (len(end_regions) == 1) & (len(start_regions) == 0):
                start_regions = 0
            elif (len(end_regions) == 0) & (len(start_regions) == 1):
                end_regions = len(positions) - 1
            elif (end_regions[0] < start_regions[0]) & (
                start_regions[-1] > end_regions[-1]
            ):
                start_regions = np.hstack((0, start_regions))
                end_regions = np.hstack((end_regions, len(positions) - 1))
            elif end_regions[0] < start_regions[0]:
                # starts will be one shorter
                start_regions = np.hstack((0, start_regions))
            elif start_regions[-1] > end_regions[-1]:
                end_regions = np.hstack((end_regions, len(positions) - 1))
        # prepare a data structure that will be later filled up

        columnslist = [
            "chr",
            "start_bp",
            "end_bp",
            "length_bp",
            "number_bps",
            "number_bps_clustered",
            "avgDist_bp",
            "no_samples",
            "no_del",
            "no_dup",
            "no_inv",
            "np_trn",
            "firstBp",
            "lastBp",
        ]
        temp = matlib.repmat(np.nan, len(start_regions), len(columnslist))

        kat_regions_all = pd.DataFrame(temp, columns=columnslist)
        kat_regions_all["chr"] = subs["chr"][subs["chr"].index[0]]
        kat_regions_all["firstBp"] = start_regions
        kat_regions_all["lastBp"] = end_regions
        # print('intermittent= ', time.time()-t)
        # pdb.set_trace()
        # t = time.time()
        kat_regions_all = hotspotInfo2(kat_regions_all, subs, segInterDist)
        # print('hotspot1= ', time.time()-t)
        # pdb.set_trace()

        step_segInterDist_left = [np.nan] * len(segInterDist)
        step_segInterDist_left[1 : len(segInterDist)] = (
            segInterDist[1 : len(segInterDist)]
            - segInterDist[0 : len(segInterDist) - 1]
        )
        step_segInterDist_right = [np.nan] * len(segInterDist)
        step_segInterDist_right[0 : len(segInterDist) - 1] = (
            segInterDist[0 : len(segInterDist) - 1]
            - segInterDist[1 : len(segInterDist)]
        )
        kat_regions_all["step_left"] = list(
            step_segInterDist_left[i] for i in start_regions
        )
        kat_regions_all["step_right"] = list(
            step_segInterDist_right[i] for i in end_regions
        )

        # run the filters on the regions of increased frequency
        # make sure there are at least kmin samples
        # t =time.time()
        if (not kat_regions_all.empty) & (len(kat_regions_all) > 0):
            kat_regions_all = kat_regions_all[
                kat_regions_all["no_samples"] >= kmin_samples
            ]

        # make sure there are at least kmin.filter breakpoints
        if not np.isnan(kmin_filter):
            kat_regions_all = kat_regions_all[
                kat_regions_all["number_bps"] >= kmin_filter
            ]

        if (not kat_regions_all.empty) & (len(kat_regions_all) > 0):
            kat_regions_all = assignPvalues(kat_regions_all, subs, bp_rate)
            kat_regions_all = kat_regions_all[
                kat_regions_all["pvalue"] <= pvalue_thresh
            ]
            kat_regions_all = kat_regions_all[
                kat_regions_all["rate_factor"] >= rate_factor_thresh
            ]
        # merge segments if both were found to be peaks
        kat_regions_all = kat_regions_all.reset_index(drop=True)
        if doMerging:
            if len(kat_regions_all) > 1:
                for r in range(1, len(kat_regions_all)):
                    if (
                        kat_regions_all["lastBp"][r - 1]
                        == kat_regions_all["firstBp"][r] - 1
                    ):
                        # merge two segments
                        kat_regions_all["firstBp"][r] = kat_regions_all["firstBp"][
                            r - 1
                        ]
                        kat_regions_all["firstBp"][r - 1] = np.nan
                        kat_regions_all["lastBp"][r - 1] = np.nan
                        kat_regions_all["avgDist_bp"][
                            r
                        ] = (
                            np.nan
                        )  # this will need to be updated as segments are being merged
            # remove some of the merged segments
            columns_backup = kat_regions_all.columns.to_list()
            kat_regions_all = kat_regions_all[
                list(
                    not (np.isnan(kat_regions_all["firstBp"].values[i]))
                    and not np.isnan(kat_regions_all["lastBp"].values[i])
                    for i in range(len(kat_regions_all))
                )
            ]
            if kat_regions_all.empty:
                kat_regions_all = pd.DataFrame(columns=columns_backup)
            kat_regions_all = hotspotInfo2(kat_regions_all, subs, segInterDist)
            kat_regions_all = assignPvalues(kat_regions_all, subs, bp_rate)
    return kat_regions_all


#######################################################


def annotateBedpe(sv_bedpe):
    # ,kmin,kmin_samples,gamma_sdev=25,PEAK_FACTOR,thresh_dist,gamma,kmin_filter
    # sv_bedpe = data
    sv_bedpe["id"] = sv_bedpe.index + 1  # add an id to the rearrangement
    sv_bedpe = sv_bedpe.astype({"chrom1": str}, {"chrom2": str})
    # functions below expect rows to be organised by chromosomes and ordered by position on the chromosome
    # prepare a dataframe for the calculation
    left = pd.DataFrame(sv_bedpe[["chrom1", "start1", "sample", "id"]])
    right = pd.DataFrame(sv_bedpe[["chrom2", "start2", "sample", "id"]])
    left = left.astype({"chrom1": str})
    right = right.astype({"chrom2": str})
    cncd = pd.DataFrame(
        np.concatenate([left.values, right.values]),
        columns=("chr", "position", "sample", "id"),
    )
    cncd["isLeft"] = True
    cncd["isLeft"][len(left) : len(left) + len(right)] = False
    cncd = cncd[["chr", "position", "sample", "isLeft", "id"]]

    sample_bps = pd.DataFrame(columns=cncd.columns)
    for chromi in unique_py(cncd["chr"]):
        sample_bps = pd.concat(
            [sample_bps, cncd[cncd["chr"] == chromi].sort_values("position", kind="mergesort")],
            ignore_index=True,
        )

    sample_bps.index = pd.RangeIndex(len(sample_bps.index)) + 1
    genome_size = 3 * 10**9
    MIN_BPS = (
        10  # minimal number of breakpoints on a chromosome to do any any segmentation
    )
    logScale = False
    exp_dist = genome_size / len(sample_bps)
    gamma_sdev = 25  #
    PEAK_FACTOR = 10
    thresh_dist = np.nan

    if logScale:
        sample_bps["intermut_dist"] = np.log10(
            calcIntermutDist2(sample_bps, first_chrom_na=False)["distPrev"].values
        )
        if np.isnan(thresh_dist):
            thresh_dist = np.log10(exp_dist / PEAK_FACTOR)
    else:
        sample_bps["intermut_dist"] = calcIntermutDist2(
            sample_bps, first_chrom_na=False
        )["distPrev"].values
        if np.isnan(thresh_dist):
            thresh_dist = exp_dist / PEAK_FACTOR

    gamma = np.nan
    if np.isnan(gamma) & ~np.isnan(gamma_sdev):
        # compute the mean absolute deviation
        sdev = getMad(sample_bps["intermut_dist"].values)
        gamma = gamma_sdev * sdev

    sample_bps["is_clustered_single"] = False
    all_kat_regions = pd.DataFrame()
    sample_bps["mean_intermut_dist"] = np.nan
    for chrom in unique_py(sample_bps["chr"]):  # loop over chromosomes
        sample_bps_flag = (
            sample_bps["chr"] == chrom
        )  # breakpoints on a current chromosome
        if (
            sum(sample_bps_flag) > MIN_BPS
        ):  # if there are enough breakpoints on a chromosome to run pcf
            data_points = sample_bps["intermut_dist"][sample_bps_flag]
            kmin = 10
            res = exactPcf(data_points.values, kmin, gamma, True)
            sample_bps["mean_intermut_dist"][sample_bps_flag] = res["yhat"]
            # prepare the points for pcf
            subs = pd.DataFrame(columns=["chr", "pos", "sample"])
            subs["chr"] = sample_bps["chr"][sample_bps_flag]
            subs["pos"] = sample_bps["position"][sample_bps_flag]
            subs["sample"] = sample_bps["sample"][sample_bps_flag]
            (
                kmin_samples,
                kmin_filter,
                doMerging,
                pvalue_thresh,
                rate_factor_thresh,
                bp_rate,
            ) = (1, kmin, True, 1, 1, np.nan)
            kat_regions = extract_kat_regions(
                res,
                thresh_dist,
                subs,
                kmin_samples,
                pvalue_thresh,
                rate_factor_thresh,
                doMerging,
                kmin_filter,
                bp_rate,
            )

            all_kat_regions = pd.concat([all_kat_regions, kat_regions], axis=0)
            if not kat_regions.empty & len(kat_regions) > 0:
                for k in range(len(kat_regions)):
                    ind = np.where(sample_bps_flag)[0]
                    temp = sample_bps["is_clustered_single"].values[ind]
                    temp[
                        int(kat_regions["firstBp"][k]) : int(kat_regions["lastBp"][k])
                        + 1
                    ] = True
                    sample_bps["is_clustered_single"][ind[temp] + 1] = True
        else:
            sample_bps["mean_intermut_dist"][sample_bps_flag] = np.mean(
                sample_bps["intermut_dist"][sample_bps_flag]
            )

    if (
        not logScale
    ):  # even if pcf was run on non-logged distances, the output is logged
        sample_bps["intermut_dist"] = np.log10(
            sample_bps["intermut_dist"].values.astype(float)
        )
        sample_bps["mean_intermut_dist"] = np.log10(
            sample_bps["mean_intermut_dist"].values.astype(float)
        )
    # a rearrangement is in a cluster if any of its breakpoints are

    sample_bps["is_clustered"] = sample_bps["is_clustered_single"]
    sv_bedpe["is_clustered"] = np.nan

    check_exist_list = sample_bps["id"][sample_bps["is_clustered"]]
    sample_bps["is_clustered"][
        np.isin(sample_bps["id"].values, check_exist_list.values)
    ] = True
    sv_bedpe["is_clustered"] = np.isin(
        sv_bedpe["id"], sample_bps["id"][sample_bps["is_clustered"]]
    )
    sv_bedpe = processBEDPE(sv_bedpe)
    result = {"sv_bedpe": sv_bedpe, "kat_regions": all_kat_regions}
    return result


def generateSVMatrix(input_dir, project, output_dir, plot=True, skip=False):
    # create output_dir if it does not yet exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, project + "_logfile.txt"), "w") as fout:
        if input_dir[-1] != "/":
            input_dir = input_dir + "/"
        all_samples = []  # list of dataframes for each sample

        vcf = False  # assumes BEDPE
        for file in os.listdir(input_dir):
            if file.endswith(".vcf"):
                vcf = True
                break

        if vcf:  # dealing with VCF
            for f in os.listdir(input_dir):
                if f.endswith(".vcf"):
                    fout.write("Converting " + f + " to bedpe format\n")
                    sample = f.split(".")[0]
                    try:
                        bedpe, unclassified = vcfToBedpe(input_dir + f, input_dir)
                        bedpe.to_csv(
                            os.path.join(input_dir, sample + ".bedpe"),
                            sep="\t",
                            index=None,
                        )
                        unclassified.to_csv(
                            os.path.join(output_dir, sample + ".unclassified.bedpe"),
                            sep="\t",
                            index=None,
                        )
                    except Exception as e:
                        print(
                            f"Error in converting VCF to BEDPE for sample {sample}. The error was: {e}"
                        )
                    fout.write(
                        "Performed conversion of VCF to BEDPE and outputted bedpe file to "
                        + str(input_dir + sample + ".bedpe" + "\n")
                    )
                    fout.write(
                        "Note that events that could not be classified were outputted to "
                        + str(output_dir + sample + ".unclassified.txt" + "\n")
                    )

        for f in os.listdir(input_dir):
            if os.path.isfile(input_dir + f) and f.endswith(".bedpe"):
                fout.write("Generating count vector for " + f + "\n")
                data = pd.read_csv(input_dir + f, sep="\t")
                if data.shape[0] == 0:
                    fout.write("SKIPPING " + str(f) + "because it has 0 SVs")
                    continue
                elif (
                    "sample" not in data.columns
                    or len(data["sample"].iloc[0]) <= 1
                    or "chrom1" not in data.columns
                    or "chrom2" not in data.columns
                    or "start1" not in data.columns
                    or "start2" not in data.columns
                    or "end1" not in data.columns
                    or "end2" not in data.columns
                ) and skip == False:
                    raise Exception(
                        "Please ensure that there is a sample column containing the name of the sample"
                    )
                elif (
                    "sample" not in data.columns
                    or len(data["sample"].iloc[0]) <= 1
                    or "chrom1" not in data.columns
                    or "chrom2" not in data.columns
                    or "start1" not in data.columns
                    or "start2" not in data.columns
                    or "end1" not in data.columns
                    or "end2" not in data.columns
                ) and skip == True:
                    print(
                        "Warning: it appears that "
                        + str(f)
                        + " may not have the correct input format, please check for required columns that are missing"
                    )
                    continue
                else:
                    # get annotated bedpe for a single sample
                    result = annotateBedpe(data)

                all_samples.append(result["sv_bedpe"])

    if len(all_samples) < 1:
        fout.write(
            "Warning: unable to generate SV matrix, as all samples have 0 classified SVs"
        )
        return None

    matrix = tsv2matrix(all_samples, project, output_dir)
    out_file = os.path.join(output_dir, project + ".SV32.matrix.tsv")
    matrix.to_csv(out_file, sep="\t")
    print("Saved matrix to " + out_file)

    if plot == True:
        sigPlt.plotSV(
            matrix,
            output_dir,
            project,
            savefig_format="pdf",
            percentage=False,
            aggregate=True,
        )

    return matrix


# reformat input bedpe files
def processBEDPE(df):
    """A function that processes a given bedpe file produced by an SV caller"""

    # CHECK FORMAT OF CHROMOSOME COLUMN ("chr1" vs. "1"), needs to be the latter
    if not str(df["chrom1"][0]).isdigit():
        if df["chrom1"][0].startswith("chr"):
            chrom1 = []
            chrom2 = []
            for a, b in zip(df["chrom1"], df["chrom2"]):
                if a.startswith("chr") or b.startswith("chr"):
                    a = a[3:]
                    b = b[3:]
                    chrom1.append(a)
                    chrom2.append(b)
                else:
                    break

            df["chrom1"] = chrom1
            df["chrom2"] = chrom2

    # df = df[(df["chrom1"] != 'Y') & (df["chrom2"] != 'Y')]

    if "strand1" in df.columns and "strand2" in df.columns:
        df = df[
            [
                "chrom1",
                "start1",
                "end1",
                "chrom2",
                "start2",
                "end2",
                "strand1",
                "strand2",
                "sample",
                "is_clustered",
            ]
        ]
    else:
        df = df[
            [
                "chrom1",
                "start1",
                "end1",
                "chrom2",
                "start2",
                "end2",
                "sample",
                "svclass",
                "is_clustered",
            ]
        ]
    df = df.astype(
        {
            df.columns[1]: "int32",
            df.columns[2]: "int32",
            df.columns[4]: "int32",
            df.columns[5]: "int32",
            df.columns[0]: "str",
            df.columns[3]: "str",
        }
    )

    lengths = []
    if "svclass" not in df.columns:
        if "strand1" not in df.columns or "strand2" not in df.columns:
            raise Exception(
                "cannot classify rearrangements: svclass column missing, and cannot compute it because strand1 and strand2 are missing."
            )
        else:
            svclass = []
            for row in df.itertuples():
                if row.chrom1 != row.chrom2:
                    sv = "translocation"
                    svclass.append(sv)
                    # print(row)
                elif (row.strand1 == "+" and row.strand2 == "-") or (
                    row.strand1 == "-" and row.strand2 == "+"
                ):
                    sv = "inversion"
                    svclass.append(sv)
                elif row.strand1 == "+" and row.strand2 == "+":
                    sv = "deletion"
                    svclass.append(sv)
                elif row.strand1 == "-" and row.strand2 == "-":
                    sv = "tandem-duplication"
                    svclass.append(sv)
                else:
                    raise Exception(
                        "cannot classify rearrangements: svclass column missing, and cannot compute it because strand1 and strand2 are not in the proper format."
                    )
            # f.write(svclass)
            df["svclass"] = svclass
    else:
        svclass = list(df["svclass"])

    # GET SIZE
    sizes = [0 for x in svclass]
    i = -1
    for row in df.itertuples():
        i = i + 1
        if row.svclass != "translocation":
            lengths.append(abs(row.start1 - row.start2))
            l = abs(row.start1 - row.start2) / 1000000  # covert to megabases
            # if abs(row.start1 - row.start2) < 1000:
            #     print(row.svclass, abs(row.start1 - row.start2), row.sample, row.is_clustered)
            if l <= 0.010:
                size = "1-10Kb"
                sizes[i] = size
            elif l > 0.01 and l <= 0.1:
                size = "10-100Kb"
                sizes[i] = size
            elif l > 0.1 and l <= 1:
                size = "100Kb-1Mb"
                sizes[i] = size
            elif l > 1 and l <= 10:
                size = "1Mb-10Mb"
                sizes[i] = size
            else:
                size = ">10Mb"
                sizes[i] = size
        else:
            sizes[i] = "0"
            lengths.append(abs(row.start1 - row.start2))
            # print(row)

    df["size_bin"] = sizes
    df["length"] = lengths

    df = df.filter(
        items=[
            "chrom1",
            "start1",
            "end1",
            "chrom2",
            "start2",
            "end2",
            "sample",
            "svclass",
            "size_bin",
            "length",
            "is_clustered",
        ]
    )

    to_remove = []
    # remove SV's less than 1KB (unless its a translocation)
    for row in df.itertuples():
        index = row.Index
        if row.svclass != "translocation" and row.length < 1000:
            to_remove.append(index)
            # print(row)

    df.drop(df.index[to_remove], inplace=True)
    return df


def tsv2matrix(sv_bedpe_list, project, output_dir):
    features = [
        "clustered_del_1-10Kb",
        "clustered_del_10-100Kb",
        "clustered_del_100Kb-1Mb",
        "clustered_del_1Mb-10Mb",
        "clustered_del_>10Mb",
        "clustered_tds_1-10Kb",
        "clustered_tds_10-100Kb",
        "clustered_tds_100Kb-1Mb",
        "clustered_tds_1Mb-10Mb",
        "clustered_tds_>10Mb",
        "clustered_inv_1-10Kb",
        "clustered_inv_10-100Kb",
        "clustered_inv_100Kb-1Mb",
        "clustered_inv_1Mb-10Mb",
        "clustered_inv_>10Mb",
        "clustered_trans",
        "non-clustered_del_1-10Kb",
        "non-clustered_del_10-100Kb",
        "non-clustered_del_100Kb-1Mb",
        "non-clustered_del_1Mb-10Mb",
        "non-clustered_del_>10Mb",
        "non-clustered_tds_1-10Kb",
        "non-clustered_tds_10-100Kb",
        "non-clustered_tds_100Kb-1Mb",
        "non-clustered_tds_1Mb-10Mb",
        "non-clustered_tds_>10Mb",
        "non-clustered_inv_1-10Kb",
        "non-clustered_inv_10-100Kb",
        "non-clustered_inv_100Kb-1Mb",
        "non-clustered_inv_1Mb-10Mb",
        "non-clustered_inv_>10Mb",
        "non-clustered_trans",
    ]
    svclass_mapping = {
        "deletion": "del",
        "tandem-duplication": "tds",
        "inversion": "inv",
        "translocation": "trans",
    }
    if len(sv_bedpe_list) <= 1:
        warnings.warn(
            "There seems to be <= 1 samples, please ensure the sample column contains a unique sample name"
        )
    df = pd.concat(sv_bedpe_list)  # one master table with all samples
    out_file = os.path.join(output_dir, project + ".SV32.annotated.tsv")
    df.to_csv(out_file, index=False, sep="\t")
    print("Saved annotated bedpe to " + out_file)
    samples = list(df["sample"].unique())
    arr = np.zeros((32, len(samples)), dtype="int")
    nmf_matrix = pd.DataFrame(arr, index=features, columns=samples)
    for row in df.itertuples():
        if row.is_clustered:
            c = "clustered"
        else:
            c = "non-clustered"

        if svclass_mapping[row.svclass] != "trans":
            channel = c + "_" + svclass_mapping[row.svclass] + "_" + row.size_bin
        else:
            channel = c + "_" + svclass_mapping[row.svclass]
        nmf_matrix.at[channel, row.sample] += 1
    nmf_matrix.reindex([features])
    nmf_matrix.index.name = "MutationType"

    return nmf_matrix
