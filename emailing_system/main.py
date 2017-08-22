# -*- coding: utf-8 -*-

import os
import sys
import argparse
import ConfigParser
import datetime
import time
import json
import logging
import schedule

import setting
import send
import order
import extract


def get_last_day_orders(config):
    """get the list of orders of last day"""
    try:
        account_id = config.get('mws_setting', 'account_id')
        access_key = config.get('mws_setting', 'access_key')
        secret_key = config.get('mws_setting', 'secret_key')
        mws_marketplaceids = json.loads(config.get('mws_setting', 'marketplaceids'))
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    utcnow = datetime.datetime.utcnow()
    end_date = utcnow.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - datetime.timedelta(days=1)

    orders = order.fetch_fba_orders_report(account_id, access_key,
            secret_key, start_date, end_date, mws_marketplaceids)
    return start_date, orders


def save_into_directory(orders, directory, filename):
    """Save the orders info as a file"""
    try: 
        os.makedirs(args.orders_dir)
    except OSError:
        if not os.path.isdir(args.orders_dir):
            raise

    name = os.path.join(directory, filename)
    logging.getLogger().debug("Writing to: File Name = {0}".format(name))

    with open(name, 'w') as foj:
        foj.write("\n".join(orders))


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Automatically send email to Amazon customers at a specific time')
    parser.add_argument('--delay', type=float, default=0.5,
            help="Delay between two sent email")
    parser.add_argument('--at', default='20:00',
            help="Schedule the task every day at a specific time")
    parser.add_argument('--run_once', default=False, action='store_true',
            help='Run the task once without scheduling') 
    parser.add_argument('--send_only', default=False, action='store_true',
            help="Send the email only")
    parser.add_argument('--download_only', default=False,
            action='store_true', help="Send the email only")
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('positive', metavar='POSITIVE_EMAIL')
    parser.add_argument('negative', metavar='NEGATIVE_EMAIL')
    parser.add_argument('orders_dir', metavar='ORDERS_DIR')
    return parser.parse_args()


def get_config(filename):
    """Get teh ConfigParser object"""
    config = ConfigParser.ConfigParser()
    if not config.read(filename):
        logging.getLogger().error('Configuration file is missing')
        sys.exit(1)
    return config


def job(args, config):
    """Sent email to Amazon customers"""
    logging.getLogger().info("Start the hard work...")

    order_file_pattern = '%Y_%m_%d'
    simplified_file_suffix = '_simple'

    if not args.send_only:
        start_date, orders = get_last_day_orders(config)

        # save it into the directory
        save_into_directory(orders, args.orders_dir,
                start_date.strftime(order_file_pattern))

        simplified_orders = extract.extract_order_detail(orders, config)
        seperator = ','
        simplified_orders = map(lambda order: seperator.join(order),
                simplified_orders)
        save_into_directory(simplified_orders, args.orders_dir,
                start_date.strftime(order_file_pattern) + \
                        simplified_file_suffix)

    if not args.download_only:
        try:
            time_to_email = dict(config.items('time_to_email'))
        except:
            logging.getLogger().exception("Configuration error")
            sys.exit(1)

        # set up the blacklist
        blacklist = set()
        blacklist.update(send.list_of_line(args.positive))
        blacklist.update(send.list_of_line(args.negative))
        logging.getLogger().debug('blacklist = {0}'.format(blacklist))

        # send email
        for days_ago, email_type in time_to_email.iteritems():
            utcnow = datetime.datetime.utcnow()
            start_date = utcnow - datetime.timedelta(days=int(days_ago))

            filename = os.path.join(args.orders_dir,
                    start_date.strftime(order_file_pattern) + \
                            simplified_file_suffix)

            if not os.path.exists(filename):
                logging.getLogger().warn("Order file is missing, " \
                        "File Name = {0}".format(filename))
                continue

            with open(filename) as orders:
                send.process_order_file(orders, blacklist,
                        config, email_type)


if __name__ == "__main__":
    # logging setting
    setting.basic_logging_config()

    args = parse_arguments()
    config = get_config(args.config_file)

    if args.run_once:
        job(args, config)
    else:
        schedule.every().day.at(args.at).do(job, args, config)
        while True:
            schedule.run_pending()
            logging.getLogger().info("I'm sleeping..")
            time.sleep(10)
