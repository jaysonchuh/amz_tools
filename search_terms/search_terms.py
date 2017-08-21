# -*- coding: utf-8 -*-

import sys
import argparse
import setting
import collections

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

def deselect_checkbox(driver, id):
    """deselect a checkbox"""
    checkbox = driver.find_element_by_name(id)
    if checkbox.is_selected():
        checkbox.click()

def select_checkbox(driver, id):
    """select a checkbox"""
    checkbox = driver.find_element_by_name(id)
    if not checkbox.is_selected():
        checkbox.click()

def input_text_and_press_enter(driver, id, value):
    """input text and press enter key"""
    element  = driver.find_element_by_id(id)
    element.clear()
    element.send_keys(value)
    element.send_keys(Keys.RETURN)

def select_pull_down_list(driver, id, value):
    """select from pull down list"""
    select = Select(driver.find_element_by_id(id))
    select.select_by_value(value)

def parse_arguments():
    """parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--more_words", metavar="more_words",
            help="Extra words to be processed")
    parser.add_argument("--delay", metavar="delay", type=int, default=10,
            help="A time period to wait for the search results")

    parser.add_argument("keyword", metavar="keyword",
            help='A keyword to be searched')
    return parser.parse_args()

def get_keyword_from_seochat_com(args):
    """Get the trailing keywords of a search term"""
    driver = webdriver.PhantomJS()

    # load the landing page
    seochat_com = "http://tools.seochat.com/tools/suggest-tool/"
    driver.get(seochat_com)

    # trailing keywords on Amazon
    select_checkbox(driver, "amazon_checkbox")

    deselect_checkbox(driver, "bing_checkbox")
    deselect_checkbox(driver, "google_checkbox")
    deselect_checkbox(driver, "youtube_checkbox")

    input_text_and_press_enter(driver, "search_value", args.keyword)

    # wait for loading
    try:
        WebDriverWait(driver, args.delay).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, 'cb_result')))

    except TimeoutException:
        driver.close()
        sys.exit("Loading took too much time.")

    # find all the long tailed keywords
    elements = driver.find_elements_by_css_selector(
            ".checkbox.results-check")

    keywords = [element.text for element in elements]
    driver.close()
    return keywords


if __name__ == "__main__":
    args = parse_arguments()

    keywords = []

    if args.more_words is not None:
        more_words = args.more_words.split()
        keywords.extend(map(lambda s: s.decode('utf-8'), more_words))

    # list of unicode string
    keywords.extend(get_keyword_from_seochat_com(args))

    keywords = map(unicode.lower, keywords)
    # list of strings
    list_of_string = []
    for keyword in keywords:
        list_of_string.extend(keyword.split())
     
    # get sorted unique words
    counter = collections.Counter(list_of_string)
    for word in sorted(counter.keys()):
        print word
