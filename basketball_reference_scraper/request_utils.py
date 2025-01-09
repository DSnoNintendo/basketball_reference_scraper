import os
from os import getenv
from time import sleep, time

from proxy_cycling_webdriver.chrome import WebDriver
from requests import get
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def build_proxy_list():
    proxies = os.getenv("PROXY_URLS", None)
    if proxies is None:
        return ValueError("'PROXY_URLS' environment variable must be set")
    return proxies.split(",")


options = Options()
options.add_argument("--headless=new")
driver = WebDriver(
    options=options,
    proxies=build_proxy_list(),  # TODO: allow no proxies
)
last_request = time()


def get_selenium_wrapper(url, xpath):
    # Verify last request was 3 seconds ago
    driver.cycle_proxies()  # TODO: allow no proxies
    while True:
        try:
            sleep(3)
            print("current proxy", driver.current_proxy)
            driver.get(url)
            element = driver.find_element(By.XPATH, xpath)
            return f'<table>{element.get_attribute("innerHTML")}</table>'
        except Exception as e:
            if len(driver.proxies) > 1:
                print(f"Failed to get {url}. Cycling proxy")
                driver.cycle_proxies()
            else:
                print(e)
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
