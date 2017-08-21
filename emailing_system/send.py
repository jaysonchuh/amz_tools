# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import setting
import traceback
import smtplib
import logging
import time
import StringIO

from email.mime.text import MIMEText


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

def process_order_file(orders, blacklist, config, email_type, seperator=',', delay=0.5):
    """Send email to every customer"""
    try:
        sender_email_address = config.get('email_setting', 'sender_email_address')
        sender_smtp_server = config.get('email_setting', 'sender_smtp_server')
        sender_smtp_password = config.get('email_setting', 'sender_smtp_password')
        sender_name = config.get('email_setting', 'sender_name')
        shop_name = config.get('email_setting', 'shop_name')

        email_subject_template = dict(config.items('email_subject_template'))
        email_content_template = dict(config.items('email_content_template'))

        subject_template = email_subject_template[email_type]
        content_template = email_content_template[email_type]
    except KeyError:
        logging.getLogger().exception("Invalid email type")
        sys.exit(1)
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    sender = Sender(sender_email_address, sender_smtp_server,
            sender_smtp_password)

    try:
        for record in orders:
            # No leading blanks or trailing blanks for every field
            product_name, asin, order_id, customer_name, \
                    email_address, order_status = record.split(seperator)

            if record.startswith('#') or record.strip() == '':
                logging.getLogger().info("Skipped Order Info: Customer_Name = {0}, Email_Address = {1}, Product_Name = {2}".format(customer_name, email_address, product_name))
                continue

            if record.strip() in blacklist:
                logging.getLogger().info("Order in blacklist: Customer_Name = {0}, Email_Address = {1}, Product_Name = {2}".format(customer_name, email_address, product_name))
                continue

            logging.getLogger().info("Order Info: Customer_Name = {0}, Email_Address = {1}, Product_Name = {2}".format(customer_name, email_address, product_name))

            email_subject = subject_template.format(customer_name=customer_name,
                    product_name=product_name)
            email_content = content_template.format(customer_name=customer_name,
                    asin=asin, product_name=product_name, order_id=order_id,
                    sender_name=sender_name, shop_name=shop_name)

            sender.send_email([email_address], email_subject, email_content)
            logging.getLogger().info("Email sent")
            time.sleep(delay)
    except:
        logging.getLogger().exception('Exception get Caught')
                        

def list_of_line(filename):
    """return a list of string with the trailing newline character striped"""
    with open(filename) as foj:
        return [line.strip()  for line in foj.readlines() if line.strip() != '']


if __name__ == "__main__":
    setting.basic_logging_config()

    parser = argparse.ArgumentParser(description='send email to Amazon customers')
    parser.add_argument('-s', '--seperator', default=',')
    parser.add_argument('-d', '--delay', type=float, default=1)
    parser.add_argument('email_type', metavar='EMAIL_TYPE')
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('positive', metavar='POSITIVE_ORDERS')
    parser.add_argument('negative', metavar='NEGATIVE_ORDERS')
    parser.add_argument('orders_file', metavar='ORDERS_FILE')

    args = parser.parse_args()

    # load the configuration file
    config = ConfigParser.ConfigParser()
    if not config.read(args.config_file):
        logging.getLogger().error('Configuration file is missing')
        sys.exit(1)
    
    # set up the blacklist
    blacklist = set()
    blacklist.update(list_of_line(args.positive))
    blacklist.update(list_of_line(args.negative))
    logging.getLogger().debug('blacklist = {0}'.format(blacklist))

    with open(args.orders_file) as orders:
        process_order_file(orders, blacklist, config, args.email_type, args.seperator, args.delay)
