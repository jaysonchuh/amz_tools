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

    # load the seller_to_feedback_number pickle file
    try:
        with open(args.pickle_file, 'rb') as pkl_file:
            seller_to_feedback_number = pickle.load(pkl_file)
    except:
        seller_to_feedback_number = {}
    
    try:
        sender_email_address = config.get('email_setting', 'sender_email_address')
        sender_smtp_server = config.get('email_setting', 'sender_smtp_server')
        sender_smtp_password = config.get('email_setting', 'sender_smtp_password')
        recipients_email_address = json.loads(config.get('email_setting', 'recipients_email_address'))
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    sender = Sender(sender_email_address, sender_smtp_server, sender_smtp_password)

    email_subject = 'Update on feedback number!'
    content_template = """
    <style media="screen" type="text/css"><!--
    p {{ margin: 0 0 1.6em 0; }}
    --></style>
    <div id="wrapper" style="color: #000000; font-family: Arial,Helvetica,sans-serif; font-size: 14px; line-height: 18px;">
    <p>Seller: {seller_name}<br />
    Storefront: <a href="{storefront_link}">Link</a><br />
    Lastest Feedback Number: {latest_number}<br />
    Last Feedback Number: {last_number}<br />
    </div>
    """

    logging.getLogger().info("---------- Start working ----------")

    with open(args.storefronts) as storefronts:
        for record in storefronts:
            try:
                seller_name, storefront_link = record.strip().split(args.seperator)
                logging.getLogger().info("Storefront: {0}".format(storefront_link))

                # Get the feedback number
                timeout = 5
                response = requests.get(storefront_link, timeout=timeout)
                response.raise_for_status()

                page = BeautifulSoup(response.content)
                feedback_table = page.find("table",
                        id="feedback-summary-table")

                if feedback_table:
                    rows = feedback_table.findChildren(['th', 'tr'])
                    last_row = rows[len(rows) - 1]

                    cells_in_last_row = last_row.findChildren('td')
                    last_cell_in_last_row = cells_in_last_row[len(cells_in_last_row) - 1]

                    latest_number = last_cell_in_last_row.string
                    last_number = seller_to_feedback_number.get(seller_name, 0)

                    logging.getLogger().info("last_number = {0}, latest_number = {1}".format(last_number, latest_number))

                    if last_number != latest_number:
                        # update on the feedback number, then send a email
                        seller_to_feedback_number[seller_name] = latest_number

                        email_content = content_template.format(seller_name=seller_name,
                                storefront_link=storefront_link, latest_number=latest_number,
                                last_number=last_number)
                        sender.send_email(recipients_email_address, email_subject, email_content)
                else:
                    seller_to_feedback_number[seller_name] = 0

                logging.getLogger().info("Done: Seller_Name = {0}, Storefront = {1}".format(seller_name,
                    storefront_link))
            except:
                logging.getLogger().info("Done: Seller_Name = {0}, Storefront = {1}".format(seller_name,
                    storefront_link))

            time.sleep(args.delay)

        # write back into pickle file
        with open(args.pickle_file, 'w') as pkl_file:
            pickle.dump(seller_to_feedback_number, pkl_file)


if __name__ == "__main__":
    setting.basic_logging_config()

    # parse the command-line options
    parser = argparse.ArgumentParser(description='Check for update on review number')
    parser.add_argument('-s', '--seperator', default=',')
    parser.add_argument('-i', '--interval', type=float, default=5)
    parser.add_argument('-d', '--delay', type=float, default=1)
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('storefronts', metavar='STOREFRONTS')
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
