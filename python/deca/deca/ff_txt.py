import json
import io


def load_json(buffer):
    """
    Returns a structure if file was json
    :param buffer:
    :return: JSON created object or None
    """
    fp = io.BytesIO(buffer)
    try:
        data = json.load(fp)
        return data
    except json.decoder.JSONDecodeError:
        return None
