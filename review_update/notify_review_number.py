# -*- coding: utf-8 -*-

import re
import sys
import time
import schedule
import logging
import ConfigParser
import argparse
import smtplib
import requests
import json
import cPickle as pickle
import traceback
import StringIO
import setting

from email.mime.text import MIMEText
from bs4 import BeautifulSoup


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


def check_for_update(args, config):

    # load the asin_to_review_number pickle file
    try:
        with open(args.pickle_file, 'rb') as pkl_file:
            asin_to_review_number = pickle.load(pkl_file)
    except:
        asin_to_review_number = {}
    
    try:
        sender_email_address = config.get('email_setting', 'sender_email_address')
        sender_smtp_server = config.get('email_setting', 'sender_smtp_server')
        sender_smtp_password = config.get('email_setting', 'sender_smtp_password')
        recipients_email_address = json.loads(config.get('email_setting', 'recipients_email_address'))
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    sender = Sender(sender_email_address, sender_smtp_server, sender_smtp_password)

    email_subject = 'Update on review number!'
    content_template = """
    <style media="screen" type="text/css"><!--
    p {{ margin: 0 0 1.6em 0; }}
    --></style>
    <div id="wrapper" style="color: #000000; font-family: Arial,Helvetica,sans-serif; font-size: 14px; line-height: 18px;">
    <p>Product Name: {product_name}<br />
    Product Page: <a href="{product_page}">Page Link</a><br />
    Latest Review Number: {latest_number}<br />
    Last Review Number: {last_number}</p>
    </div>
    """

    logging.getLogger().info("---------- Start working ----------")

    with open(args.product_file) as product_file:
        for record in product_file:
            try:
                product_name, product_page = record.strip().split(args.seperator)
                logging.getLogger().info("Product_Page: {0}".format(product_page))

                # Get the review number
                timeout = 5
                response = requests.get(product_page, timeout=timeout)
                response.raise_for_status()

                page = BeautifulSoup(response.content)
                review_text_element = page.find("span",
                        id="acrCustomerReviewText")

                if review_text_element:
                    match = re.match(r'(?P<review_number>\d*) customer review[s]?',
                            review_text_element.string)

                    if match:
                        latest_number = match.group('review_number')
                        last_number = asin_to_review_number.get(product_page, 0)
                        logging.getLogger().info("last_number = {0}, latest_number = {1}".format(last_number, latest_number))
                        if last_number != latest_number:
                            # update on the reivew number, then send a email
                            asin_to_review_number[product_page] = latest_number

                            email_content = content_template.format(product_name=product_name,
                                    product_page=product_page, latest_number=latest_number,
                                    last_number=last_number)
                            sender.send_email(recipients_email_address, email_subject, email_content)
                else:
                    asin_to_review_number[product_page] = 0

                logging.getLogger().info("Done: Product_Name = {0}, Product_Page= {1}".format(product_name,
                    product_page))
            except:
                logging.getLogger().exception("Product_Name = {0}, Product_Page= {1}".format(product_name,
                    product_page))
            time.sleep(args.delay)

        # write back into pickle file
        with open(args.pickle_file, 'w') as pkl_file:
            pickle.dump(asin_to_review_number, pkl_file)


if __name__ == "__main__":
    setting.basic_logging_config()

    # parse the command-line options
    parser = argparse.ArgumentParser(description='Check for update on review number')
    parser.add_argument('-s', '--seperator', default=',')
    parser.add_argument('-i', '--interval', type=float, default=5)
    parser.add_argument('-d', '--delay', type=float, default=1)
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('product_file', metavar='PRODUCT_FILE')
    parser.add_argument('pickle_file', metavar='PICKLE_FILE')
    args = parser.parse_args()

    # load the configuration file
    config = ConfigParser.ConfigParser()
    if not config.read(args.config_file):
        logging.getLogger().error('Configuration file is missing')
        sys.exit(1)

    check_for_update(args, config)
    
    # run the task every X minutes
    schedule.every(args.interval).minutes.do(check_for_update, args, config)
    while True:
        schedule.run_pending()
        time.sleep(args.delay)
