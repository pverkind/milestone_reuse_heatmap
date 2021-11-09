"""Represent the frequency of text reuse of each token with a heatmap.

!!!!!!!!!!!!!!!!!!!!!!!!!!!

WORKS ONLY WITH PYTHON 3.8+

!!!!!!!!!!!!!!!!!!!!!!!!!!!

Steps needed:
1. download_srt_files(): download srt files related to one text
and put them in a folder with the full URI of the text as folder name
2. extract_milestone_data_from_file(): extract for each milestone
the text reuse data from all srt files
and save that data for each milestone in a separate json file
3. create the heatmap using those json files:
* ms_data_heatmap(): all text reuse in a single graph
* ms_data_heatmap_split(): 2 graphs: text reuse in texts
before and after `split_date`


Useful colormaps (often it is useful not to have colormaps that start with white):
* Reds
* autumn_r
* inferno_r

"""

import os

import re
import csv
from collections import defaultdict
import json
import requests
import gzip

import matplotlib.pyplot as plt
import matplotlib


def load_metadata(meta_fp="OpenITI_metadata_2021-1-4_merged.txt"):
    with open(meta_fp, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        meta = {row["id"]: {"status": row["status"],\
                            "date": int(row["date"])} for row in reader}
    return meta
            

##def visualize_ms_data(folder):
##    max_val = 0
##    fig, ax = plt.subplots()
##
##    for fn in os.listdir(folder):
##        if fn.endswith(".json"):
##            with open(os.path.join(folder, fn), mode="r", encoding="utf-8") as f:
##                ms_data = json.load(f)
##            ms = int(fn.split(".")[0])
##            if ms > max_val:
##                max_val = ms
##            for comp in ms_data.keys():
##                for comp_ms in ms_data[comp].keys():
##                    for comp_strt, d in ms_data[comp][comp_ms].items():
##                        y = [d["main_bw"], d["main_ew"]]
##                        x = [ms, ms]
##                        #print()
##                        ax.plot(x, y, c="black", linewidth=0.2, alpha=0.1)
##    plt.show()

def ms_data_heatmap(folder, cmap=plt.cm.inferno_r):
    """Visualize reuse of tokens in each milestone by a heat map. 

    Args:
        folder (str): path to folder containing the milestone files.
        cmap (Matplotlib color map): Matplot lib color map to be used
            for the heatmap: see
            https://matplotlib.org/stable/tutorials/colors/colormaps.html
    """
    
    max_val = 0
    ms_data = dict()

    for fn in os.listdir(folder):
        if fn.endswith(".json"):
            #print(fn)
            fp = os.path.join(folder, fn)
            with open(fp, mode="r", encoding="utf-8") as file:
                data = json.load(file)
            ms = int(fn.split(".")[0])
            if not ms in ms_data:
                ms_data[ms] = [0]*301
            for comp in data.keys():
                for comp_ms in data[comp].keys():
                    for comp_strt, d in data[comp][comp_ms].items():
                        for i in range(d["main_bw"], d["main_ew"]):
                            try:
                                ms_data[ms][i] += 1
                            except:
                                print(i)
                                print(ms_data[ms])
                                print(len(ms_data[ms]))
                                input()
                            if ms_data[ms][i] > max_val:
                                max_val = ms_data[ms][i]
    fig, ax = plt.subplots()
    #cm = plt.get_cmap('hot_r') # use the "hot" colour map, in reverse order
    print(max_val)

    
    for ms in ms_data:
        current_line_val = 0
        current_line_start = 0
        for i in range(len(ms_data[ms])):
            v = ms_data[ms][i]
            #print(v)
            if v == current_line_val:
                continue
            else:
                if current_line_val:
                    x = [ms, ms]
                    y = [current_line_start, i]
                    #print(current_line_val/max_val)
                    ax.plot(x, y, c=cmap(current_line_val/max_val),
                            linewidth=1)
                current_line_val = v
                current_line_start = i

    norm = matplotlib.colors.Normalize(vmin=1, vmax=max_val)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax)
    cbar.ax.set_title("reuse cases")
    ax.title.set_text("Text reuse heatmap of "+ folder)
    plt.show()

def calculate_token_reuse_freq(folder, split_date):
    print("Calculating reuse frequency of each reused token...")
    # create dictionaries containing for every token in reused milestones
    # the number of times it figures in an alignment:

    max_val = 0
    ms_data_pre = dict()
    ms_data_post = dict()

    for fn in os.listdir(folder):
        if fn.endswith(".json"):
            #print(fn)
            fp = os.path.join(folder, fn)
            with open(fp, mode="r", encoding="utf-8") as file:
                data = json.load(file)
            ms = int(fn.split(".")[0])
            if not ms in ms_data_pre:
                ms_data_pre[ms] = [0]*301
                ms_data_post[ms] = [0]*301
            for comp in data.keys():
                comp_id = comp.split("-")[0]
                if int(meta[comp_id]["date"]) < int(split_date):
                    ms_data = ms_data_pre
                else:
                    ms_data = ms_data_post
                for comp_ms in data[comp].keys():
                    for comp_strt, d in data[comp][comp_ms].items():
                        for i in range(d["main_bw"], d["main_ew"]):
                            try:
                                ms_data[ms][i] += 1
                            except:
                                print(i)
                                print(ms_data[ms])
                                print(len(ms_data[ms]))
                                input()
                            if ms_data[ms][i] > max_val:
                                max_val = ms_data[ms][i]
    return max_val, ms_data_pre, ms_data_post

def create_plot_lines(ms_data_pre, ms_data_post, max_val, pre_fp, post_fp):
    print("Calculating location and color for each line in heatmap...")

    pre = []
    post = []

    for i in range(2):
        ms_data = (ms_data_pre, ms_data_post)[i]
        json_list = (pre, post)[i]
        outfp = (pre_fp, post_fp)[i]
        for ms in ms_data:
            current_line_val = 0
            current_line_start = 0
            for i in range(len(ms_data[ms])):
                v = ms_data[ms][i]
                #print(v)
                if v == current_line_val:
                    continue
                else:
                    if current_line_val:
                        x = [ms, ms]
                        y = [current_line_start, i]
                        #print(current_line_val/max_val)
##                        ax.plot(x, y, c=cmap(current_line_val/max_val),
##                                linewidth=1)
                        json_list.append([x, y, current_line_val/max_val])
                    current_line_val = v
                    current_line_start = i
        with open(outfp, mode="w", encoding="utf-8") as file:
            d = {"lines": json_list, "max_val": max_val}
            json.dump(d, file, ensure_ascii=False, indent=2)
    return pre, post

def ms_data_heatmap_split(folder, split_date=None,
                          cmap=plt.cm.autumn_r):
    """Visualize reuse data on two levels: before and after split_date.
    The number of times reuse has been detected for a token is
    represented by a heat map. 

    Args:
        folder (str): path to folder containing the milestone files.
            Ideally, the folder has the URI of the text as name.
        split_date (int): date by which the reuse data has to be split;
            reuse from texts by authors who died before `split_date`
            will be visualized in the top graph, others in the bottom graph.
        cmap (Matplotlib color map): Matplot lib color map to be used
            for the heatmap: see
            https://matplotlib.org/stable/tutorials/colors/colormaps.html
    """
    if not split_date:
        split_date = int(os.path.split(folder)[-1][:4])


    # check if data has already been calculated:
    pre_fp = os.path.join(folder, "pre_{}.plotjson".format(split_date))
    post_fp = os.path.join(folder, "post_{}.plotjson".format(split_date))
    if os.path.exists(pre_fp) and os.path.exists(post_fp):
        print("loading data from json files")
        with open(pre_fp, mode="r", encoding="utf-8") as file:
            pre_data = json.load(file)
            max_val = pre_data["max_val"]
            pre = pre_data["lines"]
        with open(post_fp, mode="r", encoding="utf-8") as file:
            post_data = json.load(file)
            max_val = post_data["max_val"]
            post = post_data["lines"]        
    else:
        print("calculating...")
        max_val, ms_data_pre, ms_data_post = calculate_token_reuse_freq(folder, split_date)
        pre, post = create_plot_lines(ms_data_pre, ms_data_post, max_val, pre_fp, post_fp)
    
    print("max_val:", max_val)

    # plot:
    print("Plotting {} lines...".format(len(pre)+len(post)))
    fig, (ax1, ax2) = plt.subplots(2, 1)
    for i in range(2):
        ms_data = (pre, post)[i]
        ax = (ax1, ax2)[i]
        for x, y, c in ms_data:
            ax.plot(x, y, c=cmap(c), linewidth=1)
    
    # add color bar legend:
    norm = matplotlib.colors.Normalize(vmin=1, vmax=max_val)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=[ax1, ax2])
    cbar.ax.set_title("reuse cases")

    # set both X axis to the last reused milestone:
    max_ms = max([x[0][0] for x in pre+post])
    print("last milestone:", max_ms)
    ax1.set_xlim([0, max_ms+10])
    ax2.set_xlim([0, max_ms+10])

    # add titles:
    fig.suptitle(os.path.split(folder)[-1])
    ax1.title.set_text("Reuse of texts by authors who died before {}".format(split_date))
    ax1.set_xticks([])
    ax2.title.set_text("Reuse in texts by authors who died after {}".format(split_date))

    # display plot:
    #plt.tight_layout() # does not work with cbar!
    plt.show()

def extract_milestone_data_from_file(file, ms_data, main, comp,
                                     main_col, comp_col):
    """"Extract start and end of each reused milestone

    Args:
        file (file object)
        ms_data (defaultdict): contains for each milestone in the `main` text
            a dictionary of other texts in which this milestone is reused:
            ms_data[main_ms][comp][comp_ms][comp_bw] = {"comp_bw":, "comp_ew":, "comp_s":,
                                                        "main_bw":, "main_ew":, "main_s":
                                                        }
        main (str): id of the main book (derived from the srt file name).
        comp (str): id of the compared book (derived from the srt file name).
        main_col (str): is the main book bk1 or bk2 in the srt file? "1" or "2".
        comp_col (str): is the compared book bk1 or bk2 in the srt file? "1" or "2". 
    """
    for row in csv.DictReader(file, delimiter="\t"):
        main_ms = int(re.findall(r"\d+$", row["id"+main_col])[0])
        main_bw = int(row["bw"+main_col])
        main_ew = int(row["ew"+main_col])
        main_s = row["s"+main_col]
        comp_ms = int(re.findall(r"\d+$", row["id"+comp_col])[0])
        comp_bw = int(row["bw"+comp_col])
        comp_ew = int(row["ew"+comp_col])
        comp_s = row["s"+comp_col]
        if not comp in ms_data[main_ms]:
            ms_data[main_ms][comp] = defaultdict(dict)
        if not comp_ms in ms_data[main_ms][comp]: 
            ms_data[main_ms][comp][comp_ms] = defaultdict(dict)
        ms_data[main_ms][comp][comp_ms][comp_bw]["comp_bw"] = comp_bw
        ms_data[main_ms][comp][comp_ms][comp_bw]["comp_ew"] = comp_ew
        #ms_data[main_ms][comp][comp_ms][comp_bw]["comp_id"] = comp
        ms_data[main_ms][comp][comp_ms][comp_bw]["comp_s"] = comp_s
        ms_data[main_ms][comp][comp_ms][comp_bw]["main_bw"] = main_bw
        ms_data[main_ms][comp][comp_ms][comp_bw]["main_ew"] = main_ew
        #ms_data[main_ms][comp][comp_ms][comp_bw]["main_id"] = main
        ms_data[main_ms][comp][comp_ms][comp_bw]["main_s"] = main_s    

def extract_milestone_data_from_folder(folder):
    """Extract for every milestone in the mail text all corresponding
    milestones from all csv files in `folder` and save them as json files
    (one json file per milestone)
    """
    count = defaultdict(int)
    for fn in os.listdir(folder):
        if not fn.endswith("json"):
            bk1, bk2 = ".".join(fn.split(".")[:-1]).split("_")
            count[bk1] += 1
            count[bk2] += 1
    main = sorted(count.items(), key=lambda item: item[1], reverse=True)[0][0]

    ms_data = defaultdict(dict)
    for fn in os.listdir(folder):
        if not fn.endswith("json"):
            print(fn)
            fp = os.path.join(folder, fn)
            bk1, bk2 = ".".join(fn.split(".")[:-1]).split("_")
            if bk1 == main:
                comp = bk2
                main_col = "1"
                comp_col = "2"
            else:
                comp = bk1
                main_col = "2"
                comp_col = "1"
                
            if not fp.endswith("gz"):
                with open(fp, mode="r", encoding="utf-8") as file:
                    extract_milestone_data_from_file(file, ms_data, main, comp,
                                                     main_col, comp_col)
            else:
                with gzip.open(fp, mode="rt", encoding="utf-8") as file:
                    extract_milestone_data_from_file(file, ms_data, main, comp,
                                                     main_col, comp_col)
                
            #print(json.dumps(ms_data, ensure_ascii=False, indent=2, sort_keys=True))
    for ms in ms_data:
        outfp = os.path.join(folder, "{}.json".format(ms))
        with open(outfp, mode="w", encoding="utf-8") as file:
            json.dump(ms_data[ms], file, ensure_ascii=False, sort_keys=True, indent=2)

def download_file(url, filepath):
    """
    Write the download to file in chunks,
    so that the download does not fill up the memory.
    See http://stackoverflow.com/a/16696317/4045481
    """
    r = requests.get(url, stream=True)
    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

def download_srt_files(base_url, main_text_id, outfolder, incl_sec=False):
    print("Downloading srt files to", outfolder)
    if not os.path.exists(outfolder):
        os.mkdir(outfolder)
    if not base_url.endswith("/"):
        base_url += "/"
    base_url += main_text_id + "/"
    r = requests.get(base_url)
    links = re.findall('<a href="([^"]{10,})"', r.text)
    print(len(links), "LINKS DOWNLOAD STARTED")
    for link in links:
        print(link)
        outfp = os.path.join(outfolder, link)
        if not os.path.exists(outfp):
            if incl_sec:
                print("    downloading (pri and sec)")
                download_file(base_url+link, outfp)
            else:
                text_ids = re.sub("(?:\.csv|\.txt|\.gz)*$", "", link)
                text_ids = text_ids.split("_")
                for t in text_ids:
                    if main_text_id not in t:
                        sec_text_id = t.split("-")[0]
                print(sec_text_id)
                if sec_text_id in meta:
                    if meta[sec_text_id]["status"] == "pri":
                        print("    downloading")
                        download_file(base_url+link, outfp)
                    else:
                        print("    excluding from download: not a primary file")
                else:
                    print(sec_text_id, "not in metadata. Aborting download")
        else:
            print("    already in folder")

meta = load_metadata()

##base_url = "http://dev.kitab-project.org/passim01022019/Shamela0011484-ara1/"
##outfolder = "MarasidIttilac"
##download_srt_files(base_url, outfolder)
##
##input("Continue?")
##
##folder = "IbnHawqal"
##folder = outfolder
##extract_milestone_data_from_folder(folder)

##urls = {
####    "Muqaddasi": "MSG20191024-ara1.mARkdown",
####    "IbnHawqal": "Shamela0011780-ara1.completed",
####    "Istakhri": "Shamela0011680-ara1.mARkdown",
####    "YaqutBuldan": "Shamela0023735-ara1.completed",
####    "YaqutUdaba": "Shamela0009788-ara1.completed",
####    "Yacqubi": "Shamela0010808-ara1.completed",
####    "IbnKhurradadhbih": "Shamela0011800-ara1.completed",
##    "Zamakhshari": "Shamela0007287-ara1",
##    "Idrisi": "Shamela0011787-ara1"
##}
##
##
##base_url = "http://dev.kitab-project.org/passim01022021/"
##for folder, text_id in urls.items():
##    download_srt_files(base_url, text_id, folder)
##    extract_milestone_data_from_folder(folder)

#ms_data_heatmap("IbnHawqal")

base_url = "http://dev.kitab-project.org/passim01022021/"
text_id = "Shamela0009783BK1-ara1.completed"
folder = r"D:\London\publications\co-authored vol\geographers_srts_2019\0310Tabari.Tarikh"
#download_srt_files(base_url, text_id, folder)
#ms_data_heatmap(folder)
extract_milestone_data_from_folder(folder)
ms_data_heatmap_split(folder, cmap=plt.cm.inferno_r)
