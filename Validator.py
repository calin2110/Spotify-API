from ValidatorError import ValidatorError


class Validator:

    @staticmethod
    def validate_top_request(tokens):
        if len(tokens) != 4:
            raise ValidatorError("invalid number of tokens")

        type = tokens[0]
        possible_types = ["_", "tracks", "artists"]
        if type not in possible_types:
            raise ValidatorError("type must either be a wildcard, tracks or artists")

        term = tokens[1]
        possible_terms = ["_", "short", "medium", "long"]
        if term not in possible_terms:
            raise ValidatorError("term must either be wildcard, short, medium or long")

        limit = tokens[2]
        if limit != "_" and not limit.isnumeric():
            raise ValidatorError("invalid limit specifier")
        if limit.isnumeric() and (int(limit) > 50 or int(limit) <= 0):
            raise ValidatorError("limit must be between 1 and 50")

        offset = tokens[3]
        if offset != "_" and not offset.isnumeric():
            raise ValidatorError("invalid offset specifier")
        if offset.isnumeric() and (int(offset) >= 50 or int(offset) < 0):
            raise ValidatorError("offset must be between 1 and 50")

    @staticmethod
    def validate_search_request(tokens):
        if len(tokens) != 4:
            raise ValidatorError("invalid number of tokens")

        query = tokens[0]

        operator = tokens[1]
        possible_operators = ["_", "or", "not"]
        if operator.lower() not in possible_operators:
            raise ValidatorError("invalid operator")

        operator_query = tokens[2]

        type = tokens[3]
        possible_types = ["_", "track", "artist", "album"]
        if type not in possible_types:
            raise ValidatorError("invalid type")

