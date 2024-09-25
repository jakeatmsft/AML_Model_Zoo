import os
import logging
import json
from time import time
import io 
import time

from azureml.contrib.services.aml_response import AMLResponse


def init():
    """
    This function is called when the container is initialized/started, typically after create/update of the deployment.
    You can write the logic here to perform init operations like caching the model in memory
    """
    logging.info("Init complete")

def run(raw_data):
    def _mock_chat():
        words = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.'.split(' ')
        yield "start:\n"
        for w in words:
            yield w + ",\n"
            time.sleep(.5)
    """
    This function is called for every invocation of the endpoint to perform the actual scoring/prediction.
    In the example we extract the data from the json input and call the scikit-learn model's predict()
    method and return the result back
    """
    logging.info("model 1: request received")
    ret = _mock_chat()
    to_ret = AMLResponse(ret, 200)
    to_ret.headers["Content-Type"] = "text/event-stream"
    to_ret.headers["X-Accel-Buffering"] = "no"
    return to_ret

