import os

import texttable

import Validator
from SpotifyAPIFlow import SpotifyAPIFlow
from ValidatorError import ValidatorError


class Console:
    def __init__(self):
        client_id = '7d18e9fda3934bbf951ce48af9d46a3e'
        client_secret = os.getenv("clientsecret")
        filename = "tokens.bin"
        spotify = SpotifyAPIFlow(client_id, client_secret, filename)
        self.__spotify_API_flow = spotify
        self.__options = {"top": self.__find_top, "search": self.__search, "help": self.__help}

    def run(self):
        done = False
        while not done:
            try:
                command = input(">")
                if command == "":
                    print("Enter a valid command!")
                    continue
                tokens = self.__split_tokens_properly(command)
                initial_command = tokens[0].lower()

                command_tokens = tokens[1:]
                if initial_command not in self.__options:
                    print("Command is invalid!")
                else:
                    self.__options[initial_command](command_tokens)
            except ValidatorError as vError:
                print(str(vError))

    def __find_top(self, tokens):
        Validator.Validator.validate_top_request(tokens)

        presumed_type = tokens[0]
        if presumed_type == "_":
            type = "tracks"
        else:
            type = presumed_type

        presumed_term = tokens[1]
        if presumed_term == "_":
            term = "medium_term"
        else:
            term = presumed_term + "_term"

        presumed_limit = tokens[2]
        if presumed_limit == "_":
            limit = 50
        else:
            limit = int(presumed_limit)

        presumed_offset = tokens[3]
        if presumed_offset == "_":
            offset = 0
        else:
            offset = int(presumed_offset)

        json_info = self.__spotify_API_flow.get_personalized_info(type, term, limit, offset)
        table = self.__print_info_nicely(json_info, type)
        print(table)

    def __search(self, tokens):
        Validator.Validator.validate_search_request(tokens)

        query = tokens[0]

        presumed_operator = tokens[1]
        if presumed_operator == "_":
            operator = None
        else:
            operator = presumed_operator

        if operator is None:
            query_operator = None
        else:
            query_operator = tokens[2]

        presumed_type = tokens[3]
        if presumed_type == "_":
            type = "artist"
        else:
            type = presumed_type

        json_info = self.__spotify_API_flow.search(query, operator, query_operator, type)
        table = self.__print_info_nicely(json_info, type)
        print(table)

    def __help(self, tokens = None):
        print("top <type> <time_range> <limit> <offset>")
        print("search <query> <operator> <query operator> <type>")
        print("<type>: tracks, artists")
        print("<time_range>: short, medium, long")
        print("<limit>:0...50")
        print("<offset>:0...50")
        print("_ is a wildcard for all inputs")
        print("to write a sentence with spaces, start it with \" and end it with \"")
        print("<query>: sentence")
        print("<operator>: or, not")
        print("<query operator>: sentence")

    @staticmethod
    def __print_info_nicely(information, type):
        if len(information) == 0:
            return
        table = texttable.Texttable()
        header = []
        width = []

        list_of_keys = information[0].keys()

        for key in list_of_keys:
            header.append(key)

        if type == 'tracks' or type == 'track':
            width = [40, 30, 30, 10, 10, 10, 25, 10]
        elif type == 'artists' or type == 'artist':
            width = [20, 70, 10, 25, 10]
        elif type == 'album':
            width = [40, 40, 15, 30, 10, 10]

        allign = ['c' for _ in width]
        table.header(header)
        for entity in information:
            entity_row = []
            for key in list_of_keys:
                entity_row.append(entity[key])
            table.add_row(entity_row)
            table.set_cols_width(width)
            table.set_cols_align(allign)
        return table.draw()

    @staticmethod
    def __split_tokens_properly(command):
        tokens = command.split(" ")
        correct_tokens = []
        in_current_token = False
        current_token = ""
        for token in tokens:
            if not in_current_token and token[0] != "\"":
                correct_tokens.append(token)
                continue
            if in_current_token:
                if current_token != "":
                    current_token += " "
                if token[-1] == "\"":
                    current_token += token[:-1]
                    correct_tokens.append(current_token)
                    current_token = ""
                    in_current_token = False
                else:
                    current_token += token
                continue
            in_current_token = True
            current_token += token[1:]
        return correct_tokens
