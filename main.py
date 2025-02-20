import logging
import sys
import traceback
import time
import os
import subprocess

from DrissionPage import ChromiumPage, ChromiumOptions
from src.utils import CONFIG, sendNotification, getProjectRoot
from src.CloudflareBypasser import CloudflareBypasser

# Importing Proxy Bypass Functions
from proxy_bypass import UserAgentTester

def setupLogging():
    _format = CONFIG['logging']['format']
    _level = CONFIG['logging']['level']
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(logging.Formatter(_format))

    logs_directory = getProjectRoot() / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)

    fileHandler = logging.FileHandler(logs_directory / "activity.log", encoding="utf-8")
    fileHandler.setFormatter(logging.Formatter(_format))
    fileHandler.setLevel(logging.getLevelName(_level.upper()))

    logging.basicConfig(
        level=logging.getLevelName(_level.upper()),
        format=_format,
        handlers=[
            terminalHandler,
            fileHandler,
        ],
    )

def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    options = ChromiumOptions().auto_port()
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def bypass_cloudflare(driver):
    logging.info('Starting Cloudflare bypass.')
    cf_bypasser = CloudflareBypasser(driver)
    cf_bypasser.bypass()
    logging.info("Cloudflare bypass completed.")

def open_url_in_chrome(driver, url, duration):
    logging.info('Opening the URL in Chrome...')
    driver.get(url)
    # Keep the browser open for the specified duration
    logging.info(f'Keeping the browser open for {duration} seconds.')
    time.sleep(duration * 60)  # Convert minutes to seconds
    # You can add more interactions here if needed

def bypass_proxy(proxy_details):
    tester = UserAgentTester("user_agents.json")  # Ensure the user agents file is in the same directory
    successful_user_agent = None

    # Test user agents to bypass proxy
    for user_agent in tester.user_agents:
        if tester.test_user_agent(proxy_details, user_agent):
            successful_user_agent = user_agent
            break

    if successful_user_agent:
        logging.info(f'Successfully bypassed proxy with user agent: {successful_user_agent["user-agent"]}')
        return successful_user_agent["user-agent"]
    else:
        logging.warning('Failed to bypass proxy with any user agent.')
        return None

def main():
    setupLogging()

    url = CONFIG['url']
    duration = CONFIG['duration']
    proxy_details = CONFIG['browser']['proxy']  # Get the proxy details from config

    try:
        browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")
        arguments = [
            "-no-first-run",
            "-force-color-profile=srgb",
            "-metrics-recording-only",
            "-password-store=basic",
            "-use-mock-keychain",
            "-export-tagged-pdf",
            "-no-default-browser-check",
            "-disable-background-mode",
            "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
            "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
            "-deny-permission-prompts",
            "-disable-gpu",
            "-accept-lang=en-US",
        ]

        # Bypass Proxy
        if proxy_details:
            successful_user_agent = bypass_proxy(proxy_details)
            if successful_user_agent:
                arguments.append(f"--user-agent={successful_user_agent}")

        options = get_chromium_options(browser_path, arguments)

        # Initialize the browser and bypass Cloudflare
        driver = ChromiumPage(addr_or_opts=options)
        logging.info("Bypassing Cloudflare for the URL...")
        driver.get(url)
        bypass_cloudflare(driver)
        
        # Continue using the same browser instance to open the URL
        logging.info("Cloudflare bypass successful. Opening the URL in Chrome...")
        open_url_in_chrome(driver, url, duration)
        
    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)
    finally:
        logging.info('Closing the browser.')
        driver.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)
        exit(1)
