"""boogh vault is stored tokens and ids."""
import hashlib
import json
import os
import uuid

from boogh import config


class Vault:
    def __init__(self, path=""):
        self.path = path or config.store

    def load(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except (OSError, ValueError):
            if self.path == config.store:
                try:
                    with open(config.old_store) as f:
                        return json.load(f)
                except (OSError, ValueError):
                    pass
            return {}

    def save(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with os.fdopen(os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
            json.dump(data, f, indent=2)

    def get(self, key):
        return self.load().get(key)

    def put(self, key, value):
        data = self.load()
        data[key] = value
        self.save(data)

    def udid(self):
        data = self.load()
        found = data.get("udid")
        if not found:
            found = str(uuid.uuid4())
            data["udid"] = found
            self.save(data)
        return found

    def device(self):
        data = self.load()
        found = data.get("ride_device_id")
        if not found:
            found = str(uuid.uuid4())
            data["ride_device_id"] = found
            self.save(data)
        return found

    def fingerprint(self):
        data = self.load()
        found = data.get("ride_fp")
        if not found or len(found) != 32:
            found = hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()
            data["ride_fp"] = found
            self.save(data)
        return found

    def params(self, lat=None, long=None):
        return {"lat": lat if lat is not None else config.home_lat,
                "long": long if long is not None else config.home_long,
                "optionalClient": config.food_client, "client": config.food_client,
                "deviceType": config.food_client, "appVersion": config.food_version,
                "UDID": self.udid(), "Bonyan": "true"}
