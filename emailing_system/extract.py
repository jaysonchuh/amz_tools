# -*- coding: utf-8 -*-

import sys
import argparse
import logging
import setting
import ConfigParser

def simplify_record(sku_to_asin, sku_to_product_name,
        input_seperator):
    """Return a mapping function"""

    unique_order_dict = {}

    def mapping(record):
        """Simplify a order record"""
        # product_name, asin, order_id, buyer_name, buyer_email, order_status
        fields = record.split(input_seperator)

        try:
            sku = fields[13].lower()

            product_name = sku_to_product_name[sku].strip()
            asin = sku_to_asin[sku].strip()
            order_id = fields[0]

            # first name, strip the non-alphabet characters if possible
            buyer_name = (fields[11].split(' ', 1))[0]
            buyer_name = filter(str.isalpha, buyer_name).capitalize()

            buyer_email = fields[10]
            order_status = 'shipped'
        except:
            # skip invalid record
            logging.getLogger().exception('Invalid record: "{0}"'.format(record))
            return None

        # skip non-Amazon-channel orders
        if buyer_email == '':
            return None

        # remove the duplicate
        key = buyer_email + '_' + product_name
        if key in unique_order_dict:
            return None

        unique_order_dict[key] = True

        return [product_name, asin, order_id, buyer_name, 
                buyer_email, order_status]

    return mapping


def extract_order_detail(orders, config, input_seperator='\t'):
    """Simplify orders report
        orders:                 list of order
        sku_to_asin:            map sku to asin
        sku_to_product_name:    map sku to product name
        input_seperator:        input record delimiter 
    """
    try:
        sku_to_asin = dict(config.items('sku_to_asin'))
        sku_to_product_name = dict(config.items('sku_to_product_name'))
    except:
        logging.getLogger().exception("Configuration error")
        sys.exit(1)

    simplify = simplify_record(sku_to_asin, sku_to_product_name,
            input_seperator)

    simplify_list = filter(lambda x : x is not None, map(simplify, orders))
    logging.getLogger().debug("simplify_list = {0}".format(simplify_list))
    return simplify_list


if __name__ == "__main__":
    # logging setting
    setting.basic_logging_config()

    parser = argparse.ArgumentParser(description='Extract detail from order report')
    parser.add_argument('-s', '--input_seperator', default='\t')
    parser.add_argument('-o', '--output_seperator', default=',')
    parser.add_argument('config_file', metavar='CONFIG_FILE')
    parser.add_argument('fba_order_report', metavar='FBA_ORDER_REPORT')
    args = parser.parse_args()

    # load the configuration file
    config = ConfigParser.ConfigParser()
    if not config.read(args.config_file):
        logging.getLogger().error("Configuration file is missing")
        sys.exit(1)

    with open(args.fba_order_report) as order_report:
        order_list = extract_order_detail(order_report, config,
                args.input_seperator)

    for record in order_list:
        print args.output_seperator.join(record)
