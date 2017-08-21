# -*- coding: utf-8 -*-

import sys
import mws
import setting
import logging
import time
import datetime
import dateutil.parser
import ConfigParser
import argparse

def fetch_fba_orders_report(account_id, access_key, secret_key,
        start_date, end_date):
    """Fetch orders report within certain timerange (UTC time standard)"""
    orders = []

    try:
        reports_api = mws.Reports(access_key, secret_key, account_id)
        report_type = '_GET_AMAZON_FULFILLED_SHIPMENTS_DATA_'

        logging.getLogger().info("RequestReport: report_type = {0}, start_date = {1}, end_date = {2}".format(report_type, start_date.isoformat(), end_date.isoformat()))

        # request the order report using MWS API
        response = reports_api.request_report(report_type,
                start_date.isoformat(), end_date.isoformat())
        response.response.raise_for_status()
        report_request_id = response.parsed['ReportRequestInfo']['ReportRequestId']['value']

        # wait for 30 seconds
        sleeptime = 30
        time.sleep(sleeptime)

        # get the report request status
        logging.getLogger().info("GetReportRequestList: report_request_id = {0}".format(report_request_id))

        response = reports_api.get_report_request_list((report_request_id,))
        response.response.raise_for_status()
        processing_status = response.parsed['ReportRequestInfo']['ReportProcessingStatus']['value']

        logging.getLogger().debug("GetReportRequestList, response = {0}".format(response.parsed))

        while processing_status != '_DONE_':
            if processing_status == '_CANCELLED_':
                raise ValueError('Unexpected Cancellation of report request')
            moretime = 60
            time.sleep(moretime)

            # get the status again
            logging.getLogger().info("GetReportRequestList: report_request_id = {0}".format(report_request_id))
            response = reports_api.get_report_request_list((report_request_id,))
            response.response.raise_for_status()
            processing_status = response.parsed['ReportRequestInfo']['ReportProcessingStatus']['value']

        report_id = response.parsed['ReportRequestInfo']['GeneratedReportId']['value']

        # download the report
        logging.getLogger().info("GetReport: report_id = {0}".format(report_id))
        response = reports_api.get_report(report_id)
        response.response.raise_for_status()

        orders = response.parsed.split('\r\n')
        # remove the header
        orders = orders[1:]
        logging.getLogger().debug("Orders number = {0}".format(len(orders)))
    except:
        logging.getLogger().exception("Exception get caught")
    finally:
        return orders
    
    

if __name__ == "__main__":
    # logging setting
    setting.basic_logging_config()

    parser = argparse.ArgumentParser(description='Fetch orders report using MWS API')
    parser.add_argument('--range', nargs=2,
            help="Time range of orders report")
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    args = parser.parse_args()

    # load the configuration file
    config = ConfigParser.ConfigParser()
    if not config.read(args.config_file):
        logging.getLogger().error("Configuration file is missing")
        sys.exit(1)
        print 'zhu'

    try:
        account_id = config.get('mws_setting', 'account_id')
        access_key = config.get('mws_setting', 'access_key')
        secret_key = config.get('mws_setting', 'secret_key')
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    # get the list of order of `last day' (UTC time standard)
    utcnow = datetime.datetime.utcnow()
    end_date = utcnow.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - datetime.timedelta(days=1)

    if args.range is not None:
        try:
            start = dateutil.parser.parse(args.range[0])
            end = dateutil.parser.parse(args.range[1])
        except:
            logging.warn("Invalid string format")
        else:
            start_date = start
            end_date = end

    orders = fetch_fba_orders_report(account_id, access_key,
            secret_key, start_date, end_date)

    for order in orders: print order
