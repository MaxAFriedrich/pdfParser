#! /bin/python3
"""
Author: Max Friedrich

This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
"""
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

from re import sub, MULTILINE

from difflib import SequenceMatcher

from numpy import percentile, sort
from math import log


from threading import Thread
from queue import Queue


from argparse import ArgumentParser

from os import path

NO_HEADER_LINES = 5
NO_FOOTER_LINES = 4
WINDOW_SIZE = 8
PERCENTILE_TARGET = 75


def similar(a: str, b: str) -> float:
    """compares to strings and returns a float between 0 and 1 expressing the similarity between the two

    Args:
        a (str): first string
        b (str): second string

    Returns:
        float: value from 0 to 1 where 0 is completely different and 1 is identical
    """
    return SequenceMatcher(None, a, b).ratio()


def parse_file(file_name: str,first:int,last:int) -> list:
    """takes a pdf file path and converts it to a list of pages that can then be parsed

    Args:
        file_name (str): name of input file

    Raises:
        Exception: Exception if the file has no pages.

    Returns:
        list: list of pages
    """
    parsed_text = []
    i=1
    for page_layout in extract_pages(file_name):
        if i<first:
            i+=1
            continue
        elif i>last and last !=0:
            break
        else:
            i+=1

        page = {
            "text": [],
            "height": page_layout.height,
            "width": page_layout.width,
        }
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text = element.get_text()
                elm = {
                    "text": text,
                    "all_scores": [],
                    "score": 0,
                    "compared": [],
                    "x0": element.x0,
                    "y0": element.y0,
                    "x1": element.x1,
                    "y1": element.y1,
                    "removed": False,
                }
                page["text"].append(elm)

        parsed_text.append(page)
    if len(parsed_text) < 1:
        raise Exception("File has no pages.")
    return parsed_text


def scale(value: float, maxVal: float = 501) -> float:
    """compresses a value to a number between 0 and 1 on a log scale

    Args:
        value (float): value to scale
        maxVal (float, optional): The maximum number that is expected as a value. Defaults to 501.

    Returns:
        float: The scaled log value.
    """
    return abs(log(abs(value) + 1) / log(maxVal))


def score_lines(parsed_text: list, page: int, new_page: int, target_hf: str) -> list:
    """goes through each header or footer line in a page and compares them to the header or footer lines in another page

    Args:
        parsed_text (list): all of the document's text
        page (int): index of the page being scored
        new_page (int): index of the page that is being compared
        target_hf (str): whether to score the footer or header

    Raises:
        Exception: if the header or footer is invalid text

    Returns:
        list: the parsed_text with scores
    """

    len_cur_page = len(parsed_text[page]["text"])
    len_new_page = len(parsed_text[new_page]["text"])

    if target_hf == "header":
        no_lines = min(NO_HEADER_LINES, len_cur_page, len_new_page)
        start_cur_line = 0
        end_cur_line = no_lines
        start_new_line = 0
        end_new_line = no_lines
    elif target_hf == "footer":
        no_lines = min(NO_FOOTER_LINES, len_cur_page, len_new_page)
        start_cur_line = len_cur_page - no_lines
        end_cur_line = len_cur_page
        start_new_line = len_new_page - no_lines
        end_new_line = len_new_page
    else:
        raise Exception("Not a valid target_hf.")

    for cur_line in range(start_cur_line, end_cur_line, 1):
        for new_line in range(start_new_line, end_new_line, 1):
            total = []
            c_l = parsed_text[page]["text"][cur_line]
            n_l = parsed_text[new_page]["text"][new_line]
            if [page, cur_line] in n_l["compared"]:
                continue
            parsed_text[new_page]["text"][new_line]["compared"].append([page, cur_line])
            # pos
            total_size = max(
                (parsed_text[page]["width"] * 2), (parsed_text[new_page]["width"] * 2)
            ) + max(
                (parsed_text[page]["height"] * 2), (parsed_text[new_page]["height"] * 2)
            )
            total.append(
                1
                - scale(
                    (n_l["x0"] + n_l["x1"] + n_l["y0"] + n_l["y1"])
                    - (c_l["x0"] + c_l["x1"] + c_l["y0"] + c_l["y1"]),
                    total_size,
                )
            )
            # text similarity
            total.append(
                similar(
                    sub(r"\d", "@", c_l["text"], 0, MULTILINE),
                    sub(r"\d", "@", n_l["text"], 0, MULTILINE),
                )
            )
            # text length
            len_c_l = len(c_l["text"])
            len_n_l = len(n_l["text"])
            total.append(1 - scale(len_c_l - len_n_l, max(len_c_l + 10, len_n_l + 10)))
            parsed_text[page]["text"][cur_line]["all_scores"].append(
                percentile(total, PERCENTILE_TARGET)
            )
    return parsed_text


def remove_lines(parsed_text: list, page: int, target_hf: str,threshold:float) -> list:
    """removes lines with a high score/probability iof being a header or footer line

    Args:
        parsed_text (list): the text of the document with scores
        page (int): the index of the page to remove the lines from
        target_hf (str): whether to remove header or footer lines

    Raises:
        Exception: invalid header or footer

    Returns:
        list: the text with the removed lines
    """
    len_cur_page = len(parsed_text[page]["text"])

    if target_hf == "header":
        no_lines = min(NO_HEADER_LINES, len_cur_page)
        start_cur_line = 0
        end_cur_line = no_lines
    elif target_hf == "footer":
        no_lines = min(NO_FOOTER_LINES, len_cur_page)
        start_cur_line = len_cur_page - no_lines
        end_cur_line = len_cur_page
    else:
        raise Exception("Not a valid target_hf.")

    for line in range(start_cur_line, end_cur_line, 1):
        line_scores = parsed_text[page]["text"][line]["all_scores"]
        if len(line_scores) == 0:
            continue
        parsed_text[page]["text"][line]["score"] = max(
            percentile(line_scores, PERCENTILE_TARGET), max(sort(line_scores)[-3:])
        )
        if parsed_text[page]["text"][line]["score"] > threshold:
            parsed_text[page]["text"][line]["removed"] = True
    return parsed_text


def do_page(parsed_text: list, page: int, result_queue: Queue,threshold:float):
    """process a page

    Args:
        parsed_text (list): the document text
        page (int): the index of the page
        result_queue (Queue): queue to which the result is returned
    """
    lower_bound = max(page - WINDOW_SIZE, 0)
    upper_bound = min(page + WINDOW_SIZE, len(parsed_text))
    for new_page in range(lower_bound, upper_bound, 1):
        if new_page == page:
            continue
        parsed_text = score_lines(parsed_text, page, new_page, "header")
        parsed_text = score_lines(parsed_text, page, new_page, "footer")
    parsed_text = remove_lines(parsed_text, page, "header",threshold)
    parsed_text = remove_lines(parsed_text, page, "footer",threshold)
    result_queue.put([parsed_text[page], page])


def find_hf(parsed_text: list,threshold:float) -> list:
    """parses the document and finds all of the headers and footers

    Args:
        parsed_text (list): the text to be parsed

    Returns:
        list: the text that has been parsed
    """
    result_queue = Queue()
    threads = []
    for page in range(len(parsed_text)):
        t = Thread(target=do_page, args=(parsed_text, page, result_queue,threshold))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    while not result_queue.empty():
        data = result_queue.get(block=True, timeout=None)
        parsed_text[data[1]] = data[0]
    return parsed_text


def clean_text(text: str) -> str:
    """runs regular expressions on a string to remove junk

    Args:
        text (str): a plain text string to be cleaned

    Returns:
        str: the cleaned text
    """
    text = sub(r"\t", " ", text, 0, MULTILINE)
    text = sub(r" {2,}", " ", text, 0, MULTILINE)
    return text


def clean_file(file_name: str,debug:bool,first:int, last:int,threshold:float):
    """takes a file as input and then parses and cleans the file

    Args:
        file_name (str): name of the file to be cleaned
    """
    parsed_text = parse_file(file_name,first,last)
    parsed_text = find_hf(parsed_text,threshold)
    if debug:
        print(parsed_text)
    out_text = "".join(
        [
            "".join(
                [
                    text["text"].replace("\n", " ") + "\n"
                    for text in page["text"]
                    if not text["removed"]
                ]
            )
            for page in parsed_text
        ]
    )
    out_text = clean_text(out_text)
    base_name, _ = path.splitext(file_name)
    with open(base_name + ".txt", "w") as file:
        file.write(out_text)


if __name__ == "__main__":
    parser = ArgumentParser(prog='pdfParser', description='Convert a PDF to a plain text document with improved formatting and without headers or footers.')
    parser.add_argument("filenames", nargs="+", help="A list of filenames to be processed. The completed files are saved with the same name and a .txt extension.")
    parser.add_argument("-d","--debug",default=False,help="Returns a python dictionary to stdout.",action="store_true")
    parser.add_argument("-f","--first_page",default=1,help="First page to parse.",type=int)
    parser.add_argument("-l","--last_page",default=0,help="Last page to parse.", type=int)
    parser.add_argument("-t","--removal_threshold",default=0.8,help="The threshold for text removal.",type=float)
    args = parser.parse_args()
    filenames = args.filenames
    for file_name in filenames:
        t = Thread(target=clean_file, args=(file_name,args.debug,args.first_page,args.last_page,args.removal_threshold))
        t.start()
