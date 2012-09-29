import importlib
import logging
import sys

log = logging.getLogger(__name__)

DEFAULT_VALIDATORS = [
    "mimeprovider.validators.jsonschema_validator"
]


def get_default_validator():
    for module in DEFAULT_VALIDATORS:
        try:
            m = importlib.import_module(module)
            return m.__validator__
        except ImportError:
            log.warning(
                "Validator not found {0}".format(module),
                exc_info=sys.exc_info())

            continue

    return None
