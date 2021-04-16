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

import time

from bokeh.plotting import figure, output_file, show, save, ColumnDataSource
from bokeh.palettes import inferno
from bokeh.layouts import column, grid
from bokeh.models import Div, Title, ColorBar, LinearColorMapper, HoverTool, WheelZoomTool
from bokeh.embed import file_html
from bokeh.events import DoubleTap
from bokeh.models.callbacks import CustomJS


from tqdm import tqdm


def load_metadata(meta_fp="OpenITI_metadata_2021-1-4_merged.txt"):
    with open(meta_fp, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        meta = {row["id"]: {"status": row["status"],\
                            "date": int(row["date"])} for row in reader}
    return meta
            

def calculate_token_reuse_freq(folder, date_ranges):
    """Calculate how often an token is reused in milestone json files
    in `folder` in specific date ranges"""
    print("Calculating reuse frequency of each reused token...")
    # create dictionaries containing for every token in reused milestones
    # the number of times it figures in an alignment:

    ms_count_dicts = [dict() for x in date_ranges]

    #for fn in tqdm(os.listdir(folder)):
    for fn in os.listdir(folder):
        if fn.endswith(".json"):
            # load json file with data about text reuse in the milestone:
            # main_ms.json = {comp_id: {comp_ms: {}}}
            fp = os.path.join(folder, fn)
            with open(fp, mode="r", encoding="utf-8") as file:
                data = json.load(file)
            ms = int(fn.split(".")[0])
            for comp in data.keys():
                comp_id = comp.split("-")[0]
                # select the time range dictionary in which to save the data:
                ms_count = None
                for x, r in enumerate(date_ranges):
                    if r[0] <= int(meta[comp_id]["date"]) < r[1]:
                        ms_count = ms_count_dicts[x]
                        break
                if ms_count == None:
                    continue  # not in any desired date range!
                else:
                    if not ms in ms_count:
                        ms_count[ms] = [0]*301
                    for comp_ms in data[comp].keys():
                        for comp_strt, d in data[comp][comp_ms].items():
                            for i in range(d["main_bw"], d["main_ew"]):
                                ms_count[ms][i] += 1
    return ms_count_dicts

def create_plot_lines(ms_count_dicts, outfps):
    """Create list with start and end coordinates + number of reuse cases
    of each line to be plotted.

    Args:
        ms_count_dicts (list): list of dictionaries
            (one for each relevant data range)
            containing for every milestone a list of 300 integers
            (one for each token in the milestone)
            that represents the number of times the token was
            repeated within the relevant date range
        outfps (list): list of file paths to which each list of lines
            should be saved
            (same number of paths as dictionaries in ms_count_dicts)

    Returns:
        list (list of dictionaries {"xs": [<x value tuples (start = end) for each line>],
                                    "ys": [<y value tuples (start, end) for each line>],
                                    "vals": [<number of times the tokens covered by this line are reused>]}
    """
    print("Calculating location and color for each line in heatmap...")

    #lines = [{"xs": [], "ys":[], "vals":[]} for i in range(len(ms_count_dicts))]
    lines = [[] for i in range(len(ms_count_dicts))]

    for i in range(len(ms_count_dicts)):
        ms_data = ms_count_dicts[i]
        #json_d = lines[i]
        json_list = lines[i]
        outfp = outfps[i]
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
                        #json_list.append([x, y, current_line_val/max_val])
##                        json_d["xs"].append(x)
##                        json_d["ys"].append(y)
##                        json_d["vals"].append(current_line_val)
                        json_list.append([x, y, current_line_val])
                    current_line_val = v
                    current_line_start = i
        with open(outfp, mode="w", encoding="utf-8") as file:
            #json.dump(json_d, file, ensure_ascii=False, indent=2)
            json.dump(json_list, file, ensure_ascii=False, indent=2)
    return lines


def plot_with_bokeh(date_ranges, split_data_lines, max_val, last_ms,
                    cmap, outfp=None):
    # create subplots:
    tools = "pan,wheel_zoom,box_zoom,reset,tap"
    title_fmt = "Reuse of texts by authors who died between {} and {} AH"
    axes = []
    for i ,dr in enumerate(date_ranges):
        ax = figure(plot_width=250, plot_height=250, tools=tools)
        ax.background_fill_color="grey"
        ax.background_fill_alpha=0.3
        title=title_fmt.format(*dr)
        ax.add_layout(Title(text=title, text_font_size="12pt"), "above")
        axes.append(ax)

    cmap = list(cmap(max_val)) # number of values in the color palette
    cmap.reverse()

    # plot lines:
    for i in range(len(date_ranges)):
        line_data = split_data_lines[i]
        ax = axes[i]
        vals = dict()
        #print("plotting values in subplot ", i+1)
        print("plotting values in subplot {}".format(i+1))
        for x, y, v in line_data:
            #ax.plot(x, y, c=cmap(v/max_val), linewidth=1) # this is too slow
            # group lines by reuse count, which speeds up plotting:
            if not v in vals:
                vals[v] = {"xs": [], "ys": [], "val": []}
            vals[v]["xs"].append(x)
            vals[v]["ys"].append(y)
            vals[v]["val"].append(v)
        for val in sorted(vals.keys()):
            #print(val)
            print("val", val, "color:", cmap[val-1])
            source = ColumnDataSource(data=vals[val])
            ml = ax.multi_line("xs", "ys", source=source,
                               color=cmap[val-1],
                               #line_width=1)
                               nonselection_line_width=1,
                               selection_line_width=3)

    # add color bar:
    color_mapper = LinearColorMapper(palette=cmap, low=0.5, high=max_val+0.5)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12)
    for ax in axes:
        ax.add_layout(color_bar, 'right')

    # set x range of all axes to last_ms:
    for ax in axes:
        ax.x_range.end = last_ms + 10
        ax.x_range.start = 0
        ax.y_range.start = 0
        ax.y_range.end = 300
        ax.sizing_mode = "stretch_width"

    # add title:        
    #title = "<h1>{}</h1>".format(os.path.split(folder)[-1])
    title = os.path.split(folder)[-1]
    axes[0].add_layout(Title(text=title, text_font_size="16pt"), "above")

    # add tooltips and double-click callback:        
    TOOLTIPS = [("reuse cases", "@val")]
    for ax in axes:
        ax.add_tools(HoverTool(tooltips=TOOLTIPS, line_policy="interp"))
        #ax.add_tools(WheelZoomTool())
        ax.toolbar.active_scroll = ax.select_one(WheelZoomTool)
        #ax.toolbar_location=None
##        callback = CustomJS(code="""
##var div = Document.getElementById("ms-info");
##var json_fn = cb_obj.x+".json"
##fetch(json_fn)
##  .then(response => response.json())
##  .then(data => div.innerHTML(data);
##div.setAttribute("style","display:block;");
##div.style.display="block";
##""")
##        ax.on_event(DoubleTap, callback)
##
##    div_text = """
##<div id="ms-info" style="display:hidden;">
##</div>
##"""
##    div = Div(text=div_text, sizing_mode="stretch_width")

    # save and show image:
    #c = column(*axes, sizing_mode="stretch_width")
    columns = [[ax] for ax in axes]
##    columns = [[div]] + columns
    c = grid(columns)
    if outfp:
        #output_file(title+".html")
        save(c, outfp)
    #show(column(Div(text=title), *axes, sizing_mode="stretch_both"))
    show(c)
    

    

def plot_with_matplotlib(date_ranges, split_data_lines, max_val, last_ms,
                         cmap, outfp=None):
    """Use matplotlib to create the """
    # create the different subplots (axes);
    fig, axes = plt.subplots(len(date_ranges), 1)
    if len(date_ranges) == 1:
        axes = [axes, ]

    # plot the lines:
    start = time.time()
    #for i in range(len(date_ranges)):
    pbar = tqdm(range(len(date_ranges)))
    for i in pbar:
        line_data = split_data_lines[i]
        ax = axes[i]
        vals = dict()
        #print("plotting values in subplot ", i+1)
        pbar.write("plotting values in subplot {}".format(i+1))
        for x, y, v in line_data:
            #ax.plot(x, y, c=cmap(v/max_val), linewidth=1) # this is too slow
            # group lines by reuse count, which speeds up plotting:
            if not v in vals:
                vals[v] = []
            vals[v]+=[x, y]
        for val in sorted(vals.keys()):
            #print(val)
            pbar.write(str(val))
            ax.plot(*vals[val], c=cmap(val/max_val), linewidth=1)
    print("plotting took", time.time()-start)
    # set all X axes to the last reused milestone:
    for ax in axes:
        ax.set_xlim([0, last_ms+10])
        ax.set_ylim([0, 300])

    # add titles:
    fig.suptitle(os.path.split(folder)[-1])
    for i, dr in enumerate(date_ranges):
        ax = axes[i]
        title = "Reuse of texts by authors who died between {} and {} AH"
        ax.title.set_text(title.format(*dr))
        if i < len(date_ranges)-1:
            ax.set_xticks([])

    # add color bar legend:
    norm = matplotlib.colors.Normalize(vmin=0, vmax=max_val)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=list(axes))
    cbar.ax.set_title("reuse cases")

    # display plot:
    #plt.tight_layout() # does not work with cbar!
    plt.get_current_fig_manager().window.state('zoomed') # fullscreen!
    if outfp:
        plt.savefig(outfp)
    plt.show()

def ms_data_heatmap(folder, date_ranges=[(0, 1501),],
                    cmap=plt.cm.autumn_r, plot_func=plot_with_matplotlib,
                    outfp=None):
    """Visualize the frequency of reuse of each token in a text
    by a heat map. 

    Args:
        folder (str): path to folder containing the milestone files.
            Ideally, the folder has the URI of the text as name.
        date_ranges (list): list of tuples (start_date (int), end_date (int))
            for each date range for which the reuse data should be
            visualized in a separate graph.
            NB: start date is inclusive, end date exclusive:
            with [(0, 300), (300, 1501)] 300 will be included in the second graph.
        cmap (Matplotlib color map): Matplot lib color map to be used
            for the heatmap: see
            https://matplotlib.org/stable/tutorials/colors/colormaps.html
        plot_func (function): function to be used to plot the data.
        outfp (str): graph will be saved to file if a path is provided.
            Default: None.
    """
    # check if data has already been calculated:
    split_data_lines = []
    split_fps = []
    for i, dr in enumerate(date_ranges):
        fp = os.path.join(folder, "lines_{}_{}.plotjson".format(*dr))
        split_fps.append(fp)
        if os.path.exists(fp):
            print("loading data for range", dr)
            with open(fp, mode="r", encoding="utf-8") as file:
                split_data_lines.append(json.load(file))
        else:
            print("Data for range", dr, "not yet calculated")
            split_data_lines.append([])

    # calculate missing date range data:
    no_data = [i for i in range(len(split_data_lines)) if split_data_lines[i] == []]
    if no_data:
        #filtered_ms_data = filter_srt_files(folder, [date_ranges[e] for e in no_data])
        ms_count_dicts = calculate_token_reuse_freq(folder, [date_ranges[e] for e in no_data])
        missing_lines = create_plot_lines(ms_count_dicts, [split_fps[e] for e in no_data])
        for i, e in enumerate(no_data):
            split_data_lines[e] = missing_lines[i]

    # calculate the maximum value and last milestone:
    max_val = 0
    last_ms = 0
    for lst in split_data_lines:
        for tup in lst:
            if tup[2] > max_val:
                max_val = tup[2]
            if tup[0][0] > last_ms:
                last_ms = tup[0][0]
    print("max_val:", max_val)
    print("last milestone:", last_ms)

    plot_func(date_ranges, split_data_lines, max_val, last_ms, cmap, outfp)

def split_dates_to_date_ranges(split_dates, start_date=0, end_date=1501):
    """Given a list of dates, create date ranges
    that start with start_date and end with end_date.

    Args:
        split_dates (list): a list of years (int) that should
            be used as delimiters of the date ranges in the graphs
        start_date (int): earliest date to be included in the graph
        end_date (int): latest date to be included in the graph

    Returns:
        list (of tuples: (start_of_range (int), end_of_range (int)))
    """
    date_ranges = []
    for i, sd in enumerate(split_dates):
        if i == 0:
            date_ranges.append((start_date, sd))
        else:
            date_ranges.append((split_dates[i-1], sd))
    if date_ranges[-1] != end_date:
        date_ranges.append((sd, end_date))
    return date_ranges
    

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


base_url = "http://dev.kitab-project.org/passim01022021/"
text_id = "Shamela0009788-ara1.mARkdown"
folder = r"D:\London\publications\co-authored vol\geographers_srts_2019\0310Tabari.Tarikh"
#download_srt_files(base_url, text_id, folder)
#extract_milestone_data_from_folder(folder)
split_dates = [310]
date_ranges = split_dates_to_date_ranges(split_dates)
folder_name = os.path.split(folder)[-1]
ms_data_heatmap(folder, date_ranges=date_ranges, cmap=inferno,
                outfp="output_images/{}_{}.html".format(folder_name, split_dates[0]),
                plot_func=plot_with_bokeh)


split_dates = [300, 500, 700, 900, 1100]
date_ranges = split_dates_to_date_ranges(split_dates)
parent = r"D:\London\publications\co-authored vol\geographers_srts_2019"
##for folder in os.listdir(parent):
##    if os.path.isdir(os.path.join(parent, folder)):
##        
##        split_dates = [int(folder[:4]),]
##        date_ranges = split_dates_to_date_ranges(split_dates)
##        ms_data_heatmap(os.path.join(parent, folder),
##                        date_ranges=date_ranges, cmap=plt.cm.inferno_r,
##                        outfp="output_images/{}_{}.png".format(folder, split_dates[0]))
