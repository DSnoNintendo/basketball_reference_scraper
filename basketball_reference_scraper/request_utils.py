import os
from os import getenv
from time import sleep, time

from requests import get
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from seleniumwire import webdriver
from proxy_cycler import ProxyCycler


def build_proxy_list():
    proxies = os.getenv("PROXY_URLS", None)
    if proxies is None:
        return ValueError("'PROXY_URLS' environment variable must be set")
    return proxies.split(",")


options = Options()
options.add_argument("--headless=new")
selenium_proxy_cycler = ProxyCycler(build_proxy_list())
requests_proxy_cycler = ProxyCycler(build_proxy_list())
driver = webdriver.Chrome(options=options)
last_request = time()


def get_selenium_wrapper(url, xpath):
    # Verify last request was 3 seconds ago
    if len(driver.proxies):
        driver.cycle_proxies()
    while True:
        try:
            sleep(3)
            print("current proxy", driver.current_proxy)
            driver.get(url, seleniumwire_options={'proxy': selenium_proxy_cycler.cycle_proxies()})
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
    while True:
        r = get(url, proxies=requests_proxy_cycler.cycle_proxies())
        if r.status_code == 200:
            return r
        elif r.status_code == 429:
            print(f"Error code {r.status_code}. Cycling proxies")
        else:
            return r
