"""Class jsonfile."""
import json


class JsonFile:
    def __init__(self, filepath):
        self._filepath = filepath

    def read(self):
        with open(self._filepath, "r") as jsonfile:
            return json.loads(jsonfile.read())

    def write(self, content):
        with open(self._filepath, "w") as jsonfile:
            jsonfile.write(json.dumps(content, indent=4))

    def update(self, key, value):
        content = self.read()
        if "." in key:
            content[key.split(".")[0]][key.split(".")[1]] = value
        else:
            content[key] = value
        self.write(content)
