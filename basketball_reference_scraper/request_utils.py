import os
from os import getenv
from time import sleep, time

from proxy_cycling_webdriver.chrome import WebDriver
from requests import get
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from basketball_reference_scraper.utils import build_proxy_list

options = Options()
options.add_argument("--headless=new")
driver = WebDriver(
    options=options,
    proxies=build_proxy_list(),  # TODO: allow no proxies
)
last_request = time()


def get_selenium_wrapper(url, xpath):
    global last_request
    # Verify last request was 3 seconds ago
    try:
        driver.cycle_proxies() # TODO: allow no proxies
        driver.get(url)
        element = driver.find_element(By.XPATH, xpath)
        return f'<table>{element.get_attribute("innerHTML")}</table>'
    except:
        print("Error obtaining data table.")
        return None


def get_wrapper(url):
    global last_request
    # Verify last request was 3 seconds ago
    if 0 < time() - last_request < 3:
        sleep(3)
    last_request = time()
    r = get(url)
    while True:
        if r.status_code == 200:
            return r
        elif r.status_code == 429:
            retry_time = int(r.headers["Retry-After"])
            print(f"Retrying after {retry_time} sec...")
            sleep(retry_time)
        else:
            return r
