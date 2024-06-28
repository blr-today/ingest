class Firebase:
    def parse_firebase_struct(obj):
        if type(obj) == list:
            return [Firebase.parse_firebase_struct(x) for x in obj]
        for c in [
            "stringValue",
            "timestampValue",
            "booleanValue",
            "integerValue",
            "nullValue",
        ]:
            if c in obj:
                return obj[c]
        if "fields" in obj:
            for k in obj["fields"]:
                obj[k] = Firebase.parse_firebase_struct(obj["fields"][k])
            del obj["fields"]
        if "mapValue" in obj:
            return Firebase.parse_firebase_struct(obj["mapValue"])
        if "arrayValue" in obj:
            if "values" in obj["arrayValue"]:
                x = Firebase.parse_firebase_struct(obj["arrayValue"]["values"])
            else:
                x = []
            del obj["arrayValue"]
            return x
        return obj
