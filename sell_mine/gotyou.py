# -*- coding: utf-8 -*-

import re
import sys
import time
import schedule
import logging
import ConfigParser
import argparse
import smtplib
import json
import cPickle as pickle
import traceback
import StringIO
import setting

from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException


last_invalid_seller = {}

class Sender(object):
    """Email sender"""
    def __init__(self, sender_email_address, sender_smtp_server, sender_smtp_password, timeout=30):
        self.sender_email_address  = sender_email_address
        self.sender_smtp_server = sender_smtp_server
        self.sender_smtp_password = sender_smtp_password
        self.timeout = timeout

    def send_email(self, recipients, subject, content, content_type='html'):
        """Send a email"""
        try:

            fp = StringIO.StringIO(content)
            msg = MIMEText(fp.read(), content_type)
            fp.close()

            msg['Subject'] = subject
            msg['From'] = self.sender_email_address
            msg['To'] = ", ".join(recipients)

            logging.getLogger().debug('sender = {0}'.format(self.sender_email_address))
            logging.getLogger().debug('recipients = {0}'.format(recipients))
            # Send the message via our own SMTP server, but don't include the envelope header.
            server = smtplib.SMTP(self.sender_smtp_server, timeout=self.timeout)
            server.starttls()
            server.login(self.sender_email_address, self.sender_smtp_password)
            server.sendmail(self.sender_email_address, recipients, msg.as_string())
            server.quit()
        except:
            logging.getLogger().exception("Exception get caught.")


def check_for_asshole_seller(args, config ):
    """Check for asshole seller"""
    try:
        sender_email_address = config.get('email_setting', 'sender_email_address')
        sender_smtp_server = config.get('email_setting', 'sender_smtp_server')
        sender_smtp_password = config.get('email_setting', 'sender_smtp_password')
        recipients_email_address = json.loads(config.get('email_setting', 'recipients_email_address'))
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    sender = Sender(sender_email_address, sender_smtp_server, sender_smtp_password)

    email_subject = 'Mother Fcuker Found!'
    content_template = """
    <style media="screen" type="text/css"><!--
    p {{ margin: 0 0 1.6em 0; }}
    --></style>
    <div id="wrapper" style="color: #000000; font-family: Arial,Helvetica,sans-serif; font-size: 14px; line-height: 18px;">
    <p>Product Name: {product_name}<br />
    <p>Product Page: <a href="{product_page}">Page Link</a><br />
    <p>Seller Name: {asshole_name}<br />
    </div>
    """

    logging.getLogger().info("---------- Start working ----------")

    with open(args.product_file) as product_file:
        for record in product_file:
            try:
                authentic_seller, product_name, product_page = record.strip().split(args.seperator)
                logging.getLogger().info("Product_Page: {0}".format(product_page))

                # load the landing page
                driver = webdriver.PhantomJS()
                driver.get(product_page)

                # wait for loading
                try:
                    WebDriverWait(driver, args.delay).until(
                            EC.presence_of_all_elements_located(
                                (By.ID, 'merchant-info')))
                except TimeoutException:
                    driver.close()
                    sys.exit("Loading took too much time.")

                element = driver.find_element_by_id("merchant-info")

                match = re.match(r'.*[sS]old by (?P<seller_name>[^ .]*).*', element.text)

                if match:
                    seller_name = match.group('seller_name')
                    last_seller = last_invalid_seller.get(product_page, '')
                    if seller_name != authentic_seller and seller_name != last_seller:
                        driver.save_screenshot('./{0}_{1}.png'.format(seller_name, int(time.time())))
                        email_content = content_template.format(product_name=product_name, product_page=product_page,
                                asshole_name=seller_name)
                        sender.send_email(recipients_email_address, email_subject, email_content)
                        last_invalid_seller[product_page] = seller_name

                logging.getLogger().info("Done: Product_Name = {0}, Product_Page= {1}".format(product_name,
                    product_page))
            except:
                logging.getLogger().exception("Product_Name = {0}, Product_Page= {1}".format(product_name,
                    product_page))
            finally:
                driver.close()

            time.sleep(args.delay)


if __name__ == "__main__":
    setting.basic_logging_config()

    # parse the command-line options
    parser = argparse.ArgumentParser(description='Check for the asshole seller')
    parser.add_argument('-s', '--seperator', default=',')
    parser.add_argument('-i', '--interval', type=float, default=10)
    parser.add_argument('-d', '--delay', type=float, default=10)
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('product_file', metavar='PRODUCT_FILE')
    args = parser.parse_args()

    # load the configuration file
    config = ConfigParser.ConfigParser()
    if not config.read(args.config_file):
        logging.getLogger().error('Configuration file is missing')
        sys.exit(1)

    check_for_asshole_seller(args, config)
    
    # run the task every X minutes
    schedule.every(args.interval).minutes.do(check_for_asshole_seller, args, config)
    while True:
        schedule.run_pending()
        time.sleep(args.delay)
