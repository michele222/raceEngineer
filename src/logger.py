import logging

logger = logging
logger.basicConfig(filename='events.log',
                   filemode='w',
                   format='%(levelname)s [%(asctime)s] [%(filename)s.%(funcName)s:%(lineno)d] %(message)s',
                   datefmt='%d-%m-%Y %H:%M:%S',
                   encoding='utf-8',
                   level=logging.INFO)