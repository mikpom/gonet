#from io import BytesIO
from django.db import models
import pandas as pd
from pandas.compat import StringIO
import json

class DataFrameField(models.Field):
    """
    Implements Django field for Pandas DataFrame object
    """
    def from_db_value(self, json_string, expression, connection, context):
        if json_string is None:
            return json_string
        # dtype=False is a workaround so a column consisting of only
        # None is coerced to object dtype
        return pd.read_json(json_string, orient='split', dtype=False)
    
    def to_python(self, value):
        if isinstance(value, pd.DataFrame):
            return value
        if value is None:
            return value
        return pd.read_json(value, orient='split', dtype=False)

    def get_prep_value(self, value):
        if isinstance(value, pd.DataFrame):
            json_buf = StringIO()
            value.to_json(json_buf, orient='split')
            return json_buf.getvalue()
        elif isinstance(value, str):
            return value

    def get_internal_type(self):
        return "TextField"

    def get_default(self):
        return  pd.DataFrame()

class JSONField(models.Field):
    """
    Implements JSON Field
    """
    def from_db_value(self, json_string, expression, connection, context):
        if json_string is None:
            return json_string
        obj = json.loads(json_string)
        return obj
    
    def to_python(self, value):
        if value is None:
            return value
        obj = json.loads(json_string)
        return obj

    def get_prep_value(self, value):
        return json.dumps(value)

    def get_internal_type(self):
        return "TextField"

    def get_default(self):
        return {}
